"""Comparison mechanisms, as mechanism abstractions (spec/protocol.md, s. 14).

These are NOT reproductions of published systems.

* ``tc``: threshold-issued expiring credentials. A credential Lease(h, s, e) is valid with
  q distinct officer signatures; an honest officer signs it if the person consents to h
  and e <= C_u + H. There is no exclusive-succession rule. This abstracts the renewal and
  expiry mechanism that threshold credential systems share; it does not model URSA's or
  HRCred's other features.
* ``xl``: exclusive leases with Byzantine quorums. Our adaptation of the grantor-side
  exclusivity rule of quorum leases (Nerio, crash faults) to signed, windowed credentials
  verified at the device. Nerio's authors did not propose or evaluate this adaptation.
  Signer state: A_u (current holder), S_u (earliest start allowed for A_u), F_u (largest
  end time signed). Sign Lease(h, s, e) only if the person consents to h, s <= e <= C_u + H,
  and either h = A_u and s >= S_u, or h != A_u and s >= F_u + g. On a change of holder,
  A_u := h and S_u := s; always F_u := max(F_u, e).
* ``qo-w``: quorum per order with a validity window W. Each command needs q distinct
  officer signatures on Order(h, cid, payload, s, e) with s <= e <= C_u + W. No nonce or
  challenge from the verifier (that variant is specified in research/roadmap.md, not
  implemented).

All three verify at the device with the same clock bound as Mandate and keep replay
protection per verifier.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from mandate.messages import Command, Lease, Message, Order


@dataclass
class LeaseSignerState:
    consents: frozenset[str] = frozenset()
    holder: str | None = None  # A_u (xl only)
    floor: int = 0  # S_u (xl only)
    max_end: int = 0  # F_u (xl only)

    def durable(self) -> dict:
        return {
            "consents": sorted(self.consents),
            "holder": self.holder,
            "floor": self.floor,
            "max_end": self.max_end,
        }

    @classmethod
    def from_durable(cls, d: dict) -> LeaseSignerState:
        return cls(frozenset(d["consents"]), d["holder"], d["floor"], d["max_end"])


@dataclass
class LeaseVerifierState:
    leases: dict[str, list[Lease]] = field(
        default_factory=dict
    )  # holder -> valid leases
    orders: dict[tuple[str, str], list[Order]] = field(default_factory=dict)  # (h, cid)
    accepted: set[tuple[None, str, str]] = field(default_factory=set)


class _Base:
    commit_before_release = True
    distinct_signers = True

    def __init__(self, p, W: int | None = None):
        self.p = p
        self.W = W

    def new_signer(self, init: dict) -> LeaseSignerState:
        d = {"consents": [], "holder": None, "floor": 0, "max_end": 0, **init}
        return LeaseSignerState.from_durable(d)

    def restore_signer(self, durable: dict) -> LeaseSignerState:
        return LeaseSignerState.from_durable(durable)

    def durable(self, st: LeaseSignerState) -> dict:
        return st.durable()

    def learn(self, st, m: Message) -> list[dict]:
        return []

    def withdraw(self, st: LeaseSignerState, target: dict) -> dict:
        h = target["holder"]
        st.consents = st.consents - {h}
        return {"holder": h}

    def set_consent(self, st: LeaseSignerState, holder: str, value: bool) -> None:
        st.consents = st.consents | {holder} if value else st.consents - {holder}

    def new_verifier(self) -> LeaseVerifierState:
        return LeaseVerifierState()

    def store(self, vs: LeaseVerifierState, m: Message) -> None:
        if isinstance(m, Lease):
            known = vs.leases.setdefault(m.holder, [])
            if m not in known:
                known.append(m)
        elif isinstance(m, Order):
            known = vs.orders.setdefault((m.holder, m.cid), [])
            if m not in known:
                known.append(m)

    def commit(self, vs: LeaseVerifierState, cmd: Command, rule: str, evidence) -> None:
        vs.accepted.add((None, cmd.holder, cmd.cid))


class _LeaseVerify(_Base):
    def check_command(self, vs: LeaseVerifierState, cmd: Command, tau: int, attached):
        if cmd.epoch is not None:
            return "bad-command", None, ()
        leases = vs.leases.get(cmd.holder, [])
        if not leases:
            return "no-lease", None, ()
        current = [x for x in leases if x.start <= tau <= x.end]
        if not current:
            return (
                ("not-started" if all(tau < x.start for x in leases) else "expired"),
                None,
                (),
            )
        if (None, cmd.holder, cmd.cid) in vs.accepted:
            return "replay", None, ()
        best = max(current, key=lambda x: (x.end, -x.start))
        return None, "LEASE", (best,)


class TCProtocol(_LeaseVerify):
    name = "tc"
    family = "lease"

    def check_sign(self, st: LeaseSignerState, m: Message, clock: int) -> str | None:
        if not isinstance(m, Lease):
            return "unknown-message"
        if m.holder not in st.consents:
            return "no-consent"
        if m.start > m.end:
            return "empty-window"
        if m.end > clock + self.p.H:
            return "beyond-horizon"
        return None

    def apply_sign(self, st: LeaseSignerState, m: Message) -> list[dict]:
        return []


class XLProtocol(_LeaseVerify):
    name = "xl"
    family = "lease"

    def check_sign(self, st: LeaseSignerState, m: Message, clock: int) -> str | None:
        reason = TCProtocol.check_sign(self, st, m, clock)  # same base conditions
        if reason:
            return reason
        if m.holder == st.holder:
            return None if m.start >= st.floor else "start-before-floor"
        return None if m.start >= st.max_end + self.p.g else "start-too-early"

    def apply_sign(self, st: LeaseSignerState, m: Message) -> list[dict]:
        notes = []
        if m.holder != st.holder:
            notes.append({"ev": "switch", "from": st.holder, "to": m.holder})
            st.holder, st.floor = m.holder, m.start
        st.max_end = max(st.max_end, m.end)
        return notes


class QOWProtocol(_Base):
    name = "qo-w"
    family = "order"

    def check_sign(self, st: LeaseSignerState, m: Message, clock: int) -> str | None:
        if not isinstance(m, Order):
            return "unknown-message"
        if m.holder not in st.consents:
            return "no-consent"
        if m.start > m.end:
            return "empty-window"
        if m.end > clock + self.W:
            return "beyond-window"
        return None

    def apply_sign(self, st: LeaseSignerState, m: Message) -> list[dict]:
        return []

    def check_command(self, vs: LeaseVerifierState, cmd: Command, tau: int, attached):
        if cmd.epoch is not None:
            return "bad-command", None, ()
        orders = [
            o
            for o in vs.orders.get((cmd.holder, cmd.cid), [])
            if o.payload == cmd.payload
        ]
        if not orders:
            return "no-order", None, ()
        current = [o for o in orders if o.start <= tau <= o.end]
        if not current:
            return (
                ("not-started" if all(tau < o.start for o in orders) else "expired"),
                None,
                (),
            )
        if (None, cmd.holder, cmd.cid) in vs.accepted:
            return "replay", None, ()
        return None, "ORDER", (max(current, key=lambda o: o.end),)


def make_baseline(name: str, p, W: int | None):
    if name == "tc":
        return TCProtocol(p)
    if name == "xl":
        return XLProtocol(p)
    if name == "qo-w":
        if W is None or W <= 0:
            raise ValueError("qo-w needs a window W > 0")
        return QOWProtocol(p, W)
    raise KeyError(name)
