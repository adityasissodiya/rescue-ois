"""The journal rules on hand-built record sets."""

from aas_testbed.model import (
    Kind,
    Org,
    Record,
    Status,
    classify,
    holder_at,
    required_signers,
    timeline,
)

ORG = Org()
EPS = 0.5
_seq: dict[str, int] = {}


def rec(kind: Kind, signer: str, ts: float, **kw) -> Record:
    _seq[signer] = _seq.get(signer, 0) + 1
    return Record(rid=kw.pop("rid", f"{kind.value}-{signer}-{_seq[signer]}"), kind=kind,
                  signer=signer, device="x", pseq=_seq[signer], ts=ts, true_ts=ts, **kw)


GRANT = rec(Kind.GRANT, "C", 0.0, subject="A", rid="grant")
RULE = rec(Kind.RULE, "C", 0.0, subject="B", primary="A", timeout=300.0,
           primary_timeout=240.0, rid="rule")


def test_grant_then_takeover():
    take = rec(Kind.TAKEOVER, "C", 100.0, subject="B")
    segs = timeline([GRANT, take], ORG)
    assert holder_at(segs, 50) == "A"
    assert holder_at(segs, 150) == "B"


def test_handover_by_non_holder_is_ignored():
    hand = rec(Kind.HANDOVER, "B", 100.0, subject="S")
    assert holder_at(timeline([GRANT, hand], ORG), 150) == "A"


def test_activation_needs_rule_holder_and_silence():
    ok = rec(Kind.ACTIVATION, "B", 400.0, subject="B", rule="rule", last_heard=90.0)
    short = rec(Kind.ACTIVATION, "B", 400.0, subject="B", rule="rule", last_heard=200.0)
    assert holder_at(timeline([GRANT, RULE, ok], ORG), 500) == "B"
    assert holder_at(timeline([GRANT, RULE, short], ORG), 500) == "A"
    assert holder_at(timeline([GRANT, ok], ORG), 500) == "A"  # rule not held


def test_handover_inside_partition_overrules_later_activation():
    hand = rec(Kind.HANDOVER, "A", 200.0, subject="S")
    act = rec(Kind.ACTIVATION, "B", 400.0, subject="B", rule="rule", last_heard=90.0)
    segs = timeline([GRANT, RULE, hand, act], ORG)
    assert holder_at(segs, 500) == "S"
    d = rec(Kind.DECISION, "B", 450.0, subject="K1", grant_ref=act.rid)
    v = classify(d, segs, EPS)
    assert (v.status, v.reason) == (Status.RESIDUAL, "no_valid_grant")


def test_statuses():
    take = rec(Kind.TAKEOVER, "C", 100.0, subject="B")
    segs = timeline([GRANT, take], ORG)
    before = rec(Kind.DECISION, "A", 50.0, grant_ref="grant")
    after = rec(Kind.DECISION, "A", 150.0, grant_ref="grant")
    close = rec(Kind.DECISION, "A", 100.2, grant_ref="grant")
    by_b = rec(Kind.DECISION, "B", 150.0, grant_ref=take.rid)
    assert classify(before, segs, EPS).status is Status.PROVISIONAL
    assert classify(before, segs, EPS, settled=True).status is Status.AUTHORITATIVE
    assert classify(after, segs, EPS).reason == "superseded"
    assert classify(close, segs, EPS).status is Status.IN_DOUBT
    assert classify(close, segs, 0.0).status is Status.RESIDUAL
    assert classify(by_b, segs, EPS).status is Status.PROVISIONAL


def test_missing_dependency_keeps_decision_provisional():
    act = rec(Kind.ACTIVATION, "B", 400.0, subject="B", rule="rule", last_heard=90.0)
    d = rec(Kind.DECISION, "B", 450.0, grant_ref=act.rid)
    held = {r.rid: r for r in (GRANT, act, d)}  # the rule has not arrived
    segs = timeline(held.values(), ORG)
    v = classify(d, segs, EPS, held=held)
    assert (v.status, v.reason) == (Status.PROVISIONAL, "missing_dependency")


def test_settlement_closing_drops_superseded_commander():
    take = rec(Kind.TAKEOVER, "C", 100.0, subject="B")
    segs = timeline([GRANT, take], ORG)
    named = {"A", "B", "C"}
    assert "A" in required_signers(150.0, segs, [], named, ORG, EPS, "strict")
    assert "A" not in required_signers(150.0, segs, [], named, ORG, EPS, "closing")
    # Before the takeover, or within eps of it, A's records still matter.
    assert "A" in required_signers(100.2, segs, [], named, ORG, EPS, "closing")


def test_settlement_closing_keeps_primary_under_activation():
    act = rec(Kind.ACTIVATION, "B", 400.0, subject="B", rule="rule", last_heard=90.0)
    segs = timeline([GRANT, RULE, act], ORG)
    need = required_signers(500.0, segs, [RULE], {"A", "B", "C"}, ORG, EPS, "closing")
    assert {"A", "B", "C"} <= need
