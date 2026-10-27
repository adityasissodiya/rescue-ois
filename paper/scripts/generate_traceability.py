#!/usr/bin/env python3
"""T-20: build the claim -> scenario -> data -> script -> table traceability map.

WONS_2027_ACTION_PLAN.md section 8.4 requires every numerical claim in the paper
to be traceable to (1) a named scenario, (2) a specific JSONL file and
scenario/metric_name value, (3) the script invocation that produced it, and
(4) the table or figure it lands in. This emits that map as TRACEABILITY.md.

It is a generator, not a hand-written document, for the same reason the tables
are: a hand-typed traceability table rots silently, and a rotted one is worse
than none because it looks like evidence. Every row here is **verified against
the data** at generation time -- the file must exist, the scenario/metric_name
filter must match, and the record count must be what the row claims. A row that
cannot be resolved is reported as FAIL and the script exits non-zero.

Usage:
    python scripts/generate_traceability.py        # writes TRACEABILITY.md
    python scripts/generate_traceability.py --check # verify only, write nothing
"""
from __future__ import annotations

import argparse
import json
import statistics as st
import sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = ROOT / "TRACEABILITY.md"

# Canonical invocations. These match README.md in the rescue-ois artifact repo;
# paths there are repo-relative, and the resulting JSONL is copied into this
# paper tree's data/ directory (raw), then scrubbed to *.anon.jsonl, which is
# what every generator actually reads.
INVOKE = {
    "pilot": "python3 scripts/evaluate-pilot.py",
    "cmdpart": "python3 scripts/evaluate-command-local-partition.py",
    "fenced": "python3 scripts/evaluate-fenced-promotion.py --n 5 --writes-per-phase 20",
    "outbox": "python3 scripts/evaluate-outbox-crash-restart.py",
    "netemprop": "python3 scripts/evaluate-netem-propagation.py",
    "schedule": "python3 scripts/evaluate-netem-schedule.py --runs 10",
    "fleet": ("python3 scripts/evaluate-fleet-scaling.py --sizes 1,3,5,10 "
              "--runs 5 --events-per-responder 20"),
    "raftauth": "python3 scripts/evaluate-raft-authority.py --runs 12 --writes-per-run 5",
    "raftold": "python3 scripts/evaluate-raft-baseline.py",
    "crdt": ("python3 baseline/scripts/evaluate-crdt-baseline.py --runs 30 "
             "--throughput-events 300 --partition-s 60 --partition-runs 1 "
             "--output data/eval_crdt_baseline.jsonl"),
    "crdtn10": ("python3 baseline/scripts/evaluate-crdt-baseline.py --runs 1 "
                "--throughput-events 30 --partition-s 60 --partition-runs 10 "
                "--output data/eval_crdt_partition_n10.jsonl"),
}

# (paper location, claim, plan scenario, data file, scenario, metric_name,
#  expected record count or None, invocation key, generator, destination)
ROWS = [
    # ---- Table III: primary service-path numbers -------------------------
    ("IV-C", "Responder-to-command propagation, qd 1/10/100: medians 710.1/639.4/931.5 ms",
     "NET-01 steady-state propagation", "eval_metrics.anon.jsonl",
     "field_edit_propagation", "end_to_end_propagation_ms", 90, "pilot",
     "generate_tables.py", "Table III"),
    ("IV-E3", "Command-to-core WAN recovery, 1/10/60 s outages: medians 0.75/0.91/0.23 s",
     "WAN backhaul recovery", "eval_metrics.anon.jsonl",
     "wan_recovery", "recovery_to_core_ms", 90, "pilot",
     "generate_tables.py", "Table III"),
    ("IV-B", "Saturation throughput at the sequencer: 356.3 events/s median",
     "Command journal serialization", "eval_metrics.anon.jsonl",
     "command_throughput", "events_per_sec", 30, "pilot",
     "generate_tables.py + plot_promotion_cdf.py macros", "Table III, TputDirectMedian"),
    ("IV-B", "End-to-end via outbox: 159.4 events/s median",
     "Command journal serialization (end to end)", "eval_metrics.anon.jsonl",
     "command_throughput_endtoend", "events_per_sec", 30, "pilot",
     "generate_tables.py", "Table III, TputEndToEndMedian"),
    ("IV-C", "Duplicate replay: 50 unique client_event_id x5 leaves exactly 50 rows, n=30",
     "M3 idempotency", "eval_metrics.anon.jsonl",
     "duplicate_replay", "stored_events", 30, "pilot",
     "prose only (not tabulated)", "IV-C prose"),
    ("IV-B", "Command commits during responder isolation: 20/20, seq 1--20, 0 duplicates",
     "M1--M2 responder-isolation independence", "eval_command_local_partition.anon.jsonl",
     "command_accept_path_during_responder_syncd_isolation",
     "command_local_commit_latency_ms", 20, "cmdpart",
     "generate_tables.py", "Table III"),
    ("IV-C", "Outbox survives a responder-Postgres power cycle; journal consistent ~2.6 s after recovery",
     "R2 durability across restart", "eval_outbox_crash_restart.anon.jsonl",
     "outbox_durability_across_vehicle_restart", "post_restart_outbox_survived", 1,
     "outbox", "prose only (not tabulated)", "IV-C prose"),

    # ---- Figure 4 + promotion macros -------------------------------------
    ("IV-D", ("Fenced-promotion protocol cost by phase; n=300, 100 per phase; "
              "medians A 6.3 ms / B 2.5 ms / C 5.7 ms"),
     "M4 fenced promotion, phases A/B/C", "eval_fenced_promotion.anon.jsonl",
     "fenced_promotion_stale_rejection", "attempt", 300, "fenced",
     "plot_promotion_cdf.py", "IV-D prose, promotionMedian* macros"),

    # ---- Table IV: Raft ---------------------------------------------------
    ("IV-E1", "Leader-minority partition: 12/12 elect L1 != L0; new-leader median 3.08 s, p95 4.43 s",
     "scenario_leader_isolation (plan 7.2 Option A)", "eval_raft_baseline.anon.jsonl",
     "raft_leader_minority_partition", "run", 12, "raftauth",
     "generate_raft_table.py (orphan; tab_raft_comparison.tex is not \\input)",
     "IV-E1 prose"),
    ("IV-E1", "Raft FSM assigns event_seq and enforces client_event_id idempotency",
     "Raft sanity check", "eval_raft_baseline.anon.jsonl",
     "raft_sanity_event_seq_dedup", "sanity_check", 1, "raftauth",
     "generate_raft_table.py (orphan; tab_raft_comparison.tex is not \\input)",
     "IV-E1 prose"),

    # ---- Table V: CRDT ----------------------------------------------------
    ("IV-E2", "Concurrent status edit: 30/30 LWW runs converge, median 12.8 ms",
     "CRDT semantic falsification", "eval_crdt_baseline.anon.jsonl",
     "crdt_concurrent_authoritative_edit", "convergence_ms", 30, "crdt",
     "generate_tables.py", "Table IV"),
    ("IV-E2", "Delete/update race: 30/30 runs resurrect the element, median 12.7 ms",
     "CRDT delete-resurrection", "eval_crdt_baseline.anon.jsonl",
     "crdt_delete_resurrection", "convergence_ms", 30, "crdt",
     "generate_tables.py", "Table IV"),
    ("IV-E2", "CRDT impaired field-edit propagation: 814.1 ms / 2.54 s / 3.97 s",
     "CRDT propagation under netem", "eval_crdt_baseline.anon.jsonl",
     "crdt_field_edit_propagation", "anti_entropy_propagation_ms", 180, "crdt",
     "generate_tables.py", "Table IV"),
    ("IV-E2", "CRDT aggregate local accept rate: median 349.2 events/s",
     "CRDT no-partition throughput", "eval_crdt_baseline.anon.jsonl",
     "crdt_no_partition_throughput", "events_per_sec", 30, "crdt",
     "generate_tables.py", "Table IV"),
    ("IV-E2", "Post-quiescence convergence after a 60 s outage: median 45.4 ms, n=10",
     "CRDT partition convergence", "eval_crdt_partition_n10.anon.jsonl",
     "crdt_partition_convergence", "time_to_all_replicas_consistent_ms", 10, "crdtn10",
     "generate_tables.py", "Table IV"),

    # ---- Table VI: regime schedule ---------------------------------------
    ("IV-C", "Delivery within phase vs eventually per regime; isolated row 0.00 / 1.00",
     "NET-02 time-varying connectivity", "eval_netem_schedule.anon.jsonl",
     "netem_schedule", "summary", 10, "schedule",
     "generate_network_tables.py (orphan; tab_netem_schedule.tex is not \\input)",
     "IV-C prose, Fig. 5"),
    ("IV-C", "540/540 events journaled; outbox backlog peaks at 13; recovery sub-second",
     "NET-02 time-varying connectivity", "eval_netem_schedule.anon.jsonl",
     "netem_schedule", "outbox_backlog", 1300, "schedule",
     "generate_network_tables.py (orphan; tab_netem_schedule.tex is not \\input)",
     "IV-C prose, Fig. 5"),

    # ---- Table VII: fleet size -------------------------------------------
    ("IV-B", "Fleet sizes 1/3/5/10; throughput 19.5 -> 182.5 events/s; delivery 1.00 at every size",
     "NET-03 fleet-size sweep", "eval_fleet_scaling.anon.jsonl",
     "fleet_scaling", "size_summary", 4, "fleet",
     "plot_fleet_scaling.py", "Fig. 4"),
    ("IV-B", "1900/1900 events across the sweep (20 runs)",
     "NET-03 fleet-size sweep", "eval_fleet_scaling.anon.jsonl",
     "fleet_scaling", "run", 20, "fleet",
     "plot_fleet_scaling.py", "Fig. 4, IV-B prose"),

    # ---- Orphaned but regenerable ----------------------------------------
    ("(removed)", ("Steady-state netem propagation -- Table V in the NCA submission, "
                   "REMOVED from this paper (plan 0.4 item 3, defect 5)"),
     "NET-01 static profiles", "eval_netem_propagation.anon.jsonl",
     "netem_propagation", "end_to_end_propagation_ms", 80, "netemprop",
     "generate_tables.py (orphan branch)", "none -- tables/tab_netem.tex is not \\input"),
    ("(unused)", ("Original three-scenario Raft baseline: propagation, follower "
                  "catch-up, quorum loss. Superseded for the paper by "
                  "evaluate-raft-authority.py, which isolates the *leader* -- the "
                  "scenario none of these three covers"),
     "Raft propagation / catch-up / quorum loss", "eval_metrics_raft.anon.jsonl",
     "baseline_raft_propagation", "end_to_end_propagation_ms", 90, "raftold",
     "generate_baseline_table.py (orphan; writes tab_baseline.tex)",
     "none -- tab_baseline.tex is not \\input"),
]

# Numbers in the paper that do NOT come from a JSONL, recorded so the map is
# complete rather than merely convenient.
NON_JSONL = [
    ("IV-D", "Strict variant: all six safety invariants over 38.56 M distinct states in 13.0 min",
     "TLA+ strict model check", "rescue-ois formal/tla/RUNS.md + formal/tla/runs/",
     "java -jar tla2tools.jar -config RescueOIS_strict.cfg RescueOIS.tla", "IV-D prose"),
    ("IV-D", ("Weak variants refuted: SingleAuthority 185 states (0.85 s), "
              "EpochAuthorityCoupling 144 (0.77 s), NoForkedJournal 1.0 k (0.83 s)"),
     "TLA+ weak-variant refutation", "rescue-ois formal/tla/RUNS.md + weak_counterexample.md",
     "java -jar tla2tools.jar -config RescueOIS_weak*.cfg RescueOIS.tla", "IV-D prose"),
    ("IV-D1, V-B", "Two-edge single authority has a runtime witness",
     "T-10 two-edge integration test", "rescue-ois edge/syncd/tests/",
     ("RESCUE_OIS_INTEGRATION_TESTS=1 pytest edge/syncd/tests/"
      "test_partition_and_boundary_visibility.py"
      "::test_no_two_command_writers_for_same_incident_epoch"),
     "IV-D1 prose, Fig. 3"),
]


# ---------------------------------------------------------------------------
# Spot-checks (T-20 definition of done: "manual spot-check 5 random paper
# numbers"). Each recomputes a published value straight from the data,
# independently of the generator that produced the table, and compares it with
# the typeset figure. Built in rather than done once by hand, so it re-verifies
# on every run instead of rotting.
# ---------------------------------------------------------------------------
def _median(xs):
    return st.median(xs)


def spot_checks(load_cached) -> list[tuple[str, str, str, bool]]:
    out = []

    def add(label, got, want, unit=""):
        ok = abs(got - want) <= 0.01 * max(1.0, abs(want))
        out.append((label, f"{got}{unit}", f"{want}{unit}", ok))

    m = load_cached("eval_metrics.anon.jsonl")
    v = [x["value_ms"] for x in m
         if x.get("scenario") == "field_edit_propagation"
         and x.get("scenario_params", {}).get("queue_depth") == 10
         and x.get("value_ms") is not None]
    add("Table III: responder propagation, qd=10, median", round(_median(v), 1), 639.4, " ms")

    r = load_cached("eval_raft_baseline.anon.jsonl")
    t = [x["scenario_params"]["time_to_new_leader_ms"] for x in r
         if x.get("scenario") == "raft_leader_minority_partition"
         and x.get("metric_name") == "run"
         and x.get("scenario_params", {}).get("time_to_new_leader_ms") is not None]
    add("IV-E1 prose: new-leader election, median", round(_median(t) / 1000, 2), 3.08, " s")

    c = load_cached("eval_crdt_baseline.anon.jsonl")
    cv = [x["value_ms"] for x in c
          if x.get("scenario") == "crdt_concurrent_authoritative_edit"
          and x.get("metric_name") == "convergence_ms" and x.get("value_ms") is not None]
    add("Table IV: concurrent status edit, median convergence", round(_median(cv), 1), 12.8, " ms")

    sch = [x["scenario_params"] for x in load_cached("eval_netem_schedule.anon.jsonl")
           if x.get("metric_name") == "summary"]
    within = [ph["delivered_within_phase_ratio"] for run in sch
              for ph in run["per_phase"] if ph["regime"] == "isolated"]
    iso = [run["per_regime"]["isolated"] for run in sch]
    add("IV-C prose: isolated regime, delivered within phase",
        round(st.mean(within), 2), 0.00)
    add("IV-C prose: isolated regime, delivered eventually",
        round(st.mean([d["reached_journal"] / d["submitted"] for d in iso]), 2), 1.00)
    add("IV-C prose: events journaled",
        sum(run["reached_journal_total"] for run in sch), 540)
    add("IV-C prose: peak outbox backlog",
        max(run["peak_unforwarded"] for run in sch), 13)

    fl = load_cached("eval_fleet_scaling.anon.jsonl")
    sizes = [x["scenario_params"] for x in fl if x.get("metric_name") == "size_summary"]
    ten = next(p for p in sizes if p["fleet_size"] == 10)
    add("Fig. 4: N=10 journal throughput",
        round(ten["median_journal_throughput_eps"], 1), 182.5, " ev/s")
    runs = [x["scenario_params"] for x in fl if x.get("metric_name") == "run"]
    add("IV-B prose: events journaled across the sweep",
        sum(x["journaled"] for x in runs), 1900)
    add("IV-B prose: events offered across the sweep",
        sum(x["expected_events"] for x in runs), 1900)
    return out


def load(path: Path) -> list[dict]:
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(json.loads(line))
    return out


def provenance(records: list[dict]) -> tuple[str, str]:
    """(git_commit, tree state) from the file's environment record."""
    for r in records:
        env = r.get("environment")
        if isinstance(env, dict) and env.get("git_commit"):
            commit = str(env["git_commit"])[:12]
            dirty = env.get("git_tree_dirty")
            if dirty is True:
                return commit, "dirty"
            if dirty is False:
                return commit, "clean"
            return commit, "unrecorded"
    return "MISSING", "MISSING"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="verify only; write nothing")
    args = ap.parse_args()

    cache: dict[str, list[dict]] = {}
    failures: list[str] = []
    rows_out = []

    for (loc, claim, scen, fname, scenario, metric, expect, inv, gen, dest) in ROWS:
        path = DATA / fname
        if not path.exists():
            failures.append(f"{loc}: {fname} does not exist")
            continue
        if fname not in cache:
            cache[fname] = load(path)
        recs = cache[fname]
        n = sum(1 for r in recs
                if r.get("scenario") == scenario and r.get("metric_name") == metric)
        if n == 0:
            failures.append(
                f"{loc}: no record in {fname} with scenario={scenario} metric_name={metric}")
            status = "FAIL"
        elif expect is not None and n != expect:
            failures.append(
                f"{loc}: {fname} scenario={scenario} metric_name={metric} "
                f"has {n} records, row claims {expect}")
            status = f"COUNT {n}!={expect}"
        else:
            status = f"OK ({n})"
        commit, tree = provenance(recs)
        rows_out.append((loc, claim, scen, fname, scenario, metric, status,
                         INVOKE[inv], gen, dest, commit, tree))

    # Provenance summary per file.
    prov = {}
    for fname in sorted({r[3] for r in rows_out}):
        if fname in cache:
            prov[fname] = provenance(cache[fname])

    lines = []
    A = lines.append
    A("# Traceability map (T-20)")
    A("")
    A("**Generated by `scripts/generate_traceability.py` -- do not edit by hand.**")
    A(f"Regenerated {datetime.now(UTC).date().isoformat()}. "
      "Re-run after any evaluation JSONL changes.")
    A("")
    A("Discharges WONS_2027_ACTION_PLAN.md section 8.4: every numerical claim in the "
      "paper traces to a named scenario, a specific data file and "
      "`scenario`/`metric_name` value, the script invocation that produced it, and the "
      "table or figure it lands in. This closes **Gate 3**.")
    A("")
    A("Every row is verified against the data when this file is generated. The `Verified` "
      "column is the live record count; the generator exits non-zero if any row fails to "
      "resolve, so a stale map fails loudly instead of quietly looking like evidence.")
    A("")
    A("Script paths are relative to the `rescue-ois/` artifact repository. Each harness "
      "writes `artifacts/data/<name>.jsonl`; that file is copied into this tree's `data/` "
      "and scrubbed to `<name>.anon.jsonl`, which is what the generators read.")
    A("")

    A("## Claim to evidence")
    A("")
    A("| Paper | Claim | Scenario | Data file | `scenario` / `metric_name` | Verified | "
      "Invocation | Generator | Lands in |")
    A("|---|---|---|---|---|---|---|---|---|")
    for (loc, claim, scen, fname, scenario, metric, status, inv, gen, dest, _c, _t) in rows_out:
        A(f"| {loc} | {claim} | {scen} | `{fname}` | `{scenario}` / `{metric}` | "
          f"{status} | `{inv}` | `{gen}` | {dest} |")
    A("")

    A("## Numbers that do not come from a JSONL")
    A("")
    A("| Paper | Claim | Scenario | Source | Invocation | Lands in |")
    A("|---|---|---|---|---|---|")
    for (loc, claim, scen, src, inv, dest) in NON_JSONL:
        A(f"| {loc} | {claim} | {scen} | `{src}` | `{inv}` | {dest} |")
    A("")

    A("## Dataset provenance")
    A("")
    A("`git_commit` is the artifact-repo HEAD at run time. `Tree` says whether the "
      "working tree matched that commit: a **dirty** tree means the hash does not "
      "describe the code that ran. Datasets predating the `git_tree_dirty` field show "
      "`unrecorded`; see plan section 0.49 item 4.")
    A("")
    A("| Data file | `git_commit` | Tree |")
    A("|---|---|---|")
    for fname, (commit, tree) in prov.items():
        mark = "**MISSING**" if commit == "MISSING" else f"`{commit}`"
        A(f"| `{fname}` | {mark} | {tree} |")
    A("")

    gaps = [f for f, (c, _) in prov.items() if c == "MISSING"]
    if gaps:
        A("### Provenance gap")
        A("")
        A("These datasets carry **no `environment` record at all**, so they cannot be "
          "tied to any commit:")
        A("")
        for f in gaps:
            A(f"- `{f}`")
        A("")
        A("This is not fixable retroactively -- the runs are historical and the "
          "information was never captured. It is recorded here rather than left implicit, "
          "because `eval_metrics.anon.jsonl` is the source for most of Table III. "
          "Re-running `evaluate-pilot.py` on the current tree would produce a dataset "
          "with provenance; whether that is worth the re-measurement is a judgement call, "
          "and until it is made this is the honest statement of what is known.")
        A("")

    # Completeness: a traceability map is only trustworthy if it accounts for
    # every dataset, including the ones that feed nothing.
    on_disk = {p.name for p in DATA.glob("*.anon.jsonl")}
    referenced = {r[3] for r in rows_out}
    unreferenced = sorted(on_disk - referenced)
    A("## Datasets that feed nothing in the paper")
    A("")
    if unreferenced:
        A("Present in `data/` but not the source of any published number. Listed so "
          "this map is exhaustive rather than merely convenient:")
        A("")
        for f in unreferenced:
            A(f"- `{f}`")
    else:
        A("None: every `data/*.anon.jsonl` is the source of at least one row above.")
    A("")

    def load_cached(name):
        if name not in cache:
            cache[name] = load(DATA / name)
        return cache[name]

    checks = spot_checks(load_cached)
    A("## Spot-checks")
    A("")
    A("T-20's definition of done asks for a manual spot-check of five published "
      "numbers. These recompute the value straight from the data, independently of "
      "the generator that produced the table, and run every time this file is "
      "regenerated.")
    A("")
    A("| Published value | Recomputed | In the paper | |")
    A("|---|---|---|---|")
    for label, got, want, ok in checks:
        A(f"| {label} | {got} | {want} | {'OK' if ok else '**MISMATCH**'} |")
    A("")
    bad = [c for c in checks if not c[3]]
    if bad:
        for label, got, want, _ in bad:
            failures.append(f"spot-check mismatch: {label}: recomputed {got}, paper says {want}")
    else:
        A(f"All {len(checks)} reproduce.")
        A("")

    if failures:
        A("## FAILURES")
        A("")
        for f in failures:
            A(f"- {f}")
        A("")

    text = "\n".join(lines) + "\n"

    if not args.check:
        OUT.write_text(text, encoding="utf-8", newline="\n")
        print(f"wrote {OUT} ({len(rows_out)} traced rows, "
              f"{len(NON_JSONL)} non-JSONL, {len(prov)} datasets)")

    for f in failures:
        print(f"FAIL: {f}", file=sys.stderr)
    if failures:
        print(f"\n{len(failures)} row(s) could not be verified.", file=sys.stderr)
        return 1
    print(f"all {len(rows_out)} rows verified against the data; {len(checks)} spot-checks reproduce")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
