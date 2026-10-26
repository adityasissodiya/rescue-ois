"""The experiments, each a list of labelled configurations, and a parallel runner.

Each experiment answers one open question of the paper; ``QUESTIONS`` states which. Rows
are written to ``<out>/<experiment>.csv``, one per run.
"""

from __future__ import annotations

import csv
import multiprocessing as mp
import random
from collections.abc import Callable, Iterable
from dataclasses import replace
from pathlib import Path

from .metrics import measure
from .policies import POLICIES, make_policy
from .sim import Config, simulate

Spec = tuple[dict, Config]

QUESTIONS = {
    "matrix": "Table II: what does each policy give up, per partition case, with A cut off "
    "or incapacitated? (paper section VI-A, planned)",
    "timeout": "S4: what should T be? Needless takeovers against time without command, as a "
    "function of outage length (model document, question 3 to the rescue service)",
    "lease": "S1, S2, S3L: what does the lease length L cost when only the backhaul is lost?",
    "detect": "S1 against S2: does immediate promotion overlap at all once operator "
    "reaction time is accounted for?",
    "margin": "S4: how large must T - T' be for one edge at a time, given heartbeat period, "
    "multi-hop delay and clock error?",
    "clock": "When do the in-doubt status and clock error matter for the verdicts?",
    "faults": "Where each policy fails (model document, section 'Where each policy fails')",
    "settlement": "Does every valid decision eventually settle? The document's rule read "
    "literally against our refinement",
    "search": "Randomized link flapping: do the invariants hold for every policy?",
}


def _cfg(policy: str, seed: int, **kw) -> Config:
    pol_kw = {k: kw.pop(k) for k in ("lease", "timeout", "primary_timeout", "margin")
              if k in kw}
    return Config(policy=make_policy(policy, **pol_kw), seed=seed, **kw)


# The commander's state at the cut: fit and answering voice, fit but unreachable by voice
# too (the storyboard's S3 case), or incapacitated.
A_STATES = {
    "alive": {"a_state": "alive"},
    "alive, no voice": {"a_state": "alive", "a_answers_voice": False},
    "incapacitated": {"a_state": "incapacitated"},
}


def matrix(seeds: int) -> list[Spec]:
    return [
        ({"policy": p, "case": c, "a_state": a}, _cfg(p, s, case=c, **A_STATES[a]))
        for p in POLICIES
        for c in ("none", "P-A", "P-B", "P-C")
        for a in A_STATES
        for s in range(seeds)
    ]


def timeout(seeds: int) -> list[Spec]:
    specs = []
    for t in (60, 120, 300, 600, 900, 1200):
        t_prime = t - min(60, t / 2)
        for outage in (120, 300, 600, 1200, 2400):
            for a in ("alive", "incapacitated"):
                for s in range(seeds):
                    specs.append((
                        {"policy": "S4", "T": t, "outage": outage, "a_state": a},
                        _cfg("S4", s, case="P-A", a_state=a, outage=outage, timeout=t,
                             primary_timeout=t_prime),
                    ))
    return specs


def lease(seeds: int) -> list[Spec]:
    return [
        ({"policy": p, "L": L, "case": c, "a_state": a},
         _cfg(p, s, case=c, lease=L, **A_STATES[a]))
        for p in ("S1", "S2", "S3L")
        for L in (15, 30, 60, 90, 180, 300, 600)
        for c in ("P-A", "P-B")
        for a in A_STATES
        for s in range(seeds)
    ]


def detect(seeds: int) -> list[Spec]:
    return [
        ({"policy": p, "detect": d, "a_state": a},
         _cfg(p, s, case="P-A", a_state=a, detect=d))
        for p in ("S1", "S2")
        for d in (15, 30, 60, 90, 120, 300)
        for a in ("alive", "incapacitated")
        for s in range(seeds)
    ]


def margin(seeds: int) -> list[Spec]:
    specs = []
    for acked in (False, True):
        for m in (0, 1, 2, 4, 8, 16, 32):
            for period in (1.0, 2.0, 5.0):
                for eps in (0.001, 0.2, 2.0):
                    for s in range(seeds):
                        specs.append((
                            {"policy": "S4", "acked": acked, "margin": m, "period": period,
                             "eps": eps},
                            _cfg("S4", s, case="P-A", timeout=300, primary_timeout=300 - m,
                                 sync_period=period, hb_period=period, eps=eps,
                                 clock="adversarial", outage=600, tail=600, acked=acked),
                        ))
    return specs


def clock(seeds: int) -> list[Spec]:
    # S3 with a commander who does not answer: a takeover lands while A keeps deciding,
    # so decisions fall close to a change of command.
    base = {"case": "P-A", "a_answers_voice": False, "decision_rate": 1 / 20}
    specs = []
    for eps in (0.001, 0.2, 2.0, 10.0, 60.0):
        for s in range(seeds):
            specs.append(({"policy": "S3", "eps": eps, "a_clock_error": 0.0,
                           "variant": "bounded"}, _cfg("S3", s, eps=eps, **base)))
    for err in (1.0, 5.0, 30.0, -30.0):
        for s in range(seeds):
            specs.append(({"policy": "S3", "eps": 0.2, "a_clock_error": err,
                           "variant": "A beyond bound"},
                          _cfg("S3", s, eps=0.2, a_clock_error=err, **base)))
    return specs


FAULTS: dict[str, dict] = {
    "S4: A's device ignores T'": {"policy": "S4", "case": "P-A", "a_ignores_timeout": True},
    "S4: A mute (receives, cannot send)": {"policy": "S4", "case": "P-A", "oneway": "mute"},
    "S4: A deaf (sends, cannot receive)": {"policy": "S4", "case": "P-A", "oneway": "deaf"},
    "S4: P-C, A hands over to S inside the partition": {
        "policy": "S4", "case": "P-C", "handover_to_s_after": 120},
    "S4: stale heartbeat via relay": {"policy": "S4", "relay_fault": True},
    "S4: stale heartbeat via relay, acknowledged T'": {
        "policy": "S4", "relay_fault": True, "acked": True},
    "S4: A unfit, device connected (device presence)": {
        "policy": "S4", "case": "none", "a_state": "incapacitated"},
    "S4: A unfit, device connected (person presence)": {
        "policy": "S4", "case": "none", "a_state": "incapacitated", "presence": "person"},
    "S2: A unfit, device connected": {"policy": "S2", "case": "none",
                                      "a_state": "incapacitated"},
    "S3: A fit but does not answer voice": {"policy": "S3", "case": "P-A",
                                            "a_answers_voice": False},
    "S3L: A fit, answers voice, lease expires": {"policy": "S3L", "case": "P-A"},
    "S3: P-B, A fit, no voice; takeover effective when signed": {
        "policy": "S3", "case": "P-B", "a_answers_voice": False},
    "S3: P-B, A fit, no voice; takeover effective when accepted": {
        "policy": "S3", "case": "P-B", "a_answers_voice": False, "effect": "acceptance"},
    "S1: P-B, backhaul lost, mesh up": {"policy": "S1", "case": "P-B"},
    "S5: P-C, both record": {"policy": "S5", "case": "P-C"},
}


def faults(seeds: int) -> list[Spec]:
    specs = []
    for name, kw in FAULTS.items():
        kw = dict(kw)
        p = kw.pop("policy")
        for s in range(seeds):
            specs.append(({"fault": name, "policy": p}, _cfg(p, s, **kw)))
    return specs


def settlement(seeds: int) -> list[Spec]:
    return [
        ({"policy": p, "settlement": mode, "a_device_lost": lost},
         _cfg(p, s, case="P-A", a_state="incapacitated", a_device_lost=lost,
              settlement=mode))
        for p in ("S1", "S3", "S4")
        for mode in ("strict", "closing")
        for lost in (False, True)
        for s in range(seeds)
    ]


def search_config(policy: str, seed: int, settlement_mode: str) -> tuple[dict, Config]:
    """A random incident: every link flaps, and policy parameters, clock bound, presence
    and faults are drawn too. Deterministic in ``seed``, so a violation is reproducible.
    Clocks stay within the bound, so misclassification is an invariant here."""
    rng = random.Random(seed)
    T = rng.choice((60.0, 120.0, 300.0))
    kw = {
        "lease": rng.choice((15.0, 60.0, 90.0, 300.0)),
        "timeout": T,
        "primary_timeout": T - rng.choice((0.0, 5.0, 30.0)),
        "a_state": rng.choice(("alive", "alive", "incapacitated")),
        "a_device_lost": rng.random() < 0.15,
        "presence": rng.choice(("device", "person")),
        "a_answers_voice": rng.random() < 0.5,
        "detect": rng.choice((30.0, 120.0)),
        "eps": rng.choice((0.01, 0.5, 5.0)),
        "decision_rate": rng.choice((1 / 60, 1 / 15)),
        "handover_to_s_after": rng.choice((None, None, 60.0, 400.0)),
        "flaps": (rng.choice((60.0, 300.0)), rng.choice((60.0, 300.0, 900.0))),
        "settlement": settlement_mode,
        "clock": "uniform",
    }
    labels = {"policy": policy} | {k: v for k, v in kw.items() if k != "clock"}
    return labels, _cfg(policy, seed, **kw)


def search(seeds: int) -> list[Spec]:
    specs = []
    for p in POLICIES:
        for mode in ("strict", "closing"):
            for s in range(seeds):
                labels, cfg = search_config(p, 10_000 + s, mode)
                specs.append((labels | {"acked": False, "effect": "signature"}, cfg))
                if mode != "closing":
                    continue
                if cfg.policy.lease or cfg.policy.primary_timeout:
                    specs.append((labels | {"acked": True, "effect": "signature"},
                                  replace(cfg, acked=True)))
                if cfg.policy.promotion or cfg.policy.superior_takeover:
                    specs.append((labels | {"acked": False, "effect": "acceptance"},
                                  replace(cfg, effect="acceptance")))
    return specs


EXPERIMENTS: dict[str, Callable[[int], list[Spec]]] = {
    "matrix": matrix,
    "timeout": timeout,
    "lease": lease,
    "detect": detect,
    "margin": margin,
    "clock": clock,
    "faults": faults,
    "settlement": settlement,
    "search": search,
}

# Seeds per cell for a full run; --quick divides these.
DEFAULT_SEEDS = {
    "matrix": 20, "timeout": 10, "lease": 10, "detect": 10, "margin": 20, "clock": 20,
    "faults": 10, "settlement": 10, "search": 100,
}


def _run(spec: Spec) -> dict:
    labels, cfg = spec
    row = measure(simulate(cfg))
    return labels | {k: v for k, v in row.items() if k not in labels}


def run_specs(specs: Iterable[Spec], jobs: int = 0) -> list[dict]:
    specs = list(specs)
    if jobs == 1:
        return [_run(s) for s in specs]
    with mp.get_context("fork").Pool(jobs or None) as pool:
        return pool.map(_run, specs, chunksize=4)


def write_csv(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    keys: list[str] = []
    for row in rows:
        keys += [k for k in row if k not in keys]
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def run_experiment(name: str, out: Path, seeds: int | None = None, jobs: int = 0,
                   quick: bool = False) -> list[dict]:
    n = seeds if seeds is not None else DEFAULT_SEEDS[name]
    if quick and seeds is None:
        n = max(2, n // 5)
    rows = run_specs(EXPERIMENTS[name](n), jobs)
    write_csv(rows, out / f"{name}.csv")
    return rows
