"""Discrete-event simulation of one incident under one succession policy.

Devices hold signed records and exchange them by gossip whenever a link is up (the model
document: "devices exchange records whenever some link is up"). Each device also sends
heartbeats, which is how silence is measured. Every decision a person attempts goes
through their own device's enforcement, using only what that device holds. The truth
oracle and the metrics live in ``metrics.py``.
"""

from __future__ import annotations

import heapq
import itertools
import math
import random
from collections.abc import Callable
from dataclasses import dataclass
from typing import NamedTuple

from .model import (
    AUTHORITY_KINDS,
    Kind,
    Org,
    Record,
    Segment,
    Status,
    Verdict,
    act_at,
    classify,
    holder_at,
    required_signers,
    timeline,
)
from .network import (
    CREWS,
    DEVICES,
    PERSON_DEVICE,
    SERVER,
    Interval,
    Link,
    apply_case,
    forest_fire_links,
    random_flaps,
)
from .policies import Policy

# People who may hold command in the scenario, and so may attempt decisions.
DECIDERS = ("A", "B", "S", "C")


@dataclass
class Config:
    policy: Policy
    case: str = "P-A"
    a_state: str = "alive"  # "alive": cut off but working; "incapacitated" at t_cut
    a_device_lost: bool = False  # A's device goes dark at t_cut and never comes back
    t_cut: float = 600.0
    outage: float = 1200.0
    tail: float = 900.0  # every link up after the outage, for convergence and settlement
    warmup: float = 60.0  # no decisions before this
    quiesce: float = 300.0  # no decisions in the last this-many seconds of the run
    decision_rate: float = 1 / 60  # per person, while they believe they hold command
    sync_period: float = 2.0
    hb_period: float = 2.0
    control_period: float = 1.0
    confirm_period: float = 5.0
    probe_period: float = 1.0
    eps: float = 0.2  # bound on pairwise clock error, s
    clock: str = "uniform"  # "uniform" in [-eps/2, eps/2], "adversarial", or "zero"
    a_clock_error: float = 0.0  # fault: extra offset on A's device, beyond the bound
    settlement: str = "closing"  # or "strict" (see model.required_signers)
    presence: str = "device"  # heartbeats prove the "device" is up, or the "person" is fit
    detect: float = 120.0  # data silence before the operator or C reacts, s
    voice_call: float = 60.0  # how long C tries A on voice, s
    a_answers_voice: bool = True  # an alive A answers C's call
    report_delay: float = 300.0  # incapacitated A: when someone tells the centre by voice
    recall: float = 600.0  # after A answers, C waits this long before calling again
    reach: float = 10.0  # the core counts a device as reachable within this silence, s
    b_react: float = 0.0  # deputy's delay between the offer and signing the activation
    a_ignores_timeout: bool = False  # fault: A's device does not stop at T'
    # Proposed fix: a lease or T' runs from the last of this device's own heartbeats the
    # other side is known to have received, not from the last time it heard the other side.
    acked: bool = False
    effect: str = "signature"  # or "acceptance": see model.Org.effect
    oneway: str | None = None  # fault (P-A): A's device is "mute" or "deaf"
    handover_to_s_after: float | None = None  # fault: A hands over to S after the cut
    # Fault: store-and-forward relay. A is cut off; at t_cut + 200 s V1 loses B and the
    # core; at t_cut + T + 30 s A's Wi-Fi to V1 returns, and V1 hands A a heartbeat of B's
    # older than B's activation, without the activation. Overrides ``case``.
    relay_fault: bool = False
    flaps: tuple[float, float] | None = None  # (mean up, mean down): random link flapping
    latency: dict[str, float] | None = None
    contradiction_window: float = 300.0
    seed: int = 0

    @property
    def t_end(self) -> float:
        return self.t_cut + self.outage + self.tail


class Heartbeat(NamedTuple):
    ts: float  # GNSS time at the sending device
    true_ts: float
    person: str | None  # the device's user, if any
    last_pseq: int  # that person's latest sequence number at ts: a completeness proof
    present: bool  # the beat counts as a sign of life (see Config.presence)
    # The sender's latest known heartbeat time from each other device: lets a device learn
    # which of its own heartbeats the sender has received (Config.acked).
    heard: tuple[tuple[str, float], ...] = ()


@dataclass(slots=True)
class Attempt:
    t: float
    person: str
    accepted: bool
    reason: str
    rid: str | None


class Device:
    def __init__(self, name: str, offset: float, org: Org) -> None:
        self.name = name
        self.offset = offset
        self.org = org
        self.records: dict[str, Record] = {}
        self.authority: dict[str, Record] = {}
        self.log: list[str] = []
        self.arrival: dict[str, float] = {}  # rid -> true time of arrival
        # Latest heartbeat known per (sending device, present). Under "person" presence a
        # device keeps beating after its user is unfit, with present=False: it still
        # proves what the user has signed, but no longer that the user is there, so the
        # last beat that did must not be overwritten.
        self.hb: dict[tuple[str, bool], Heartbeat] = {}
        self.first_seen: dict[str, Verdict] = {}  # decision rid -> verdict on arrival
        self.auth_seen: dict[str, float] = {}  # decision rid -> true time first authoritative
        self.pseqs: dict[str, set[int]] = {}
        self.contiguous: dict[str, int] = {}
        self._segments: list[Segment] | None = None

    def local(self, t: float) -> float:
        return t + self.offset

    def segments(self) -> list[Segment]:
        if self._segments is None:
            self._segments = timeline(self.authority.values(), self.org)
        return self._segments

    def rules(self) -> list[Record]:
        return [r for r in self.authority.values() if r.kind is Kind.RULE]

    def settled(self, d: Record) -> bool:
        conf = self.records.get(f"conf-{d.rid}")
        return conf is not None and all(rid in self.records for rid in conf.covers)

    def verdict(self, d: Record, eps: float) -> Verdict:
        return classify(d, self.segments(), eps, held=self.records, settled=self.settled(d))

    def add(self, r: Record, t: float, eps: float) -> bool:
        if r.rid in self.records:
            return False
        self.records[r.rid] = r
        self.log.append(r.rid)
        self.arrival[r.rid] = t
        if r.signer not in ("core",):
            seen = self.pseqs.setdefault(r.signer, set())
            seen.add(r.pseq)
            k = self.contiguous.get(r.signer, 0)
            while k + 1 in seen:
                k += 1
            self.contiguous[r.signer] = k
        if r.kind in AUTHORITY_KINDS:
            self.authority[r.rid] = r
            self._segments = None
            self._recheck_authoritative(t, eps)
        elif r.kind is Kind.DECISION:
            v = self.verdict(r, eps)
            self.first_seen[r.rid] = v
            if v.status is Status.AUTHORITATIVE:
                self.auth_seen.setdefault(r.rid, t)
        elif r.kind is Kind.CONFIRMATION:
            d = self.records.get(r.decision or "")
            if d is not None and self.verdict(d, eps).status is Status.AUTHORITATIVE:
                self.auth_seen.setdefault(d.rid, t)
        return True

    def _recheck_authoritative(self, t: float, eps: float) -> None:
        # A confirmation's basis may complete only when an authority record arrives.
        for r in self.records.values():
            if r.kind is Kind.CONFIRMATION and r.decision not in self.auth_seen:
                d = self.records.get(r.decision or "")
                if d is not None and self.verdict(d, eps).status is Status.AUTHORITATIVE:
                    self.auth_seen[d.rid] = t

    def merge_heartbeats(self, hb: dict[tuple[str, bool], Heartbeat]) -> None:
        for key, beat in hb.items():
            mine = self.hb.get(key)
            if mine is None or beat.ts > mine.ts:
                self.hb[key] = beat

    def silence_from_device(self, t: float, device: str) -> float:
        if device == self.name:
            return 0.0
        latest = max((b.ts for (d, _), b in self.hb.items() if d == device), default=None)
        return math.inf if latest is None else self.local(t) - latest

    def latest_from_person(self, person: str) -> Heartbeat | None:
        """The latest sign of life from ``person``."""
        best = None
        for beat in self.hb.values():
            if beat.person == person and beat.present and (best is None or beat.ts > best.ts):
                best = beat
        return best

    def latest_from_device(self, device: str) -> Heartbeat | None:
        best = None
        for (d, _), beat in self.hb.items():
            if d == device and (best is None or beat.ts > best.ts):
                best = beat
        return best

    def acked_silence(self, t: float, beat: Heartbeat | None) -> float:
        """Time since the latest of this device's heartbeats that ``beat``'s sender had."""
        if beat is None:
            return math.inf
        mine = dict(beat.heard).get(self.name)
        return math.inf if mine is None else self.local(t) - mine

    def heard_vector(self) -> tuple[tuple[str, float], ...]:
        latest: dict[str, float] = {}
        for (d, _), beat in self.hb.items():
            if d != self.name and beat.ts > latest.get(d, -math.inf):
                latest[d] = beat.ts
        return tuple(sorted(latest.items()))

    def silence_from_person(self, t: float, person: str) -> float:
        beat = self.latest_from_person(person)
        return math.inf if beat is None else self.local(t) - beat.ts


class Sim:
    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg
        self.rng = random.Random(cfg.seed)
        self.org = Org(effect=cfg.effect)
        self.links: list[Link] = forest_fire_links(cfg.latency)
        if cfg.flaps is not None:
            mean_up, mean_down = cfg.flaps
            random_flaps(self.links, self.rng, cfg.t_cut + cfg.outage, mean_up=mean_up,
                         mean_down=mean_down, start=cfg.warmup)
        elif cfg.relay_fault:
            self._relay_fault()
        elif cfg.case != "none":
            apply_case(self.links, cfg.case, cfg.t_cut, cfg.outage, oneway=cfg.oneway)
        if cfg.a_device_lost:
            for link in self.links:
                if PERSON_DEVICE["A"] in (link.a, link.b):
                    link.cut(Interval(cfg.t_cut, math.inf))
        self.devices = {name: Device(name, self._offset(name), self.org) for name in DEVICES}
        self.pseq: dict[str, int] = dict.fromkeys(("A", "B", "S", "C", "OP"), 0)
        self._queue: list[tuple[float, int, Callable[..., None], tuple]] = []
        self._tick = itertools.count()
        self._cursor: dict[tuple[int, str], int] = {}
        self.t = 0.0
        self.attempts: list[Attempt] = []
        self.acts: list[Record] = []
        self.decisions: list[Record] = []
        self.probes: list[tuple[float, frozenset[str]]] = []
        self.confirmed: dict[str, float] = {}  # decision rid -> true time of confirmation
        self.trace: list[tuple[float, str]] = []
        self._pending: set[str] = set()
        self._promoted = False
        self._c_state = "idle"  # idle -> calling -> idle (A answered) | done (took over)
        self._c_call_end = 0.0
        self._c_quiet_until = -math.inf
        self._report_handled = False

    # -- set-up -------------------------------------------------------------------------

    def _offset(self, device: str) -> float:
        cfg = self.cfg
        half = cfg.eps / 2
        if cfg.clock == "zero":
            off = 0.0
        elif cfg.clock == "adversarial":
            # Worst case for S4's margin: A's clock behind, B's ahead.
            off = {"HA": -half, "V2": half}.get(device, 0.0)
        elif cfg.clock == "uniform":
            off = self.rng.uniform(-half, half)
        else:
            raise ValueError(f"unknown clock model {cfg.clock!r}")
        if device == PERSON_DEVICE["A"]:
            off += cfg.a_clock_error
        return off

    def _relay_fault(self) -> None:
        cfg = self.cfg
        t0, heal = cfg.t_cut, cfg.t_cut + cfg.outage
        back = t0 + (cfg.policy.deputy_timeout or 300.0) + 30.0
        for link in self.links:
            ends = {link.a, link.b}
            if "HA" in ends:
                link.cut(Interval(t0, back if ends == {"HA", "V1"} else heal))
            elif "V1" in ends:
                link.cut(Interval(t0 + 200.0, heal))

    def at(self, t: float, fn: Callable[..., None], *args) -> None:
        heapq.heappush(self._queue, (t, next(self._tick), fn, args))

    def log(self, msg: str) -> None:
        self.trace.append((self.t, msg))

    def run(self) -> Sim:
        cfg = self.cfg
        self.at(0.0, self._appoint)
        for i, link in enumerate(self.links):
            for src in (link.a, link.b):
                self.at(self.rng.uniform(0, cfg.sync_period), self._sync, i, src)
        for name in DEVICES:
            self.at(self.rng.uniform(0, cfg.hb_period), self._heartbeat, name)
        for person in DECIDERS:
            self.at(cfg.warmup + self.rng.expovariate(cfg.decision_rate), self._decide, person)
        self.at(0.5, self._control)
        self.at(cfg.confirm_period, self._confirm)
        self.at(cfg.warmup, self._probe)
        self.at(cfg.t_cut, self.log, self._cut_message())
        if cfg.flaps is None and (cfg.case != "none" or cfg.relay_fault):
            name = "relay fault" if cfg.relay_fault else cfg.case
            self.at(cfg.t_cut + cfg.outage, self.log, f"{name} heals")
        if cfg.handover_to_s_after is not None:
            self.at(cfg.t_cut + cfg.handover_to_s_after, self._handover, "A", "S")
        while self._queue:
            t, _, fn, args = heapq.heappop(self._queue)
            if t > cfg.t_end:
                break
            self.t = t
            fn(*args)
        self.t = cfg.t_end
        return self

    def _cut_message(self) -> str:
        cfg = self.cfg
        if cfg.flaps is not None:
            what = "random link flapping"
        elif cfg.relay_fault:
            what = "relay fault (A cut off; V1 later relays a stale heartbeat of B's)"
        else:
            what = f"case {cfg.case}"
        state = "A incapacitated" if cfg.a_state == "incapacitated" else "A keeps working"
        return f"{what} begins; {state}"

    # -- people -------------------------------------------------------------------------

    def able(self, person: str, t: float | None = None) -> bool:
        t = self.t if t is None else t
        if person == "A" and self.cfg.a_state == "incapacitated":
            return t < self.cfg.t_cut
        return True

    def sign(self, person: str, kind: Kind, **fields) -> Record:
        dev = self.devices[PERSON_DEVICE[person]]
        self.pseq[person] += 1
        r = Record(
            rid=f"{kind.value}-{person}-{self.pseq[person]}",
            kind=kind,
            signer=person,
            device=dev.name,
            pseq=self.pseq[person],
            ts=dev.local(self.t),
            true_ts=self.t,
            **fields,
        )
        dev.add(r, self.t, self.cfg.eps)
        if kind in AUTHORITY_KINDS:
            self.acts.append(r)
            if kind is not Kind.RULE:
                self.log(f"{person} signs {kind.value}"
                         + (f" -> {r.subject}" if r.subject else "")
                         + f" on {dev.name}")
        elif kind is Kind.DECISION:
            self.decisions.append(r)
        return r

    def _appoint(self) -> None:
        self.sign("C", Kind.GRANT, subject="A")
        pol = self.cfg.policy
        if pol.deputy_timeout is not None:
            self.sign("C", Kind.RULE, subject="B", primary="A", timeout=pol.deputy_timeout,
                      primary_timeout=pol.primary_timeout)

    def believes_holder(self, person: str) -> bool:
        dev = self.devices[PERSON_DEVICE[person]]
        return holder_at(dev.segments(), dev.local(self.t)) == person

    def can_accept(self, person: str) -> tuple[bool, str]:
        """Would ``person``'s own device accept a decision from them now?"""
        cfg, pol = self.cfg, self.cfg.policy
        dev = self.devices[PERSON_DEVICE[person]]
        if holder_at(dev.segments(), dev.local(self.t)) != person:
            return False, "not_holder"
        if pol.lease is not None:
            if cfg.acked:
                silence = dev.acked_silence(self.t, dev.latest_from_device(SERVER))
            else:
                silence = dev.silence_from_device(self.t, SERVER)
            if silence > pol.lease:
                return False, "lease"
        if pol.primary_timeout is not None and not (person == "A" and cfg.a_ignores_timeout):
            for rule in dev.rules():
                if rule.primary != person or rule.primary_timeout is None:
                    continue
                if cfg.acked:
                    beat = dev.latest_from_person(rule.subject or "")
                    silence = dev.acked_silence(self.t, beat)
                else:
                    silence = dev.silence_from_person(self.t, rule.subject or "")
                if silence > rule.primary_timeout:
                    return False, "timeout"
        return True, "ok"

    def _decide(self, person: str) -> None:
        self.at(self.t + self.rng.expovariate(self.cfg.decision_rate), self._decide, person)
        if self.t > self.cfg.t_end - self.cfg.quiesce:
            return
        if not self.able(person) or not self.believes_holder(person):
            return
        ok, why = self.can_accept(person)
        rid = None
        if ok:
            dev = self.devices[PERSON_DEVICE[person]]
            crew = self.rng.choice(CREWS)
            r = self.sign(person, Kind.DECISION, subject=crew,
                          value=f"{crew}:{self.rng.randrange(1000)}",
                          grant_ref=act_at(dev.segments(), dev.local(self.t)))
            rid = r.rid
        self.attempts.append(Attempt(self.t, person, ok, why, rid))

    def _handover(self, frm: str, to: str) -> None:
        # MODEL CHOICE: a handover is gated by the same enforcement as a decision, so a
        # stopped commander cannot hand over either.
        if self.able(frm) and self.can_accept(frm)[0]:
            self.sign(frm, Kind.HANDOVER, subject=to)
        else:
            self.log(f"{frm} cannot hand over to {to}: device refuses")

    # -- network ------------------------------------------------------------------------

    def _heartbeat(self, name: str) -> None:
        self.at(self.t + self.cfg.hb_period, self._heartbeat, name)
        dev = self.devices[name]
        person = next((p for p, d in PERSON_DEVICE.items() if d == name and p not in
                       self.org.at_server), None)
        # MODEL CHOICE: "device" presence is what the document describes (B hears nothing
        # from A's device); "person" presence models a dead-man switch that only beats while
        # the user is fit. Either way the beat carries the user's last sequence number.
        present = not (person is not None and self.cfg.presence == "person"
                       and not self.able(person))
        last = self.pseq[person] if person is not None else 0
        dev.hb[(name, present)] = Heartbeat(dev.local(self.t), self.t, person, last, present,
                                            dev.heard_vector())

    def _sync(self, i: int, src: str) -> None:
        self.at(self.t + self.cfg.sync_period, self._sync, i, src)
        link = self.links[i]
        if not link.up(src, self.t):
            return
        sender = self.devices[src]
        cursor = self._cursor.get((i, src), 0)
        new = sender.log[cursor:]
        self._cursor[(i, src)] = len(sender.log)
        records = [sender.records[rid] for rid in new]
        # Deliveries on one link keep their order (constant latency), which is what makes
        # a heartbeat's last_pseq a valid completeness proof downstream.
        self.at(self.t + link.latency, self._deliver, link.other(src), records,
                dict(sender.hb))

    def _deliver(self, dst: str, records: list[Record],
                 hb: dict[tuple[str, bool], Heartbeat]) -> None:
        dev = self.devices[dst]
        for r in records:
            dev.add(r, self.t, self.cfg.eps)
        dev.merge_heartbeats(hb)

    # -- succession triggers ------------------------------------------------------------

    def _control(self) -> None:
        self.at(self.t + self.cfg.control_period, self._control)
        if self.cfg.effect == "acceptance":
            self._accept_appointments()
        pol = self.cfg.policy
        if pol.deputy_timeout is not None:
            self._maybe_activate()
        if pol.promotion is not None:
            self._maybe_promote()
        if pol.superior_takeover:
            self._maybe_takeover()

    def _accept_appointments(self) -> None:
        # MODEL CHOICE (acceptance effect): the appointee's device accepts as soon as it
        # holds the appointment; a person must be fit to accept.
        for person in DECIDERS:
            if not self.able(person):
                continue
            dev = self.devices[PERSON_DEVICE[person]]
            accepted = {r.accepts for r in dev.authority.values() if r.kind is Kind.ACCEPTANCE}
            for r in list(dev.authority.values()):
                if (r.kind in (Kind.TAKEOVER, Kind.PROMOTION) and r.subject == person
                        and r.rid not in accepted):
                    self.sign(person, Kind.ACCEPTANCE, subject=person, accepts=r.rid)

    def _reported(self) -> bool:
        cfg = self.cfg
        return cfg.a_state == "incapacitated" and self.t >= cfg.t_cut + cfg.report_delay

    def _maybe_activate(self) -> None:
        deputy = "B"
        dev = self.devices[PERSON_DEVICE[deputy]]
        if deputy in self._pending or not self.able(deputy):
            return
        rule = next((r for r in dev.rules() if r.subject == deputy), None)
        if rule is None or rule.timeout is None:
            return
        if holder_at(dev.segments(), dev.local(self.t)) != rule.primary:
            return
        beat = dev.latest_from_person(rule.primary or "")
        if beat is None or dev.local(self.t) - beat.ts < rule.timeout:
            return
        self._pending.add(deputy)
        self.at(self.t + self.cfg.b_react, self._activate, deputy, rule.rid)

    def _activate(self, deputy: str, rule_rid: str) -> None:
        self._pending.discard(deputy)
        dev = self.devices[PERSON_DEVICE[deputy]]
        rule = dev.records[rule_rid]
        if holder_at(dev.segments(), dev.local(self.t)) != rule.primary:
            return
        beat = dev.latest_from_person(rule.primary or "")
        if beat is None or dev.local(self.t) - beat.ts < (rule.timeout or math.inf):
            return
        self.sign(deputy, Kind.ACTIVATION, subject=deputy, rule=rule_rid, last_heard=beat.ts)

    def _maybe_promote(self) -> None:
        cfg, pol = self.cfg, self.cfg.policy
        srv = self.devices[SERVER]
        holder = holder_at(srv.segments(), srv.local(self.t))
        candidate = "B"
        if self._promoted or holder in (None, candidate):
            return
        # MODEL CHOICE: the operator acts on data silence at the core (the prototype's
        # runbook: confirm the command edge is unreachable) or on a voice report that A is
        # unfit; and only while the candidate reaches the core (it must copy the prefix).
        silence = srv.silence_from_person(self.t, holder)
        suspect = (math.isfinite(silence) and silence >= cfg.detect) or self._reported()
        if not suspect or srv.silence_from_person(self.t, candidate) > cfg.reach:
            return
        if pol.promotion == "after_lease":
            silence = srv.silence_from_device(self.t, PERSON_DEVICE[holder])
            lease_over = silence >= (pol.lease or 0.0) + pol.margin
            coordinated = silence <= cfg.reach  # A's device will hear of it at once
            if not (lease_over or coordinated):
                return
        self._promoted = True
        self.sign("OP", Kind.PROMOTION, subject=candidate)

    def _maybe_takeover(self) -> None:
        cfg = self.cfg
        srv = self.devices[SERVER]
        if holder_at(srv.segments(), srv.local(self.t)) != "A":
            return
        if self._c_state == "calling":
            if self.t >= self._c_call_end:
                # MODEL CHOICE: voice reaches A whenever A is fit (the document assumes
                # commanders "lose data but keep voice"); a_answers_voice=False models a
                # commander who is fit but does not answer, as in the storyboard.
                if self.able("A") and cfg.a_answers_voice:
                    self._c_state = "idle"
                    self._c_quiet_until = self.t + cfg.recall
                    self.log("C reaches A by voice; nobody acts")
                else:
                    self._c_state = "done"
                    self.log("C cannot reach A by voice")
                    self.sign("C", Kind.TAKEOVER, subject="B")
            return
        if self._c_state != "idle":
            return
        silence = srv.silence_from_person(self.t, "A")
        quiet = self.t < self._c_quiet_until
        if (math.isfinite(silence) and silence >= cfg.detect and not quiet) or (
            self._reported() and not self._report_handled
        ):
            self._report_handled = self._reported()
            self._c_state = "calling"
            self._c_call_end = self.t + cfg.voice_call
            self.log("C tries to reach A by voice")

    # -- settlement ---------------------------------------------------------------------

    def _horizon(self, srv: Device, person: str) -> float:
        if person in self.org.at_server:
            return srv.local(self.t)
        best = -math.inf
        complete = srv.contiguous.get(person, 0)
        for beat in srv.hb.values():
            if beat.person == person and beat.last_pseq <= complete:
                best = max(best, beat.ts)
        return best

    def _confirm(self) -> None:
        cfg = self.cfg
        self.at(self.t + cfg.confirm_period, self._confirm)
        srv = self.devices[SERVER]
        segs = srv.segments()
        rules = srv.rules()
        named = {r.signer for r in srv.authority.values()}
        named |= {r.subject for r in srv.authority.values() if r.subject is not None}
        named |= {r.primary for r in rules if r.primary is not None}
        horizons: dict[str, float] = {}
        for rid in list(srv.log):
            d = srv.records[rid]
            if d.kind is not Kind.DECISION or rid in self.confirmed:
                continue
            v = classify(d, segs, cfg.eps, held=srv.records, settled=False)
            if v.reason != "unsettled":
                continue
            need = required_signers(d.ts, segs, srv.authority.values(), named, self.org,
                                    cfg.eps, cfg.settlement)
            for p in need:
                if p not in horizons:
                    horizons[p] = self._horizon(srv, p)
            if all(horizons[p] >= d.ts + cfg.eps for p in need):
                covers = frozenset(r.rid for r in srv.authority.values()
                                   if r.ts <= d.ts + cfg.eps)
                conf = Record(rid=f"conf-{rid}", kind=Kind.CONFIRMATION, signer="core",
                              device=SERVER, pseq=0, ts=srv.local(self.t), true_ts=self.t,
                              decision=rid, covers=covers)
                srv.add(conf, self.t, cfg.eps)
                self.confirmed[rid] = self.t

    # -- observation --------------------------------------------------------------------

    def _probe(self) -> None:
        self.at(self.t + self.cfg.probe_period, self._probe)
        capable = frozenset(p for p in DECIDERS if self.able(p) and self.can_accept(p)[0])
        if self.probes and self.probes[-1][1] != capable:
            gained = capable - self.probes[-1][1]
            lost = self.probes[-1][1] - capable
            for p in sorted(gained):
                self.log(f"{p}'s device starts accepting {p}'s decisions")
            for p in sorted(lost):
                why = self.can_accept(p)[1] if self.able(p) else "unfit"
                self.log(f"{p}'s device stops accepting {p}'s decisions ({why})")
        self.probes.append((self.t, capable))


def simulate(cfg: Config) -> Sim:
    return Sim(cfg).run()
