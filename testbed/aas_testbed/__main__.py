"""Command line: ``python -m aas_testbed <command>``.

  run          one incident, with its trace and every decision's verdict
  <experiment> one experiment (see ``list``), written to <out>/<experiment>.csv
  all          every experiment, then the report
  report       results/REPORT.md from the CSVs already in <out>
  latex        LaTeX macros and table rows for the paper, from results/
  list         the experiments and the question each answers
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from .experiments import DEFAULT_SEEDS, EXPERIMENTS, QUESTIONS, run_experiment
from .latex import write_latex
from .metrics import decision_table, measure
from .network import CASES
from .policies import POLICIES, make_policy
from .report import write_report
from .sim import Config, simulate


def _run_one(args: argparse.Namespace) -> None:
    pol = make_policy(args.policy, lease=args.lease, timeout=args.timeout,
                      primary_timeout=args.primary_timeout)
    cfg = Config(
        policy=pol, case=args.case, a_state=args.a_state, outage=args.outage,
        seed=args.seed, eps=args.eps, settlement=args.settlement, presence=args.presence,
        a_answers_voice=not args.no_voice, a_ignores_timeout=args.a_ignores_timeout,
        oneway=args.oneway, handover_to_s_after=args.handover_to_s_after,
        a_device_lost=args.a_device_lost, a_clock_error=args.a_clock_error,
        acked=args.acked, effect=args.effect, relay_fault=args.relay_fault,
    )
    sim = simulate(cfg)
    case = "relay fault" if cfg.relay_fault else f"case {cfg.case}"
    extras = [x for x, on in (("acknowledged leases", cfg.acked),
                              ("appointments effective on acceptance",
                               cfg.effect == "acceptance")) if on]
    print(f"# {pol.label()} | {case} | A {cfg.a_state} | seed {cfg.seed}"
          + "".join(f" | {x}" for x in extras))
    print(f"# {pol.description}\n")
    for t, msg in sim.trace:
        print(f"{t:9.1f}  {msg}")
    if args.decisions:
        print("\n# decisions: truth vs final verdict at the core")
        for row in decision_table(sim):
            print(json.dumps(row))
    print("\n# metrics")
    for k, v in measure(sim).items():
        print(f"{k:28} {v}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="aas_testbed", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="one incident, with its trace")
    r.add_argument("--policy", choices=POLICIES, default="S4")
    r.add_argument("--case", choices=CASES, default="P-A")
    r.add_argument("--a-state", choices=("alive", "incapacitated"), default="alive")
    r.add_argument("--outage", type=float, default=1200.0)
    r.add_argument("--lease", type=float, default=90.0, help="L, s")
    r.add_argument("--timeout", type=float, default=300.0, help="T, s")
    r.add_argument("--primary-timeout", type=float, default=None, help="T', s (T - 60)")
    r.add_argument("--eps", type=float, default=0.2)
    r.add_argument("--settlement", choices=("strict", "closing"), default="closing")
    r.add_argument("--presence", choices=("device", "person"), default="device")
    r.add_argument("--no-voice", action="store_true", help="A does not answer C's call")
    r.add_argument("--a-ignores-timeout", action="store_true")
    r.add_argument("--oneway", choices=("mute", "deaf"), default=None)
    r.add_argument("--handover-to-s-after", type=float, default=None)
    r.add_argument("--a-device-lost", action="store_true")
    r.add_argument("--a-clock-error", type=float, default=0.0)
    r.add_argument("--relay-fault", action="store_true",
                   help="V1 relays a stale heartbeat of B's to A (overrides --case)")
    r.add_argument("--acked", action="store_true",
                   help="proposed fix: leases and T' run from acknowledged heartbeats")
    r.add_argument("--effect", choices=("signature", "acceptance"), default="signature",
                   help="when a takeover or promotion takes effect")
    r.add_argument("--seed", type=int, default=0)
    r.add_argument("--decisions", action="store_true", help="print every decision")

    for name in EXPERIMENTS:
        e = sub.add_parser(name, help=QUESTIONS[name])
        e.add_argument("--seeds", type=int, default=None,
                       help=f"seeds per cell (default {DEFAULT_SEEDS[name]})")
        e.add_argument("--out", type=Path, default=Path("results"))
        e.add_argument("--jobs", type=int, default=0, help="processes (default: all cores)")
        e.add_argument("--quick", action="store_true", help="a fifth of the seeds")

    a = sub.add_parser("all", help="every experiment, then the report")
    a.add_argument("--out", type=Path, default=Path("results"))
    a.add_argument("--jobs", type=int, default=0)
    a.add_argument("--quick", action="store_true")

    rep = sub.add_parser("report", help="write <out>/REPORT.md from the CSVs")
    rep.add_argument("--out", type=Path, default=Path("results"))

    lx = sub.add_parser("latex", help="LaTeX macros and table rows for the paper")
    lx.add_argument("--results", type=Path, default=Path("results"))
    lx.add_argument("--out", type=Path, required=True)

    sub.add_parser("list", help="the experiments and their questions")

    args = ap.parse_args(argv)
    if args.cmd == "run":
        _run_one(args)
    elif args.cmd == "list":
        for name, q in QUESTIONS.items():
            print(f"{name:11} {q}")
    elif args.cmd == "report":
        print(write_report(args.out))
    elif args.cmd == "latex":
        for path in write_latex(args.results, args.out):
            print(f"wrote {path}")
    elif args.cmd == "all":
        for name in EXPERIMENTS:
            t0 = time.time()
            rows = run_experiment(name, args.out, jobs=args.jobs, quick=args.quick)
            print(f"{name:11} {len(rows):5} runs  {time.time() - t0:6.1f} s", flush=True)
        print(write_report(args.out))
    else:
        t0 = time.time()
        rows = run_experiment(args.cmd, args.out, args.seeds, args.jobs, args.quick)
        print(f"{args.cmd}: {len(rows)} runs in {time.time() - t0:.1f} s -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
