"""Self-tests of the independent checker on hand-written traces (no simulator involved)."""

from __future__ import annotations

from experiments.checker import check

HEADER = {
    "ev": "header",
    "scenario": "T",
    "kind": "test",
    "rules": "seed-v0",
    "family": "mandate",
    "params": {"n": 4, "f": 1, "q": 3, "H": 100, "g": 3, "eps": 1, "F": 0, "W": None},
    "officers": ["A", "B", "C", "D"],
    "byzantine": ["D"],
    "verifiers": ["V1", "V2"],
    "clocks": {"A": 0, "B": 0, "C": 0, "D": 0, "V1": 1, "V2": -1},
    "scope": "s",
    "genesis": {
        "msg_id": "grant:g1",
        "msg": {
            "type": "grant",
            "epoch": 1,
            "holder": "A",
            "start": 0,
            "scope": "s",
            "deputy": None,
        },
    },
}
R1 = {"type": "renewal", "epoch": 1, "end": 98, "scope": "s"}
G2 = {
    "type": "grant",
    "epoch": 2,
    "holder": "B",
    "start": 60,
    "scope": "s",
    "deputy": None,
}
R2 = {"type": "renewal", "epoch": 2, "end": 150, "scope": "s"}


class T:
    def __init__(self):
        self.ev = []

    def add(self, t, ev, **kw):
        self.ev.append(
            {"seq": len(self.ev), "step": len(self.ev), "t": t, "ev": ev, **kw}
        )
        return self

    def certify(self, t, mid, msg, signers, at):
        for u in signers:
            self.add(t, "sign", by=u, msg_id=mid, msg=msg, local=t, adversary=u == "D")
        self.add(
            t,
            "cert",
            cert=mid,
            msg_id=mid,
            msg=msg,
            signatures=[{"by": u, "kind": "genuine"} for u in signers],
        )
        for v in at:
            self.add(t, "store", at=v, cert=mid, msg_id=mid, valid=True)
        return self

    def accept(self, t, v, epoch, holder, cid, evidence, rule="D1"):
        off = HEADER["clocks"][v]
        return self.add(
            t,
            "accept",
            at=v,
            local=t + off,
            rule=rule,
            cmd={
                "epoch": epoch,
                "holder": holder,
                "cid": cid,
                "payload": "op",
                "created": t,
            },
            evidence=[{"msg_id": m, "msg": x} for m, x in evidence],
        )


def codes(t: T) -> list[str]:
    return check(HEADER, t.ev)["codes"]


def base() -> T:
    return T().certify(0, "r1", R1, "ABC", ["V1", "V2"])


GEN = ("grant:g1", HEADER["genesis"]["msg"])


def test_clean_trace_has_no_violation():
    assert codes(base().accept(10, "V1", 1, "A", "a", [GEN, ("r1", R1)])) == []


def test_overlap_of_two_holders_is_separation_and_epoch_order():
    t = base().certify(1, "g2", G2, "ABC", ["V2"]).certify(1, "r2", R2, "ABC", ["V2"])
    t.accept(70, "V1", 1, "A", "a", [GEN, ("r1", R1)])
    t.accept(70, "V2", 2, "B", "b", [("g2", G2), ("r2", R2)])
    assert {"SEPARATION", "EPOCH-ORDER"} <= set(codes(t))


def test_lower_epoch_after_higher_is_epoch_order_even_far_apart():
    t = base().certify(1, "g2", G2, "ABC", ["V2"]).certify(1, "r2", R2, "ABC", ["V2"])
    t.accept(62, "V2", 2, "B", "b", [("g2", G2), ("r2", R2)])
    t.accept(90, "V1", 1, "A", "a", [GEN, ("r1", R1)])
    assert "EPOCH-ORDER" in codes(t) and "SEPARATION" not in codes(t)


def test_replay_is_found():
    t = base().accept(10, "V1", 1, "A", "a", [GEN, ("r1", R1)])
    t.accept(11, "V1", 1, "A", "a", [GEN, ("r1", R1)])
    assert "REPLAY" in codes(t)


def test_evidence_must_be_delivered_and_quorum_signed():
    t = T().certify(0, "r1", R1, "AD", ["V1"])  # only two distinct signers
    t.accept(10, "V1", 1, "A", "a", [GEN, ("r1", R1)])
    assert "INVALID-EVIDENCE" in codes(t)
    t = T().certify(0, "r1", R1, "ABC", ["V2"])  # delivered to V2, used at V1
    t.accept(10, "V1", 1, "A", "a", [GEN, ("r1", R1)])
    assert "INVALID-EVIDENCE" in codes(t)


def test_acceptance_outside_the_window_is_invalid_evidence():
    t = base().accept(98, "V1", 1, "A", "a", [GEN, ("r1", R1)])  # local 99 > end 98
    assert "INVALID-EVIDENCE" in codes(t)


def test_wrong_local_reading_is_a_clock_violation():
    t = base()
    t.add(
        10,
        "accept",
        at="V1",
        local=13,
        rule="D1",
        cmd={"epoch": 1, "holder": "A", "cid": "a", "payload": "op", "created": 10},
        evidence=[{"msg_id": m, "msg": x} for m, x in (GEN, ("r1", R1))],
    )
    assert "CLOCK" in codes(t)


def test_withdrawal_to_expiry_bound():
    far = {"type": "renewal", "epoch": 1, "end": 400, "scope": "s"}
    t = base().add(5, "withdraw", by="B", epoch=1).add(6, "withdraw", by="C", epoch=1)
    t.certify(7, "rf", far, "ABD", ["V1"])  # B signs after withdrawing: a broken signer
    t.accept(200, "V1", 1, "A", "a", [GEN, ("rf", far)])
    assert "WITHDRAWAL-EXPIRY" in codes(t)  # 200 > t_W + H + 2 eps = 108


def test_two_quorum_grants_for_one_epoch():
    other = dict(G2, holder="C")
    t = base().certify(1, "g2", G2, "ABD", []).certify(2, "g2c", other, "ACD", [])
    assert "GRANT-UNIQUENESS" in codes(t)


def test_bad_parameters_are_reported():
    hdr = dict(HEADER, params=dict(HEADER["params"], q=2))
    assert "PARAMS" in check(hdr, base().ev)["codes"]
