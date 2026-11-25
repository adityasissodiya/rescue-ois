"""Rule kernel: signer rules O1-O3 and verifier rule D1 (spec/protocol.md, s. 6-8).

Two rule sets share this code:

* ``seed-v0``: the normative rules of spec/protocol.md (F = 0, replay protection).
* ``orig-2026-11-11``: the rules of the 11 November 2026 draft as written, including
  grants with a deputy and the deputy rule D2 with an anchor (F > 0). Kept only to
  reproduce that draft's witnesses; it is not the proposed protocol.

Deliberately broken variants (negative controls) switch off one guard each; see
``BROKEN``. Functions here take explicit state and a local clock reading and contain no
transport: the simulator in ``sim/`` decides what is delivered when.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from .messages import Command, Grant, Message, Renewal


@dataclass(frozen=True)
class Params:
    n: int
    f: int
    H: int
    g: int
    eps: int
    F: int = 0

    def __post_init__(self) -> None:
        if self.f < 0 or self.n < 3 * self.f + 1:
            raise ValueError("need n >= 3f + 1")
        if self.H <= 0:
            raise ValueError("need H > 0")
        if self.eps < 0 or self.g <= 2 * self.eps:
            raise ValueError("need eps >= 0 and g > 2 eps")
        if self.F < 0:
            raise ValueError("need F >= 0")

    @property
    def q(self) -> int:
        """ceil((n + f + 1) / 2)"""
        return (self.n + self.f + 2) // 2

    @property
    def gamma(self) -> int:
        return self.g - 2 * self.eps


@dataclass(frozen=True)
class RuleSet:
    name: str
    deputy: bool = False  # grants name a deputy; D2 applies when F > 0 (orig only)
    replay_check: bool = True  # D1 rejects a repeated (epoch, holder, cid)
    # The switches below are False only in deliberately broken variants.
    o2_start_guard: bool = True  # O2: s >= M_u (+ F) + g
    o1_epoch_guard: bool = True  # O1: k = E_u
    d1_end_check: bool = True  # D1: tau <= e
    distinct_signers: bool = True  # validity counts distinct signers
    commit_before_release: bool = True  # s. 6.4
    fault: str | None = None  # description of the deliberate fault


SEED_V0 = RuleSet("seed-v0")
ORIG = RuleSet("orig-2026-11-11", deputy=True, replay_check=False)
BROKEN = {
    rs.name: rs
    for rs in (
        replace(
            SEED_V0,
            name="broken-o2-start-guard",
            o2_start_guard=False,
            fault="O2 signs a grant without checking s >= M_u + g",
        ),
        replace(
            SEED_V0,
            name="broken-o1-epoch-guard",
            o1_epoch_guard=False,
            fault="O1 renews epoch k after the signer has advanced past k",
        ),
        replace(
            SEED_V0,
            name="broken-d1-end-check",
            d1_end_check=False,
            fault="D1 accepts with any valid renewal, ignoring its end time",
        ),
        replace(
            SEED_V0,
            name="broken-d1-replay",
            replay_check=False,
            fault="D1 accepts the same command identifier more than once",
        ),
        replace(
            SEED_V0,
            name="broken-distinct-signers",
            distinct_signers=False,
            fault="validity counts signatures, not distinct signers",
        ),
        replace(
            SEED_V0,
            name="broken-commit-after-release",
            commit_before_release=False,
            fault="the signer releases a signature before its state is durable",
        ),
    )
}
RULESETS = {SEED_V0.name: SEED_V0, ORIG.name: ORIG, **BROKEN}


# --------------------------------------------------------------------------- signer


@dataclass
class SignerState:
    epoch: int = 1  # E_u
    max_end: int = 0  # M_u
    withdrawn: frozenset[int] = frozenset()  # X_u
    consents: frozenset[str] = frozenset()  # holders the person supports (an input)
    grants: dict[int, Grant] = field(
        default_factory=dict
    )  # volatile: valid grants held

    def durable(self) -> dict:
        return {
            "epoch": self.epoch,
            "max_end": self.max_end,
            "withdrawn": sorted(self.withdrawn),
            "consents": sorted(self.consents),
        }

    @classmethod
    def from_durable(cls, d: dict) -> SignerState:
        return cls(
            epoch=d["epoch"],
            max_end=d["max_end"],
            withdrawn=frozenset(d["withdrawn"]),
            consents=frozenset(d["consents"]),
        )


def check_renewal(
    rs: RuleSet, p: Params, st: SignerState, m: Renewal, clock: int
) -> str | None:
    """O1. Returns None if the signer may sign, else the reason it refuses."""
    if m.epoch not in st.grants:
        return "no-valid-grant"
    if rs.o1_epoch_guard and m.epoch != st.epoch:
        return "epoch-advanced" if m.epoch < st.epoch else "epoch-not-current"
    if m.epoch in st.withdrawn:
        return "withdrawn"
    if m.end > clock + p.H:
        return "beyond-horizon"
    return None


def check_grant(
    rs: RuleSet, p: Params, st: SignerState, m: Grant, clock: int
) -> str | None:
    """O2. The local clock is not used by O2; it is accepted for a uniform interface."""
    del clock
    if m.epoch <= st.epoch:
        return "epoch-not-higher"
    if rs.deputy:
        if m.deputy is None or m.deputy == m.holder:
            return "bad-deputy"
    elif m.deputy is not None:
        return "deputy-not-allowed"
    if m.holder not in st.consents:
        return "no-consent"
    fallback = p.F if rs.deputy else 0
    if rs.o2_start_guard and m.start < st.max_end + fallback + p.g:
        return "start-too-early"
    return None


# --------------------------------------------------------------------------- verifier


@dataclass
class VerifierState:
    grants: dict[int, list[Grant]] = field(
        default_factory=dict
    )  # valid grants by epoch
    renewals: dict[int, dict[int, Renewal]] = field(
        default_factory=dict
    )  # epoch -> end -> R
    accepted: set[tuple[int | None, str, str]] = field(default_factory=set)  # durable
    anchor: dict[int, int] = field(default_factory=dict)  # orig D2: fixed anchors


def _renewal_for(
    rs: RuleSet, vs: VerifierState, epoch: int, tau: int
) -> tuple[Renewal | None, str]:
    by_end = vs.renewals.get(epoch, {})
    if not by_end:
        return None, "no-renewal"
    if not rs.d1_end_check:
        return by_end[max(by_end)], ""
    current = [e for e in by_end if e >= tau]
    if not current:
        return None, "expired"
    return by_end[max(current)], ""


def check_command(
    rs: RuleSet, p: Params, vs: VerifierState, cmd: Command, tau: int
) -> tuple[str | None, str | None, tuple[Message, ...]]:
    """D1 (and D2 for the orig rule set). Returns (reason, rule, evidence).
    reason is None when the command is accepted."""
    grants = vs.grants.get(cmd.epoch, [])
    reason = "no-grant"
    for g in grants:
        if g.holder != cmd.holder:
            reason = "not-holder"
            continue
        if tau < g.start:
            reason = "not-started"
            continue
        r, why = _renewal_for(rs, vs, cmd.epoch, tau)
        if r is None:
            reason = why
            continue
        if rs.replay_check and (cmd.epoch, cmd.holder, cmd.cid) in vs.accepted:
            return "replay", None, ()
        return None, "D1", (g, r)
    if rs.deputy and p.F > 0:
        for g in grants:
            if g.deputy != cmd.holder:
                continue
            if tau < g.start:
                reason = "not-started"
                continue
            ends = vs.renewals.get(cmd.epoch, {})
            if not ends:
                reason = "no-renewal"
                continue
            if any(e >= tau for e in ends):
                reason = "commander-current"
                continue
            a = vs.anchor.get(cmd.epoch, max(ends))
            if not (a < tau <= a + p.F):
                reason = "outside-fallback"
                continue
            if rs.replay_check and (cmd.epoch, cmd.holder, cmd.cid) in vs.accepted:
                return "replay", None, ()
            return None, "D2", (g, ends[a] if a in ends else ends[max(ends)])
    return reason, None, ()


def commit_acceptance(
    vs: VerifierState, cmd: Command, rule: str, evidence: tuple
) -> None:
    vs.accepted.add((cmd.epoch, cmd.holder, cmd.cid))
    if rule == "D2" and cmd.epoch not in vs.anchor:
        vs.anchor[cmd.epoch] = evidence[1].end


# --------------------------------------------------------------------------- adapter


class MandateProtocol:
    """Uniform interface used by the simulator (sim/engine.py)."""

    family = "mandate"

    def __init__(self, rs: RuleSet, p: Params, genesis: Grant):
        if not rs.deputy and p.F != 0:
            raise ValueError(f"{rs.name} requires F = 0")
        if genesis.epoch != 1:
            raise ValueError("the genesis grant has epoch 1")
        self.rs, self.p, self.genesis = rs, p, genesis
        self.name = rs.name
        self.commit_before_release = rs.commit_before_release
        self.distinct_signers = rs.distinct_signers

    # signer side
    def new_signer(self, init: dict) -> SignerState:
        st = SignerState.from_durable(
            {"epoch": 1, "max_end": 0, "withdrawn": [], "consents": [], **init}
        )
        st.grants[1] = self.genesis
        return st

    def restore_signer(self, durable: dict) -> SignerState:
        st = SignerState.from_durable(durable)
        st.grants[1] = self.genesis  # configuration, not durable state
        return st

    def durable(self, st: SignerState) -> dict:
        return st.durable()

    def check_sign(self, st: SignerState, m: Message, clock: int) -> str | None:
        if isinstance(m, Renewal):
            return check_renewal(self.rs, self.p, st, m, clock)
        if isinstance(m, Grant):
            return check_grant(self.rs, self.p, st, m, clock)
        return "unknown-message"

    def apply_sign(self, st: SignerState, m: Message) -> list[dict]:
        if isinstance(m, Renewal):
            st.max_end = max(st.max_end, m.end)
            return []
        old = st.epoch
        st.epoch = m.epoch
        return [{"ev": "advance", "from": old, "to": m.epoch, "cause": "signed-grant"}]

    def learn(self, st: SignerState, m: Message) -> list[dict]:
        if not isinstance(m, Grant):
            return []
        st.grants.setdefault(m.epoch, m)
        if m.epoch > st.epoch:
            old = st.epoch
            st.epoch = m.epoch
            return [
                {"ev": "advance", "from": old, "to": m.epoch, "cause": "valid-grant"}
            ]
        return []

    def withdraw(self, st: SignerState, target: dict) -> dict:
        k = target["epoch"]
        st.withdrawn = st.withdrawn | {k}
        return {"epoch": k}

    def set_consent(self, st: SignerState, holder: str, value: bool) -> None:
        st.consents = st.consents | {holder} if value else st.consents - {holder}

    # verifier side
    def new_verifier(self) -> VerifierState:
        vs = VerifierState()
        vs.grants[1] = [self.genesis]
        return vs

    def store(self, vs: VerifierState, m: Message) -> None:
        if isinstance(m, Grant):
            known = vs.grants.setdefault(m.epoch, [])
            if m not in known:
                known.append(m)
        elif isinstance(m, Renewal):
            vs.renewals.setdefault(m.epoch, {})[m.end] = m

    def check_command(self, vs: VerifierState, cmd: Command, tau: int, attached: tuple):
        del attached
        return check_command(self.rs, self.p, vs, cmd, tau)

    def commit(
        self, vs: VerifierState, cmd: Command, rule: str, evidence: tuple
    ) -> None:
        commit_acceptance(vs, cmd, rule, evidence)
