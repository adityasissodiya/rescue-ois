"""Directed scenarios. All parameter values are synthetic (integer time units).

Identifiers:
  V0-*     seed-v0 rules (spec/protocol.md)
  ORIG-*   frozen fixtures of the 11 November 2026 draft rules (orig-2026-11-11); a repair
           of seed-v0 must not change these
  NC-*     negative controls: a deliberately broken rule variant; the checker must report
           the named violation. Each has a *-CONTROL twin with the correct rules and the
           same events, which must report no violation.
  CMP-*    comparison mechanisms (sim/baselines.py), mechanism abstractions only

Kinds: positive (no violation; non-vacuity minimums), witness (documented failure is
expected), negative / control, comparison.
"""

from __future__ import annotations

import copy

OFFSETS = {"A": 0, "B": 1, "C": -1, "D": 0, "V1": 1, "V2": -1}
EXACT = {p: 0 for p in OFFSETS}
BASE = {"n": 4, "f": 1, "H": 100, "g": 3, "eps": 1, "F": 0}
WITNESS = {"n": 4, "f": 1, "H": 100, "g": 1, "eps": 0, "F": 0}
HONEST3 = ("A", "B", "C")
V12 = ("V1", "V2")
G0 = {"holder": "A", "start": 0}
G0_DEPUTY = {"holder": "A", "start": 0, "deputy": "B"}
LEASE_INIT = {
    u: {"consents": ["A"], "holder": "A", "floor": 0, "max_end": 0} for u in "ABCD"
}


def hend(holder: str, t: int, params=BASE, offsets=OFFSETS) -> int:
    """The holder's requested end time C_c(t) + H - 2 eps (spec s. 7)."""
    return t + offsets[holder] + params["H"] - 2 * params["eps"]


class Sc:
    def __init__(
        self,
        sid,
        kind,
        rules,
        title,
        *,
        params=BASE,
        offsets=OFFSETS,
        byzantine=("D",),
        genesis=None,
        init=None,
        verifiers=V12,
        claim=None,
    ):
        self.d = {
            "id": sid,
            "kind": kind,
            "rules": rules,
            "title": title,
            "claim": claim,
            "scope": "feeder-7",
            "params": dict(params),
            "officers": ["A", "B", "C", "D"],
            "byzantine": list(byzantine),
            "verifiers": list(verifiers),
            "clocks": dict(offsets),
            "signer_init": copy.deepcopy(init or {}),
            "messages": {},
            "events": [],
            "expect": {},
        }
        if genesis is not None:
            self.d["genesis"] = dict(genesis)

    # ---------------------------------------------------------------- primitives
    def ev(self, t, op, **kw):
        self.d["events"].append({"t": t, "op": op, **kw})

    def msg(self, label, **fields):
        old = self.d["messages"].get(label)
        if old is not None and old != fields:
            raise ValueError(f"message label {label} reused with other fields")
        self.d["messages"][label] = fields
        return label

    def deliver(self, t, to, *certs):
        for x in to:
            self.ev(t, "deliver", to=x, certs=list(certs))

    def consent(self, t, holder, by, value=True):
        for u in by:
            self.ev(t, "consent", by=u, holder=holder, value=value)

    def note(self, t, text, mark=None):
        self.ev(t, "note", text=text, mark=mark)

    def cmd(self, t, by, cid, to, epoch=None, attach=(), **kw):
        self.ev(
            t, "command", by=by, cid=cid, to=to, epoch=epoch, attach=list(attach), **kw
        )

    def certify(
        self,
        t,
        label,
        signers,
        *,
        cert=None,
        to=(),
        learn=(),
        short=False,
        asm=None,
        **asm_kw,
    ):
        """Each signer is asked to sign at t; the certificate is assembled at asm (default
        t) from the signatures that exist (short=True allows refusals) and delivered."""
        for u in signers:
            self.ev(t, "sign", by=u, msg=label)
        ta = t if asm is None else asm
        cert = cert or label
        self.ev(
            ta,
            "assemble",
            cert=cert,
            msg=label,
            sigs=list(signers),
            allow_missing=short,
            **asm_kw,
        )
        if to:
            self.deliver(ta, to, cert)
        if learn:
            self.deliver(ta, learn, cert)
        return cert

    # ---------------------------------------------------------------- messages
    def renewal(self, t, epoch, end, signers=HONEST3, **kw):
        label = self.msg(f"R{epoch}@{end}", type="renewal", epoch=epoch, end=end)
        return self.certify(t, label, signers, **kw)

    def grant(self, t, epoch, holder, start, signers=HONEST3, deputy=None, **kw):
        fields = {"type": "grant", "epoch": epoch, "holder": holder, "start": start}
        if deputy is not None:
            fields["deputy"] = deputy
        return self.certify(
            t, self.msg(f"G{epoch}:{holder}@{start}", **fields), signers, **kw
        )

    def lease(self, t, holder, start, end, signers=HONEST3, **kw):
        label = self.msg(
            f"L:{holder}[{start},{end}]",
            type="lease",
            holder=holder,
            start=start,
            end=end,
        )
        return self.certify(t, label, signers, **kw)

    def order(self, t, holder, cid, start, end, signers=HONEST3, **kw):
        label = self.msg(
            f"O:{holder}:{cid}[{start},{end}]",
            type="order",
            holder=holder,
            cid=cid,
            payload="op",
            start=start,
            end=end,
        )
        return self.certify(t, label, signers, **kw)

    def expect(self, **kw):
        self.d["expect"].update(kw)
        return self

    def build(self) -> dict:
        return copy.deepcopy(self.d)


# ============================================================================ seed-v0


def v0_renew_expiry():
    s = Sc(
        "V0-RENEW-EXPIRY",
        "positive",
        "seed-v0",
        "Renewal, withdrawal and expiry at two verifiers",
        genesis=G0,
    )
    r98 = s.renewal(0, 1, 98)
    s.cmd(5, "A", "a1", "V1", epoch=1, attach=[r98])
    s.cmd(5, "A", "a2", "V2", epoch=1, attach=[r98])
    s.renewal(20, 1, 118, signers=("A", "B", "D"))
    r138 = s.renewal(40, 1, 138)
    s.note(50, "B and C decide to withdraw consent from epoch 1", mark="decision")
    s.ev(55, "withdraw", by="B", epoch=1)
    s.ev(57, "withdraw", by="C", epoch=1)
    short = s.renewal(60, 1, 158, signers="ABCD", short=True, cert="R1@158-short")
    s.cmd(100, "A", "a3", "V1", epoch=1, attach=[r138, short])
    s.cmd(137, "A", "a4", "V1", epoch=1)
    s.cmd(138, "A", "a5", "V1", epoch=1)
    s.cmd(139, "A", "a6", "V2", epoch=1, attach=[r138])
    s.cmd(140, "A", "a7", "V2", epoch=1)
    return s.expect(
        violations=[],
        min={"boundary_accepts": 2, "withdrawals": 2},
        equal={
            "accepted": 5,
            "valid_renewals": 3,
            "last_accept.e1:A": 139,
            "t_w.e1": 57,
        },
        refusals=["B:withdrawn", "C:withdrawn"],
        rejections=["expired"],
    )


def v0_handover():
    s = Sc(
        "V0-HANDOVER",
        "positive",
        "seed-v0",
        "Prepared handover from A (epoch 1) to B (epoch 2) at T = 150",
        genesis=G0,
    )
    for t, e in ((0, 98), (20, 118), (40, 138)):
        s.renewal(t, 1, e, to=V12)
    s.note(
        50,
        "handover to B planned for T = 150; from T - H the holder asks for ends <= T",
    )
    s.consent(50, "B", by=HONEST3)
    s.renewal(60, 1, 150, to=V12)
    s.grant(90, 2, "B", 153, learn=HONEST3, to=V12)
    s.renewal(95, 1, 193, short=True, cert="R1@193-refused")
    s.renewal(100, 2, hend("B", 100), to=V12)
    s.cmd(120, "A", "a1", "V1", epoch=1)
    s.cmd(120, "A", "a2", "V2", epoch=1)
    s.cmd(149, "A", "a3", "V1", epoch=1)
    s.cmd(151, "A", "a4", "V2", epoch=1)
    s.cmd(151, "A", "a5", "V1", epoch=1)
    s.cmd(151, "B", "b1", "V1", epoch=2)
    s.cmd(152, "B", "b2", "V1", epoch=2)
    s.cmd(152, "A", "a6", "V2", epoch=1)
    s.cmd(154, "B", "b3", "V2", epoch=2)
    return s.expect(
        violations=[],
        min={"successions": 1, "boundary_accepts": 4},
        equal={
            "accepted": 6,
            "last_accept.e1:A": 151,
            "first_accept.e2:B": 152,
            "valid_grants_by_epoch.2": 1,
        },
        refusals=["A:epoch-advanced", "B:epoch-advanced", "C:epoch-advanced"],
        rejections=["expired", "not-started"],
    )


def v0_selective():
    s = Sc(
        "V0-SELECTIVE-DELIVERY",
        "positive",
        "seed-v0",
        "Handover with delayed and selective delivery to two verifiers",
        genesis=G0,
    )
    s.renewal(0, 1, 98, to=V12)
    s.renewal(20, 1, 118, to=("V1",))
    s.cmd(30, "A", "a1", "V1", epoch=1)
    s.cmd(30, "A", "a2", "V2", epoch=1)
    s.renewal(40, 1, 138, to=("V1",))
    s.consent(50, "B", by=HONEST3)
    r150 = s.renewal(60, 1, 150, to=("V1",))
    g2 = s.grant(90, 2, "B", 153, learn=HONEST3, to=("V1",))
    r2 = s.renewal(100, 2, hend("B", 100), to=("V1",))
    s.cmd(100, "A", "a3", "V2", epoch=1)
    s.cmd(100, "A", "a4", "V1", epoch=1)
    s.cmd(151, "A", "a5", "V2", epoch=1, attach=[r150])
    s.cmd(152, "B", "b1", "V1", epoch=2)
    s.cmd(160, "B", "b2", "V2", epoch=2)
    s.deliver(200, ("V2",), g2, r2)
    s.cmd(200, "B", "b3", "V2", epoch=2)
    s.cmd(201, "B", "b4", "V2", epoch=2)
    return s.expect(
        violations=[],
        min={"successions": 1, "boundary_accepts": 2},
        equal={"accepted": 6, "last_accept.e1:A": 151, "first_accept.e2:B": 152},
        rejections=["expired", "no-grant"],
    )


def v0_removal():
    s = Sc(
        "V0-REMOVAL",
        "positive",
        "seed-v0",
        "Hostile holder: compromise, withdrawal race, expiry, successor",
        byzantine=(),
        genesis=G0,
    )
    s.renewal(0, 1, 98, to=V12)
    s.renewal(20, 1, 118, to=V12)
    s.ev(30, "compromise", who="A")
    r138 = s.renewal(40, 1, 138)
    s.note(
        45, "an operator notices commands from A that nobody planned", mark="detection"
    )
    s.note(50, "B, C and D decide to remove A; successor C", mark="decision")
    s.consent(50, "C", by=("B", "C", "D"))
    s.ev(55, "withdraw", by="B", epoch=1)
    r154 = s.renewal(56, 1, 154, signers="ABCD", short=True)
    s.ev(57, "withdraw", by="C", epoch=1)
    short = s.renewal(60, 1, 158, signers="ABCD", short=True, cert="R1@158-short")
    s.grant(61, 2, "C", 166, signers=("B", "C", "D"), learn=("B", "C", "D"), to=V12)
    s.renewal(62, 1, 160, signers="ABCD", short=True, cert="R1@160-short")
    s.cmd(100, "A", "h1", "V1", epoch=1, attach=[r138])
    s.renewal(150, 2, hend("C", 150), signers=("B", "C", "D"), to=V12)
    s.cmd(153, "A", "h2", "V1", epoch=1, attach=[r154])
    s.cmd(153, "A", "h3", "V2", epoch=1, attach=[r154, short])
    s.cmd(154, "A", "h4", "V1", epoch=1)
    s.cmd(155, "A", "h5", "V2", epoch=1)
    s.cmd(156, "A", "h6", "V2", epoch=1)
    s.cmd(164, "C", "c1", "V1", epoch=2)
    s.cmd(165, "C", "c2", "V1", epoch=2)
    s.cmd(167, "C", "c3", "V2", epoch=2)
    return s.expect(
        violations=[],
        min={"successions": 1},
        equal={
            "accepted": 6,
            "hostile_accepts": 4,
            "last_hostile_accept": 155,
            "t_w.e1": 57,
            "first_accept.e2:C": 165,
        },
        refusals=["B:withdrawn", "C:withdrawn", "D:epoch-advanced"],
        rejections=["expired", "not-started"],
    )


def v0_isolation():
    s = Sc(
        "V0-ISOLATION",
        "positive",
        "seed-v0",
        "Honest holder isolated with one verifier: fresh-command availability",
        genesis=G0,
    )
    last = None
    for t in (0, 20, 40, 60):  # Delta = 20, collection delta = 2
        last = s.renewal(t + 1, 1, hend("A", t), asm=t + 2)
    s.note(65, "outage: from now only A and V1 exchange messages", mark="outage-start")
    s.cmd(70, "A", "f1", "V1", epoch=1, attach=[last])
    s.note(80, "A's renewal request reaches no signer")
    s.cmd(100, "A", "f2", "V1", epoch=1)
    s.cmd(139, "A", "f3", "V1", epoch=1)  # t0 + H - Delta - delta - 4 eps = 139
    s.cmd(150, "A", "old", "V1", epoch=1, created=60)  # an old command delivered late
    s.cmd(157, "A", "f4", "V1", epoch=1)
    s.cmd(158, "A", "f5", "V1", epoch=1)
    return s.expect(
        violations=[],
        min={"boundary_accepts": 1},
        equal={
            "accepted": 5,
            "last_accept.e1:A": 157,
            "latest_created_accepted.e1:A": 157,
        },
        accept_between=[[139, 139]],
        rejections=["expired"],
    )


def v0_replay_clock():
    s = Sc(
        "V0-REPLAY-CLOCK",
        "positive",
        "seed-v0",
        "Replay, start and end boundaries, equal-time order, forged evidence",
        genesis={"holder": "A", "start": 10},
    )
    r98 = s.renewal(0, 1, 98)
    s.cmd(8, "A", "c1", "V1", epoch=1, attach=[r98])
    s.cmd(9, "A", "c2", "V1", epoch=1)
    s.cmd(11, "A", "c3", "V2", epoch=1, attach=[r98])
    s.ev(20, "replay", command="c2", to="V1")
    s.ev(20, "replay", command="c2", to="V2")
    s.cmd(97, "A", "c4", "V1", epoch=1)
    s.cmd(98, "A", "c5", "V1", epoch=1)
    s.cmd(99, "A", "c6", "V2", epoch=1)
    s.cmd(100, "A", "c7", "V2", epoch=1)
    r198 = s.renewal(100, 1, 198)
    s.renewal(100, 1, 250, short=True, cert="R1@250-refused")
    s.cmd(
        110, "A", "c8", "V1", epoch=1
    )  # seq order at t = 110: command, renewal, command
    s.deliver(110, ("V1",), r198)
    s.cmd(110, "A", "c9", "V1", epoch=1)
    forged = s.msg("R1@400", type="renewal", epoch=1, end=400)
    s.ev(120, "sign", by="D", msg=forged)
    s.ev(
        120,
        "assemble",
        cert="R1@400-forged",
        msg=forged,
        sigs=["D"],
        cross_scope=["A", "B"],
    )
    s.cmd(150, "A", "c10", "V1", epoch=1, attach=["R1@400-forged"])
    s.cmd(150, "A", "c11", "V1", epoch=1, forge_holder_sig=True)
    s.cmd(198, "A", "c12", "V1", epoch=1)
    return s.expect(
        violations=[],
        min={"boundary_accepts": 4},
        equal={"accepted": 7},
        refusals=["A:beyond-horizon", "B:beyond-horizon", "C:beyond-horizon"],
        rejections=["not-started", "replay", "expired", "bad-signature"],
    )


def _split_prefix(s, deputy=None):
    s.renewal(0, 1, 100, to=("V1",))
    s.cmd(10, "A", "a1", "V1", epoch=1)
    s.consent(50, "A", by=HONEST3)
    ga = s.grant(50, 2, "A", 101, signers=("A",), deputy=deputy)
    gb = s.grant(50, 2, "A", 102, signers=("B", "C"), deputy=deputy)
    s.deliver(50, ("V1", "A", "B", "C"), ga, gb)
    s.renewal(60, 1, 160, short=True, cert="R1@160-refused")
    s.renewal(60, 2, 160, short=True, cert="R2@160-refused")
    s.cmd(100, "A", "a2", "V1", epoch=1)
    s.cmd(101, "A", "a3", "V1", epoch=1)
    s.cmd(110, "A", "a4", "V1", epoch=2)


def _split_recovery(s, deputy=None):
    s.note(
        115,
        "the officers see that no epoch-2 grant formed and agree on one epoch-3 "
        "proposal",
        mark="detection",
    )
    s.grant(120, 3, "A", 121, deputy=deputy, learn=HONEST3, to=("V1",))
    s.renewal(120, 3, 220, to=("V1",))
    s.cmd(120, "A", "a5", "V1", epoch=3)
    s.cmd(121, "A", "a6", "V1", epoch=3)


SPLIT_REFUSALS = [
    f"{u}:{r}" for u in HONEST3 for r in ("epoch-advanced", "no-valid-grant")
]


def v0_split_recovery():
    s = Sc(
        "V0-SPLIT-RECOVERY",
        "positive",
        "seed-v0",
        "Split epoch-2 vote, stall, coordinated epoch-3 recovery (seed-v0, s. 9.3)",
        params=WITNESS,
        offsets=EXACT,
        genesis=G0,
    )
    _split_prefix(s)
    _split_recovery(s)
    return s.expect(
        violations=[],
        no_accept_between=[[101, 120]],
        accept_between=[[121, 121]],
        equal={"valid_grants_by_epoch.2": 0, "valid_grants_by_epoch.3": 1},
        refusals=SPLIT_REFUSALS,
        rejections=["expired", "no-grant", "not-started"],
    )


# ============================================================================ original draft


def orig_split_stall():
    s = Sc(
        "ORIG-SPLIT-STALL",
        "witness",
        "orig-2026-11-11",
        "Original rules: partial epoch-2 votes stall service after epoch 1 expires",
        params=WITNESS,
        offsets=EXACT,
        genesis=G0_DEPUTY,
    )
    _split_prefix(s, deputy="B")
    s.renewal(200, 1, 300, short=True, cert="R1@300-refused")
    s.renewal(200, 2, 300, short=True, cert="R2@300-refused")
    s.cmd(300, "A", "a5", "V1", epoch=1)
    s.cmd(300, "A", "a6", "V1", epoch=2)
    return s.expect(
        violations=[],
        no_accept_between=[[101, 300]],
        equal={"valid_grants_by_epoch.2": 0},
        refusals=SPLIT_REFUSALS,
        rejections=["expired", "no-grant"],
    )


def orig_split_recover():
    s = Sc(
        "ORIG-SPLIT-RECOVER-E3",
        "witness",
        "orig-2026-11-11",
        "Original rules: the same stall, then a coordinated epoch-3 proposal recovers",
        params=WITNESS,
        offsets=EXACT,
        genesis=G0_DEPUTY,
    )
    _split_prefix(s, deputy="B")
    _split_recovery(s, deputy="B")
    return s.expect(
        violations=[],
        no_accept_between=[[101, 120]],
        accept_between=[[121, 121]],
        equal={"valid_grants_by_epoch.2": 0, "valid_grants_by_epoch.3": 1},
        refusals=SPLIT_REFUSALS,
    )


def orig_deputy_same_reading():
    s = Sc(
        "ORIG-DEPUTY-SAME-READING",
        "witness",
        "orig-2026-11-11",
        "Original rules, F > 0: deputy and commander accepted at one clock reading",
        params={**WITNESS, "F": 20},
        offsets=EXACT,
        genesis=G0_DEPUTY,
        verifiers=("V1",),
    )
    s.renewal(0, 1, 100, to=("V1",))
    r130 = s.renewal(30, 1, 130)  # held back from V1
    s.cmd(50, "A", "a1", "V1", epoch=1)
    s.cmd(110, "B", "b1", "V1", epoch=1)  # D2: anchor 100 < 110 <= 120
    s.deliver(110, ("V1",), r130)
    s.cmd(110, "A", "a2", "V1", epoch=1)  # D1 at the same reading
    return s.expect(
        violations_include=["SAME-READING-TWO-ISSUERS"], equal={"accepted": 3}
    )


# ============================================================================ negative controls


def _nc(name, rules, kind):
    return Sc(
        name if kind == "negative" else name + "-CONTROL", kind, rules, "", genesis=G0
    )


def nc_o2_start_guard(rules, kind):
    s = _nc("NC-O2-START-GUARD", rules, kind)
    s.d["title"] = "Grant start earlier than M_u + g"
    for t, e in ((0, 98), (20, 118), (40, 138)):
        s.renewal(t, 1, e, to=("V1",))
    s.consent(50, "B", by=HONEST3)
    s.grant(50, 2, "B", 60, short=True, learn=HONEST3, to=V12)
    s.renewal(55, 2, hend("B", 55), short=True, to=("V2",))
    s.cmd(60, "B", "b1", "V2", epoch=2)
    s.cmd(62, "B", "b2", "V2", epoch=2)
    s.cmd(62, "A", "a1", "V1", epoch=1)
    s.cmd(100, "A", "a2", "V1", epoch=1)
    if kind == "negative":
        return s.expect(violations_include=["EPOCH-ORDER", "SEPARATION"])
    return s.expect(violations=[], refusals=["A:start-too-early"], min={"accepted": 2})


def nc_o1_epoch_guard(rules, kind):
    s = _nc("NC-O1-EPOCH-GUARD", rules, kind)
    s.d["title"] = "Renewal of an epoch the signer has left"
    for t, e in ((0, 98), (20, 118), (40, 138)):
        s.renewal(t, 1, e, to=("V1",))
    s.consent(50, "B", by=HONEST3)
    s.renewal(60, 1, 150, to=("V1",))
    s.grant(90, 2, "B", 153, learn=HONEST3, to=V12)
    r193 = s.renewal(95, 1, 193, short=True)
    s.renewal(100, 2, hend("B", 100), to=("V2",))
    s.cmd(154, "B", "b1", "V2", epoch=2)
    s.cmd(160, "A", "a1", "V1", epoch=1, attach=[r193])
    s.cmd(160, "B", "b2", "V2", epoch=2)
    if kind == "negative":
        return s.expect(violations_include=["EPOCH-ORDER", "SEPARATION"])
    return s.expect(violations=[], refusals=["A:epoch-advanced"], min={"accepted": 2})


def nc_d1_end_check(rules, kind):
    s = _nc("NC-D1-END-CHECK", rules, kind)
    s.d["title"] = "Verifier ignores the renewal end time"
    for t, e in ((0, 98), (20, 118), (40, 138)):
        s.renewal(t, 1, e, to=("V1",))
    s.ev(55, "withdraw", by="B", epoch=1)
    s.ev(57, "withdraw", by="C", epoch=1)
    s.cmd(100, "A", "a1", "V1", epoch=1)
    s.cmd(200, "A", "a2", "V1", epoch=1)
    if kind == "negative":
        return s.expect(violations_include=["WITHDRAWAL-EXPIRY", "INVALID-EVIDENCE"])
    return s.expect(violations=[], rejections=["expired"], equal={"accepted": 1})


def nc_d1_replay(rules, kind):
    s = _nc("NC-D1-REPLAY", rules, kind)
    s.d["title"] = "Verifier without replay protection"
    s.renewal(0, 1, 98, to=("V1",))
    s.cmd(10, "A", "a1", "V1", epoch=1)
    s.ev(20, "replay", command="a1", to="V1")
    if kind == "negative":
        return s.expect(violations_include=["REPLAY"])
    return s.expect(violations=[], rejections=["replay"], equal={"accepted": 1})


def nc_distinct_signers(rules, kind):
    s = _nc("NC-DISTINCT-SIGNERS", rules, kind)
    s.d["title"] = "Verifier counts one Byzantine signature three times"
    for t, e in ((0, 98), (20, 118), (40, 138)):
        s.renewal(t, 1, e, to=("V1",))
    s.ev(55, "withdraw", by="B", epoch=1)
    s.ev(57, "withdraw", by="C", epoch=1)
    lbl = s.msg("R1@300", type="renewal", epoch=1, end=300)
    s.ev(60, "sign", by="D", msg=lbl)
    s.ev(60, "assemble", cert="R1@300-dup", msg=lbl, sigs=["D"], dup={"D": 2})
    s.cmd(250, "A", "a1", "V1", epoch=1, attach=["R1@300-dup"])
    if kind == "negative":
        return s.expect(violations_include=["INVALID-EVIDENCE", "WITHDRAWAL-EXPIRY"])
    return s.expect(violations=[], rejections=["expired"], equal={"accepted": 0})


def nc_commit_after_release(rules, kind):
    s = _nc("NC-COMMIT-AFTER-RELEASE", rules, kind)
    s.d["title"] = "Signer crash between signature release and durable write"
    s.renewal(0, 1, 98, to=V12)
    s.renewal(40, 1, 138, to=V12)
    s.consent(45, "B", by=("A", "B"))
    s.consent(45, "C", by=("A", "C"))
    g_b = s.grant(50, 2, "B", 141, signers=("A", "B", "D"), to=("V1",))
    s.deliver(50, ("B",), g_b)
    s.ev(51, "crash", who="A")
    s.ev(52, "restart", who="A")
    g_c = s.grant(53, 2, "C", 141, signers=("A", "C", "D"), short=True, to=("V2",))
    s.deliver(54, ("C",), g_c)
    s.deliver(54, ("A", "C"), g_b)
    s.renewal(60, 2, hend("B", 60), signers="ABCD", to=V12)
    s.cmd(145, "B", "b1", "V1", epoch=2)
    s.cmd(145, "C", "c1", "V2", epoch=2)
    if kind == "negative":
        return s.expect(violations_include=["GRANT-UNIQUENESS", "SEPARATION"])
    return s.expect(
        violations=[], refusals=["A:epoch-not-higher"], equal={"accepted": 1}
    )


NEGATIVE = {
    "broken-o2-start-guard": nc_o2_start_guard,
    "broken-o1-epoch-guard": nc_o1_epoch_guard,
    "broken-d1-end-check": nc_d1_end_check,
    "broken-d1-replay": nc_d1_replay,
    "broken-distinct-signers": nc_distinct_signers,
    "broken-commit-after-release": nc_commit_after_release,
}


# ============================================================================ comparisons


def _cmp(name, proto, title, **kw):
    rules = {
        "seed-v0": "seed-v0",
        "xl": "xl",
        "tc": "tc",
        "tc-naive": "tc",
        "tc-wait": "tc",
        "qo-w": "qo-w",
    }[proto]
    if rules == "seed-v0":
        kw.setdefault("genesis", G0)
    else:
        kw.setdefault("init", LEASE_INIT)
    params = dict(kw.pop("params", BASE))
    if rules == "qo-w":
        params["W"] = 20
    return Sc(
        f"CMP-{name}-{proto.upper()}", "comparison", rules, title, params=params, **kw
    )


def cmp_handover(proto):
    s = _cmp("HANDOVER", proto, "Handover A to B decided at t = 50")
    mandate = proto == "seed-v0"
    ep = {"A": 1, "B": 2} if mandate else {"A": None, "B": None}
    if mandate:
        for t, e in ((0, 98), (20, 118), (40, 138)):
            s.renewal(t, 1, e, to=V12)
        s.consent(50, "B", by=HONEST3)
        s.grant(50, 2, "B", 156, learn=HONEST3, to=V12)
        s.renewal(60, 1, 158, short=True, cert="R1@158-refused")
    else:
        for t, e in ((0, 98), (20, 118), (40, 138)):
            s.lease(t, "A", 0, e, to=V12)
        s.consent(50, "B", by=HONEST3)
        s.consent(50, "A", by=HONEST3, value=False)
        if proto == "tc-naive":
            s.lease(50, "B", 50, 148, to=V12)
        s.lease(60, "A", 0, 158, short=True, cert="L:A-refused")
        if proto != "tc-naive":
            s.lease(60, "B", 156, 159, to=V12)
    # The same command stream in every run: B also tries to command during A's term.
    s.cmd(60, "B", "b0", "V1", epoch=ep["B"])
    s.cmd(100, "A", "a1", "V1", epoch=ep["A"])
    s.cmd(100, "B", "b00", "V2", epoch=ep["B"])
    s.cmd(137, "A", "a2", "V1", epoch=ep["A"])
    s.cmd(139, "A", "a3", "V2", epoch=ep["A"])
    if mandate:
        s.renewal(150, 2, hend("B", 150), to=V12)
    elif proto != "tc-naive":
        s.lease(150, "B", 156, hend("B", 150), to=V12)
    s.cmd(155, "B", "b1", "V1", epoch=ep["B"])
    s.cmd(157, "B", "b2", "V2", epoch=ep["B"])
    ka, kb = ("e1:A", "e2:B") if mandate else ("A", "B")
    if proto == "tc-naive":
        return s.expect(
            violations_include=["SEPARATION"], equal={f"first_accept.{kb}": 60}
        )
    return s.expect(
        violations=[],
        equal={"accepted": 5, f"last_accept.{ka}": 139, f"first_accept.{kb}": 155},
        rejections=["not-started"],
    )


def cmp_removal(proto):
    s = _cmp(
        "REMOVAL",
        proto,
        "Hostile holder: withdrawal race and late delivery",
        byzantine=(),
    )
    mandate = proto == "seed-v0"

    def withdraw(t, u):
        if mandate:
            s.ev(t, "withdraw", by=u, epoch=1)
        else:
            s.consent(t, "A", by=(u,), value=False)

    if proto == "qo-w":
        s.ev(30, "compromise", who="A")
        withdraw(55, "B")
        o1 = s.order(56, "A", "h1", 56, 75, signers="ABCD", short=True)
        o2 = s.order(56, "A", "h2", 56, 75, signers="ABCD", short=True)
        withdraw(57, "C")
        o3 = s.order(60, "A", "h3", 60, 79, signers="ABCD", short=True)
        s.cmd(61, "A", "h3", "V1", attach=[o3])
        s.cmd(74, "A", "h1", "V1", attach=[o1])
        s.cmd(76, "A", "h2", "V2", attach=[o2])
        return s.expect(
            violations=[],
            equal={"last_hostile_accept": 76, "t_w.A": 57},
            rejections=["no-order"],
        )
    cred = (
        (lambda t, e, **kw: s.renewal(t, 1, e, **kw))
        if mandate
        else (lambda t, e, **kw: s.lease(t, "A", 0, e, **kw))
    )
    ep = 1 if mandate else None
    cred(0, 98, to=V12)
    cred(20, 118, to=V12)
    s.ev(30, "compromise", who="A")
    cred(40, 138, to=V12)
    withdraw(55, "B")
    race = cred(56, 154, signers="ABCD", short=True)
    withdraw(57, "C")
    s.cmd(100, "A", "h1", "V1", epoch=ep)
    s.cmd(153, "A", "h2", "V1", epoch=ep, attach=[race])
    s.cmd(155, "A", "h3", "V2", epoch=ep, attach=[race])
    s.cmd(156, "A", "h4", "V2", epoch=ep)
    return s.expect(
        violations=[],
        equal={"last_hostile_accept": 155, ("t_w.e1" if mandate else "t_w.A"): 57},
        rejections=["expired"],
    )


def cmp_isolation(proto):
    s = _cmp("ISOLATION", proto, "Honest holder isolated with V1 from t = 65")
    key = "e1:A" if proto == "seed-v0" else "A"
    ep = 1 if proto == "seed-v0" else None
    if proto == "qo-w":
        p1 = s.order(61, "A", "p1", 60, 80, asm=62)
        s.note(
            65, "outage: from now only A and V1 exchange messages", mark="outage-start"
        )
        s.cmd(70, "A", "p1", "V1", attach=[p1], created=60)
        for t in (100, 139, 157):
            s.cmd(t, "A", f"f{t}", "V1")
        return s.expect(
            violations=[],
            equal={"accepted": 1, f"latest_created_accepted.{key}": 60},
            rejections=["no-order"],
        )
    last = None
    for t in (0, 20, 40, 60):
        if proto == "seed-v0":
            last = s.renewal(t + 1, 1, hend("A", t), asm=t + 2)
        else:
            last = s.lease(t + 1, "A", 0, hend("A", t), asm=t + 2)
    s.note(65, "outage: from now only A and V1 exchange messages", mark="outage-start")
    s.cmd(70, "A", "f1", "V1", epoch=ep, attach=[last])
    for i, t in enumerate((100, 139, 157, 158)):
        s.cmd(t, "A", f"f{i + 2}", "V1", epoch=ep)
    return s.expect(
        violations=[],
        equal={"accepted": 4, f"latest_created_accepted.{key}": 157},
        rejections=["expired"],
    )


def cmp_split(proto, two_holders):
    name = "SPLIT-TWO-HOLDERS" if two_holders else "SPLIT-SAME-HOLDER"
    s = _cmp(
        name,
        proto,
        "Split vote on the next authority, no coordination",
        params=WITNESS,
        offsets=EXACT,
    )
    first, second = ("B", "C") if two_holders else ("A", "A")
    if proto == "seed-v0":
        s.renewal(0, 1, 100, to=("V1",))
        s.cmd(10, "A", "a1", "V1", epoch=1)
        s.consent(50, first, by=("A",))
        s.consent(50, second, by=("B", "C"))
        s.grant(50, 2, first, 101, signers=("A",))
        s.grant(50, 2, second, 102 if not two_holders else 101, signers=("B", "C"))
        s.renewal(60, 1, 160, short=True, cert="R1@160-refused")
        s.cmd(100, "A", "a2", "V1", epoch=1)
        s.cmd(150, "A", "a3", "V1", epoch=1)
    else:
        s.lease(0, "A", 0, 100, to=("V1",))
        s.cmd(10, "A", "a1", "V1")
        s.consent(50, first, by=("A",))
        s.consent(50, second, by=("B", "C"))
        s.lease(50, first, 101, 150, signers=("A",))
        s.lease(50, second, 102 if not two_holders else 101, 150, signers=("B", "C"))
        s.lease(60, "A", 0, 160, short=True, to=("V1",))
        s.cmd(100, "A", "a2", "V1")
        s.cmd(150, "A", "a3", "V1")
    if proto == "xl" and not two_holders:
        return s.expect(violations=[], accept_between=[[150, 150]])
    return s.expect(violations=[], no_accept_between=[[101, 160]])


# ============================================================================ registry


def all_scenarios() -> list[dict]:
    out = [
        f().build()
        for f in (
            v0_renew_expiry,
            v0_handover,
            v0_selective,
            v0_removal,
            v0_isolation,
            v0_replay_clock,
            v0_split_recovery,
            orig_split_stall,
            orig_split_recover,
            orig_deputy_same_reading,
        )
    ]
    for broken, fn in NEGATIVE.items():
        out.append(fn(broken, "negative").build())
        out.append(fn("seed-v0", "control").build())
    for proto in ("seed-v0", "xl", "tc-naive", "tc-wait"):
        out.append(cmp_handover(proto).build())
    for proto in ("seed-v0", "xl", "tc", "qo-w"):
        out.append(cmp_removal(proto).build())
        out.append(cmp_isolation(proto).build())
    for proto in ("seed-v0", "xl"):
        for two in (False, True):
            out.append(cmp_split(proto, two).build())
    ids = [s["id"] for s in out]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate scenario identifiers")
    return out
