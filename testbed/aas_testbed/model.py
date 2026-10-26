"""The journal rules of the scenario-and-model document, as pure functions.

Everything here is deterministic and reads only what a device holds: signed records and
their GNSS timestamps (``Record.ts``). ``Record.true_ts`` is simulation truth; only the
truth oracle reads it, by passing ``truth=True``.

Rules implemented (model document, section "The rules of the journal"):

* Who held command when: start from C's grant, apply succession acts in timestamp order,
  and drop acts the signer was not entitled to make at that moment.
* Status of a decision: valid if its signer held command at its timestamp; residual if
  not; in doubt if a change of command involving the signer lies within the clock-error
  bound; a valid decision is provisional until settled, then authoritative.
* Settlement: the regional server confirms a decision once it holds every authority
  record that anyone entitled to change command could have signed before it.

Where the document is silent, the choice made here is marked ``MODEL CHOICE`` so that it
can be argued with.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from enum import StrEnum


class Kind(StrEnum):
    GRANT = "grant"  # C appoints the first commander
    RULE = "rule"  # C signs a succession rule in advance (S4, S5)
    HANDOVER = "handover"  # the holder hands command to someone
    TAKEOVER = "takeover"  # C takes command, appointing someone (possibly C)
    ACTIVATION = "activation"  # a deputy activates under a rule after silence
    PROMOTION = "promotion"  # the operator promotes someone through the server (S1, S2)
    ACCEPTANCE = "acceptance"  # the appointee accepts a takeover or promotion
    DECISION = "decision"  # a command decision
    CONFIRMATION = "confirmation"  # the server confirms that a decision is settled


# Acts that can change who holds command.
SUCCESSION_KINDS = frozenset(
    {Kind.GRANT, Kind.HANDOVER, Kind.TAKEOVER, Kind.ACTIVATION, Kind.PROMOTION,
     Kind.ACCEPTANCE}
)
# Every record a verdict can depend on.
AUTHORITY_KINDS = SUCCESSION_KINDS | {Kind.RULE}
# Acts whose validity does not depend on who held command before them.
UNCONDITIONAL_KINDS = frozenset(
    {Kind.GRANT, Kind.TAKEOVER, Kind.PROMOTION, Kind.ACCEPTANCE}
)
APPOINTMENTS = frozenset({Kind.TAKEOVER, Kind.PROMOTION})


class Status(StrEnum):
    AUTHORITATIVE = "authoritative"
    PROVISIONAL = "provisional"
    RESIDUAL = "residual"
    IN_DOUBT = "in_doubt"


VALID_LOOKING = frozenset({Status.AUTHORITATIVE, Status.PROVISIONAL})


@dataclass(frozen=True, slots=True)
class Record:
    """One signed, immutable record. Fields beyond the first seven depend on ``kind``."""

    rid: str
    kind: Kind
    signer: str
    device: str
    pseq: int  # per-person sequence number (0 for server-signed confirmations)
    ts: float  # GNSS time at the signer's device
    true_ts: float  # simulation truth; read only by the truth oracle
    subject: str | None = None  # grantee, appointee, handover target, rule deputy, or crew
    primary: str | None = None  # RULE: whose silence the rule is about
    timeout: float | None = None  # RULE: T, the deputy's silence threshold
    primary_timeout: float | None = None  # RULE: T', the primary's own timeout
    rule: str | None = None  # ACTIVATION: the rule invoked
    last_heard: float | None = None  # ACTIVATION: GNSS ts of the primary's last heartbeat
    grant_ref: str | None = None  # DECISION: the act the signer believed made them holder
    value: str | None = None  # DECISION: the order itself
    decision: str | None = None  # CONFIRMATION: the decision confirmed
    accepts: str | None = None  # ACCEPTANCE: the takeover or promotion accepted
    covers: frozenset[str] = field(default_factory=frozenset)  # CONFIRMATION: its basis


@dataclass(frozen=True, slots=True)
class Org:
    """What the organization fixes in advance."""

    appointing: frozenset[str] = frozenset({"C", "OP"})  # may appoint unconditionally
    at_server: frozenset[str] = frozenset({"C", "OP"})  # sign only at the regional server
    # When a takeover or promotion takes effect: at its "signature" (the document), or at
    # the appointee's "acceptance" (a proposed fix; handovers are not affected).
    effect: str = "signature"


@dataclass(frozen=True, slots=True)
class Segment:
    """``holder`` holds command from ``start`` until the next segment starts."""

    start: float
    holder: str | None
    prev: str | None
    act: str
    kind: Kind


@dataclass(frozen=True, slots=True)
class Verdict:
    status: Status
    reason: str


def _key(r: Record, truth: bool) -> float:
    return r.true_ts if truth else r.ts


def _rank(r: Record, org: Org) -> int:
    # MODEL CHOICE: at an exact timestamp tie, the appointing authority's act is applied
    # first, then a handover, then an activation ("a superior's act outranks a
    # subordinate's"). Ties within the clock-error bound are left to the in-doubt status.
    if r.signer in org.appointing:
        return 0
    if r.kind is Kind.HANDOVER:
        return 1
    return 2


def timeline(records: Iterable[Record], org: Org, *, truth: bool = False) -> list[Segment]:
    """Who held command when, from the authority records given."""
    rules: dict[str, Record] = {}
    appointments: dict[str, Record] = {}
    acts: list[Record] = []
    for r in records:
        if r.kind is Kind.RULE:
            rules[r.rid] = r
        elif r.kind in SUCCESSION_KINDS:
            if r.kind in APPOINTMENTS:
                appointments[r.rid] = r
                if org.effect == "acceptance":
                    continue  # takes effect through its acceptance
            elif r.kind is Kind.ACCEPTANCE and org.effect != "acceptance":
                continue
            acts.append(r)
    acts.sort(key=lambda r: (_key(r, truth), _rank(r, org), r.rid))

    segments: list[Segment] = []
    holder: str | None = None
    appointed_at = -math.inf  # when the act behind the latest appointment was signed
    for act in acts:
        if act.kind is Kind.ACCEPTANCE:
            appt = appointments.get(act.accepts or "")
            # MODEL CHOICE: an appointment older than the one in force can no longer be
            # accepted; otherwise a stale takeover could override a newer one.
            if appt is None or _key(appt, truth) < appointed_at:
                continue
        new = _apply(act, holder, rules, appointments, org, truth)
        if new is None:
            continue
        if act.kind is Kind.ACCEPTANCE:
            appointed_at = _key(appointments[act.accepts or ""], truth)
        elif act.kind in UNCONDITIONAL_KINDS:
            appointed_at = _key(act, truth)
        segments.append(Segment(_key(act, truth), new, holder, act.rid, act.kind))
        holder = new
    return segments


def _apply(
    act: Record,
    holder: str | None,
    rules: Mapping[str, Record],
    appointments: Mapping[str, Record],
    org: Org,
    truth: bool,
) -> str | None:
    """The new holder if ``act`` is valid given the current holder, else None."""
    # Acceptances and activations are not checked against the timestamp of the
    # appointment or rule they cite: a device can only cite a record it holds, so the
    # order is causal, and comparing two devices' clocks would misjudge it by up to eps.
    if act.kind is Kind.ACCEPTANCE:
        appt = appointments.get(act.accepts or "")
        if appt is None or appt.signer not in org.appointing or appt.subject != act.signer:
            return None
        return act.signer
    if act.kind in UNCONDITIONAL_KINDS:
        return act.subject if act.signer in org.appointing else None
    if act.kind is Kind.HANDOVER:
        return act.subject if holder == act.signer and act.subject != act.signer else None
    if act.kind is Kind.ACTIVATION:
        rule = rules.get(act.rule or "")
        if rule is None or rule.signer not in org.appointing:
            return None
        if rule.subject != act.signer or holder != rule.primary:
            return None
        # MODEL CHOICE: the silence condition is the deputy device's own measurement,
        # recorded in the activation (nodes are not Byzantine). The truth oracle accepts
        # the same measurement instead of re-deriving silence in true time; otherwise a
        # sub-second clock error would invalidate a deputy's whole tenure.
        if act.last_heard is None or rule.timeout is None:
            return None
        return act.signer if act.ts - act.last_heard >= rule.timeout else None
    return None


def holder_at(segments: list[Segment], t: float) -> str | None:
    holder = None
    for seg in segments:
        if seg.start <= t:
            holder = seg.holder
        else:
            break
    return holder


def act_at(segments: list[Segment], t: float) -> str | None:
    """The act under which the holder at ``t`` holds command."""
    act = None
    for seg in segments:
        if seg.start <= t:
            act = seg.act
        else:
            break
    return act


def classify(
    d: Record,
    segments: list[Segment],
    eps: float,
    *,
    held: Mapping[str, Record] | None = None,
    settled: bool = False,
    truth: bool = False,
) -> Verdict:
    """The status of decision ``d`` given a device's timeline.

    ``held`` is the device's record store, used to keep a decision provisional while an
    authority record it depends on has not arrived. The truth oracle passes ``held=None``
    and ``eps=0``.
    """
    t = _key(d, truth)
    if held is not None and d.grant_ref is not None:
        ref = held.get(d.grant_ref)
        missing = ref is None or (
            (ref.kind is Kind.ACTIVATION and (ref.rule or "") not in held)
            or (ref.kind is Kind.ACCEPTANCE and (ref.accepts or "") not in held)
        )
        if missing:
            return Verdict(Status.PROVISIONAL, "missing_dependency")
    for seg in segments:
        if seg.prev == seg.holder:
            continue
        if abs(seg.start - t) <= eps and d.signer in (seg.holder, seg.prev):
            return Verdict(Status.IN_DOUBT, "near_change")
    if holder_at(segments, t) == d.signer:
        if settled:
            return Verdict(Status.AUTHORITATIVE, "settled")
        return Verdict(Status.PROVISIONAL, "unsettled")
    if any(seg.holder == d.signer and seg.start <= t for seg in segments):
        return Verdict(Status.RESIDUAL, "superseded")
    # MODEL CHOICE: the document defines residual as "made under a grant that had already
    # been superseded". A decision made under a grant that was never valid (for example a
    # deputy's activation overruled by an earlier handover) gets the same status, with its
    # own reason, because it too must be kept and never merged.
    return Verdict(Status.RESIDUAL, "no_valid_grant")


def required_signers(
    t: float,
    segments: list[Segment],
    authority: Iterable[Record],
    all_persons: Iterable[str],
    org: Org,
    eps: float,
    mode: str,
) -> frozenset[str]:
    """Whose records the server must hold up to ``t + eps`` before settling at ``t``.

    ``strict`` is the document's rule read literally: every person who has signed, or is
    named in, any authority record. ``closing`` is our refinement: an unconditional act
    (grant, takeover, promotion) overrides everything before it, so only the appointing
    authority, the holders since the latest such act, and the deputies of those holders
    can still change who held command at ``t``. Under the acceptance effect, anyone named
    in an appointment not yet accepted can still change it too, by accepting.
    """
    authority = list(authority)
    rules = [r for r in authority if r.kind is Kind.RULE]
    accepted = {r.accepts for r in authority if r.kind is Kind.ACCEPTANCE}
    pending = {
        r.subject for r in authority
        if r.kind in APPOINTMENTS and r.rid not in accepted and r.ts <= t + eps
        and r.subject is not None
    } if org.effect == "acceptance" else set()
    if mode == "strict":
        return frozenset(all_persons) | org.appointing | pending
    if mode != "closing":
        raise ValueError(f"unknown settlement mode {mode!r}")
    horizon = t + eps
    # The latest unconditional act before the in-doubt window around t: nothing signed
    # before it can change who held command at t, or whether t is close to a change.
    start = 0
    for i, seg in enumerate(segments):
        if seg.start > t - eps:
            break
        if seg.kind in UNCONDITIONAL_KINDS:
            start = i
    chain = {
        seg.holder
        for seg in segments[start:]
        if seg.start <= horizon and seg.holder is not None
    }
    deputies = {r.subject for r in rules if r.primary in chain and r.subject is not None}
    return frozenset(org.appointing | chain | deputies | pending)
