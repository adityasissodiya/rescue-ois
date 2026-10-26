"""The truth oracle and the per-run metrics.

Truth applies the same rule as the devices, but to every record ever signed and with true
timestamps. Metrics compare what the devices did against it. The paper's evaluation
plan (section VI-A) lists the metrics; each key below names the one it measures.
"""

from __future__ import annotations

import math
import statistics
from collections.abc import Iterable

from .model import VALID_LOOKING, Kind, Record, Status, classify, holder_at, timeline
from .network import PERSON_DEVICE, READERS, SERVER
from .sim import Sim


def _pct(values: list[float], q: float) -> float | None:
    if not values:
        return None
    values = sorted(values)
    k = (len(values) - 1) * q
    lo, hi = math.floor(k), math.ceil(k)
    return values[lo] + (values[hi] - values[lo]) * (k - lo)


def _first(probes: Iterable[tuple[float, frozenset[str]]], pred) -> float | None:
    for t, capable in probes:
        if pred(t, capable):
            return t
    return None


def measure(sim: Sim) -> dict:
    cfg, pol = sim.cfg, sim.cfg.policy
    t_cut, t_heal = cfg.t_cut, cfg.t_cut + cfg.outage
    dt = cfg.probe_period
    alive = cfg.a_state == "alive"

    truth_segs = timeline(sim.acts, sim.org, truth=True)
    truth = {d.rid: classify(d, truth_segs, 0.0, settled=True, truth=True)
             for d in sim.decisions}
    srv = sim.devices[SERVER]
    final = {d.rid: srv.verdict(d, cfg.eps) for d in sim.decisions if d.rid in srv.records}
    valid = [d for d in sim.decisions if truth[d.rid].status is Status.AUTHORITATIVE]

    # -- who could record decisions, when (from the probes) ---------------------------
    after = [(t, c) for t, c in sim.probes if t >= t_cut]
    window = [(t, c) for t, c in after if t < t_heal]
    a_stop = _first(window, lambda t, c: "A" not in c) if alive else None
    a_window = (a_stop - t_cut) if a_stop is not None else (cfg.outage if alive else None)
    takeover_t = _first(after, lambda t, c: any(p != "A" for p in c))
    successor = None
    if takeover_t is not None:
        successor = next(p for t, c in after if t == takeover_t for p in sorted(c) if p != "A")
    # Over the whole run: with random flapping, overlaps can happen before t_cut.
    overlap_s = dt * sum(1 for _, c in sim.probes if len(c) >= 2)
    overlap_window_s = dt * sum(1 for _, c in window if len(c) >= 2)
    headless_window_s = dt * sum(1 for _, c in window if not c)
    headless_s = dt * sum(1 for _, c in sim.probes if not c)
    a_frac = (sum(1 for _, c in window if "A" in c) / len(window)) if window else 0.0

    # -- the trade-off of section II-C, over the outage ---------------------------------
    prop_a = alive and a_frac >= 0.999
    prop_b = any(p != "A" for _, c in window for p in c)
    prop_c = overlap_window_s == 0

    # -- decisions ----------------------------------------------------------------------
    by_status = {s: 0 for s in Status}
    reasons: dict[str, int] = {}
    for v in final.values():
        by_status[v.status] += 1
        if v.status is Status.RESIDUAL:
            reasons[v.reason] = reasons.get(v.reason, 0) + 1
    misclassified = sum(
        1 for rid, v in final.items()
        if v.status is not Status.IN_DOUBT
        and (v.status in VALID_LOOKING) != (truth[rid].status in VALID_LOOKING)
    )

    refused_legit = refused_prevented = 0
    for a in sim.attempts:
        if a.accepted:
            continue
        if holder_at(truth_segs, a.t) == a.person:
            refused_legit += 1
        else:
            refused_prevented += 1

    # -- completeness: valid decisions the core, or the successor, did not hold ----------
    core_delay = [srv.arrival[d.rid] - d.true_ts for d in valid if d.rid in srv.arrival]
    missing_at_heal = sum(1 for d in valid if d.true_ts < t_heal
                          and srv.arrival.get(d.rid, math.inf) > t_heal)
    successor_blind = None
    if takeover_t is not None and successor is not None:
        sdev = sim.devices[PERSON_DEVICE[successor]]
        successor_blind = sum(
            1 for d in valid
            if d.signer != successor and d.true_ts < takeover_t
            and sdev.arrival.get(d.rid, math.inf) > takeover_t
        )

    # -- settlement ---------------------------------------------------------------------
    settle = [sim.confirmed[d.rid] - d.true_ts for d in valid if d.rid in sim.confirmed]
    never_settled = sum(1 for d in valid if d.rid not in sim.confirmed
                        and final.get(d.rid) is not None
                        and final[d.rid].status is not Status.IN_DOUBT)

    # -- what readers saw ---------------------------------------------------------------
    flips_to_residual = flips_to_valid = 0
    for name in READERS:
        dev = sim.devices[name]
        for rid, first in dev.first_seen.items():
            now = dev.verdict(dev.records[rid], cfg.eps)
            if first.status in VALID_LOOKING and now.status is Status.RESIDUAL:
                flips_to_residual += 1
            elif first.status is Status.RESIDUAL and now.status in VALID_LOOKING:
                flips_to_valid += 1

    # Two people's orders to the same crew within the window, one of them residual: the
    # crew holds contradictory orders. (Orders from successive legitimate commanders are
    # normal and not counted.)
    conflicting = 0
    ds = sorted(sim.decisions, key=lambda d: d.true_ts)
    for i, d1 in enumerate(ds):
        for d2 in ds[i + 1:]:
            if d2.true_ts - d1.true_ts > cfg.contradiction_window:
                break
            if (d1.signer != d2.signer and d1.subject == d2.subject
                    and Status.RESIDUAL in (truth[d1.rid].status, truth[d2.rid].status)):
                conflicting += 1

    # -- invariants ---------------------------------------------------------------------
    auth_regressions = 0
    for dev in sim.devices.values():
        for rid in dev.auth_seen:
            if dev.verdict(dev.records[rid], cfg.eps).status is not Status.AUTHORITATIVE:
                auth_regressions += 1
    lost_devices = {PERSON_DEVICE["A"]} if cfg.a_device_lost else set()
    record_sets = {frozenset(dev.records) for name, dev in sim.devices.items()
                   if name not in lost_devices}
    converged = len(record_sets) == 1
    lost = sum(1 for d in sim.decisions if d.rid not in srv.records
               and d.device not in lost_devices)
    stranded = sum(1 for d in sim.decisions if d.rid not in srv.records
                   and d.device in lost_devices)
    successions = [s for s in truth_segs if s.start >= t_cut and s.prev != s.holder]
    needless = alive and any(s.kind is not Kind.HANDOVER for s in successions)
    used_core = any(r.kind is Kind.PROMOTION for r in sim.acts) or any(
        r.kind is Kind.TAKEOVER for r in sim.acts)

    return {
        "policy": pol.name,
        "policy_label": pol.label(),
        "case": ("flaps" if cfg.flaps is not None
                 else "relay" if cfg.relay_fault else cfg.case),
        "a_state": cfg.a_state,
        "a_device_lost": cfg.a_device_lost,
        "seed": cfg.seed,
        "outage_s": cfg.outage,
        "lease_s": pol.lease,
        "T_s": pol.deputy_timeout,
        "Tprime_s": pol.primary_timeout,
        "eps_s": cfg.eps,
        "settlement": cfg.settlement,
        "presence": cfg.presence,
        "acked": cfg.acked,
        "effect": cfg.effect,
        # (a) how long A can keep recording
        "a_window_s": a_window,
        "a_capable_frac": round(a_frac, 4),
        # (b) takeover delay, and by whom
        "takeover_delay_s": None if takeover_t is None else round(takeover_t - t_cut, 3),
        "successor": successor,
        "takeover_in_outage": takeover_t is not None and takeover_t < t_heal,
        "needless_takeover": needless,
        "used_core": used_core,
        # (c) overlap, and its opposite: nobody can record
        "overlap_s": overlap_s,
        "overlap_outage_s": overlap_window_s,
        "headless_outage_s": headless_window_s,
        "headless_s": headless_s,
        "prop_a": prop_a,
        "prop_b": prop_b,
        "prop_c": prop_c,
        # decisions
        "decisions": len(sim.decisions),
        "residual": by_status[Status.RESIDUAL],
        "residual_superseded": reasons.get("superseded", 0),
        "residual_no_valid_grant": reasons.get("no_valid_grant", 0),
        "in_doubt": by_status[Status.IN_DOUBT],
        "authoritative_end": by_status[Status.AUTHORITATIVE],
        "provisional_end": by_status[Status.PROVISIONAL],
        "truth_residual": sum(1 for v in truth.values() if v.status is Status.RESIDUAL),
        "misclassified": misclassified,
        "refused_legit": refused_legit,
        "refused_prevented": refused_prevented,
        "manual_review": by_status[Status.RESIDUAL] + by_status[Status.IN_DOUBT],
        # completeness (legitimate decisions not yet where they are needed)
        "core_delay_max_s": round(max(core_delay), 3) if core_delay else None,
        "missing_at_heal": missing_at_heal,
        "successor_blind": successor_blind,
        # settlement
        "settle_median_s": _round(_pct(settle, 0.5)),
        "settle_p95_s": _round(_pct(settle, 0.95)),
        "never_settled": never_settled,
        # readers
        "reader_flips_to_residual": flips_to_residual,
        "reader_flips_to_valid": flips_to_valid,
        "conflicting_orders": conflicting,
        # invariants
        "auth_regressions": auth_regressions,
        "converged": converged,
        "lost": lost,
        "stranded_on_lost_device": stranded,
        "tradeoff_violated": prop_a and prop_b and prop_c,
    }


def _round(x: float | None) -> float | None:
    return None if x is None else round(x, 3)


def median(values: list[float | None]) -> float | None:
    xs = [v for v in values if v is not None]
    return statistics.median(xs) if xs else None


def decision_table(sim: Sim) -> list[dict]:
    """Every decision with its truth and final verdict, for traces and tests."""
    truth_segs = timeline(sim.acts, sim.org, truth=True)
    srv = sim.devices[SERVER]
    rows = []
    for d in sim.decisions:
        t = classify(d, truth_segs, 0.0, settled=True, truth=True)
        f = srv.verdict(d, sim.cfg.eps)
        rows.append({
            "rid": d.rid, "signer": d.signer, "true_ts": round(d.true_ts, 3),
            "crew": d.subject, "truth": t.status.value, "truth_reason": t.reason,
            "final": f.status.value, "final_reason": f.reason,
        })
    return rows


def acts_table(sim: Sim) -> list[Record]:
    return [r for r in sim.acts if r.kind is not Kind.RULE]
