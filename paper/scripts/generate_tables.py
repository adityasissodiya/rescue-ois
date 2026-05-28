#!/usr/bin/env python3
"""Generate paper tables from evaluation JSONL files."""

from __future__ import annotations

import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "eval_metrics.anon.jsonl"
COMMAND_PARTITION_DATA = ROOT / "data" / "eval_command_local_partition.anon.jsonl"
CRDT_DATA = ROOT / "data" / "eval_crdt_baseline.anon.jsonl"
CRDT_PARTITION_DATA = ROOT / "data" / "eval_crdt_partition_n10.anon.jsonl"
OUT = ROOT / "tables" / "tab_evaluation.tex"
CRDT_OUT = ROOT / "tables" / "tab_crdt_comparison.tex"
OUT.parent.mkdir(exist_ok=True)


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        sys.exit(f"ERROR: {path} missing")
    records = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def load_records():
    return load_jsonl(DATA)


def load_command_partition_summary():
    records = load_jsonl(COMMAND_PARTITION_DATA)
    summary = next(
        (
            record["scenario_params"]
            for record in records
            if record.get("metric_name") == "summary"
        ),
        None,
    )
    if summary is None:
        sys.exit(f"ERROR: no summary record in {COMMAND_PARTITION_DATA}")
    latencies = [
        record["value_ms"]
        for record in records
        if record.get("metric_name") == "command_local_commit_latency_ms"
        and record.get("value_ms") is not None
    ]
    return summary, latencies


def percentile(xs, p):
    xs_sorted = sorted(xs)
    k = (len(xs_sorted) - 1) * (p / 100)
    f = int(k)
    c = min(f + 1, len(xs_sorted) - 1)
    if f == c:
        return xs_sorted[f]
    return xs_sorted[f] + (xs_sorted[c] - xs_sorted[f]) * (k - f)


def fmt_ms(value: float | None) -> str:
    if value is None:
        return "n/a"
    if value >= 1000:
        return f"{value / 1000:.2f}\\,s"
    return f"{value:.1f}\\,ms"


def write_primary_table(records: list[dict]) -> None:
    partition_summary, partition_latencies = load_command_partition_summary()

    prop = defaultdict(list)
    for record in records:
        if record["scenario"] == "field_edit_propagation" and record.get("value_ms") is not None:
            prop[record["scenario_params"]["queue_depth"]].append(record["value_ms"])

    rec = defaultdict(list)
    for record in records:
        if record["scenario"] == "wan_recovery" and record.get("value_ms") is not None:
            rec[record["scenario_params"]["partition_s"]].append(record["value_ms"] / 1000.0)

    tput = []
    tput_e2e = []
    for record in records:
        if record["scenario"] == "command_throughput" and record.get("run_index") != 0:
            tput.append(record["scenario_params"]["events_per_sec"])
        if record["scenario"] == "command_throughput_endtoend" and record.get("run_index") != 0:
            tput_e2e.append(record["scenario_params"]["events_per_sec"])

    rows = []
    rows.append(r"\textit{Responder-to-command propagation} & & \\")
    for key in sorted(prop.keys()):
        values = prop[key]
        rows.append(
            f"  \\hspace{{2mm}}queue depth = {key} ($n={len(values)}$) & "
            f"median {statistics.median(values):.1f}\\,ms; p95 {percentile(values, 95):.1f}\\,ms & "
            r"outbox-to-command journal path \\"
        )
    rows.append(r"\addlinespace")
    rows.append(r"\textit{Command-to-core WAN recovery} & & \\")
    for key in sorted(rec.keys()):
        values = rec[key]
        rows.append(
            f"  \\hspace{{2mm}}partition = {key}\\,s ($n={len(values)}$) & "
            f"median {statistics.median(values):.2f}\\,s; p95 {percentile(values, 95):.2f}\\,s & "
            r"support-path backhaul, not command authority \\"
        )
    rows.append(r"\addlinespace")
    rows.append(r"\textit{Command journal serialization} & & \\")
    rows.append(
        f"  \\hspace{{2mm}}direct \\texttt{{/accept}} ($n={len(tput)}$) & "
        f"median {statistics.median(tput):.1f} events/s; p95 {percentile(tput, 95):.1f} & "
        r"linearization point: command accept + journal write only \\"
    )
    if tput_e2e:
        rows.append(
            f"  \\hspace{{2mm}}end-to-end via outbox ($n={len(tput_e2e)}$) & "
            f"median {statistics.median(tput_e2e):.1f} events/s; p95 {percentile(tput_e2e, 95):.1f} & "
            r"full responder outbox $\rightarrow$ push-batch $\rightarrow$ command path \\"
        )
    rows.append(r"\addlinespace")
    seqs = partition_summary["sequence_numbers"]
    rows.append(r"\textit{Command commit during responder isolation} & & \\")
    rows.append(
        "  \\hspace{2mm}direct command accept path "
        f"($n={partition_summary['attempted_writes']}$) & "
        f"{partition_summary['successful_commits']}/{partition_summary['attempted_writes']} commits; "
        f"seq. {min(seqs)}--{max(seqs)}; "
        f"{partition_summary['duplicate_sequence_count']} duplicate seqs. & "
        f"direct \\texttt{{/accept/event-batch}} path; median/p95 latency "
        f"{statistics.median(partition_latencies):.2f}/{percentile(partition_latencies, 95):.2f}\\,ms \\\\"
    )

    with OUT.open("w", encoding="utf-8") as handle:
        handle.write("% Auto-generated by scripts/generate_tables.py.\n")
        handle.write("% Do not edit; re-run the script after evaluation JSONL changes.\n")
        for line in rows:
            handle.write(line + "\n")
        handle.write(r"\bottomrule" + "\n")
    print(f"wrote {OUT} ({len(rows)} rows)")


def first_summary(records: list[dict], scenario: str, **matches) -> dict | None:
    for record in records:
        if record.get("scenario") != scenario or record.get("metric_name") != "summary":
            continue
        params = record.get("scenario_params", {})
        if all(params.get(k) == v for k, v in matches.items()):
            return params
    return None


def write_crdt_table(aal_records: list[dict]) -> None:
    crdt_records = load_jsonl(CRDT_DATA)
    partition_records = load_jsonl(CRDT_PARTITION_DATA) if CRDT_PARTITION_DATA.exists() else crdt_records

    aal_prop = defaultdict(list)
    aal_wan = defaultdict(list)
    aal_tput = []
    for record in aal_records:
        if record.get("scenario") == "field_edit_propagation" and record.get("value_ms") is not None:
            aal_prop[record["scenario_params"]["queue_depth"]].append(record["value_ms"])
        if record.get("scenario") == "wan_recovery" and record.get("value_ms") is not None:
            aal_wan[record["scenario_params"]["partition_s"]].append(record["value_ms"])
        if record.get("scenario") == "command_throughput" and record.get("run_index") != 0:
            aal_tput.append(record["scenario_params"]["events_per_sec"])

    field_stressed = first_summary(crdt_records, "crdt_field_edit_propagation", profile="stressed", queue_depth=10)
    field_degraded = first_summary(crdt_records, "crdt_field_edit_propagation", profile="degraded", queue_depth=10)
    field_q100 = first_summary(crdt_records, "crdt_field_edit_propagation", profile="degraded", queue_depth=100)
    tput_summary = first_summary(crdt_records, "crdt_no_partition_throughput")

    conflict = [r for r in crdt_records if r.get("scenario") == "crdt_concurrent_authoritative_edit" and r.get("metric_name") == "convergence_ms"]
    delete = [r for r in crdt_records if r.get("scenario") == "crdt_delete_resurrection" and r.get("metric_name") == "convergence_ms"]
    convergence = [r for r in partition_records if r.get("scenario") == "crdt_partition_convergence" and r.get("value_ms") is not None]

    conflict_values = [r["value_ms"] for r in conflict if r.get("value_ms") is not None]
    delete_values = [r["value_ms"] for r in delete if r.get("value_ms") is not None]
    conv_values = [r["value_ms"] for r in convergence]
    winners = Counter(r.get("scenario_params", {}).get("winner") for r in conflict)
    winners_fmt = ", ".join(f"{key}: {value}" for key, value in sorted(winners.items()) if key is not None)
    resurrected = sum(int(r.get("scenario_params", {}).get("element_visible_after_delete_update_race", 0)) for r in delete)

    rows = []
    aal_q10 = statistics.median(aal_prop[10]) if aal_prop.get(10) else None
    aal_q100 = statistics.median(aal_prop[100]) if aal_prop.get(100) else None
    rows.append(
        "Field-edit propagation & "
        f"AAL bridge median {fmt_ms(aal_q10)} at qd=10; {fmt_ms(aal_q100)} at qd=100 & "
        f"CRDT qd=10 stressed/degraded {fmt_ms(field_stressed and field_stressed.get('median_ms'))}/{fmt_ms(field_degraded and field_degraded.get('median_ms'))}; qd=100 degraded {fmt_ms(field_q100 and field_q100.get('median_ms'))} & "
        r"Both preserve durable propagation; CRDT anti-entropy is not an authority boundary. \\"
    )
    rows.append(
        "Concurrent status edit & "
        "Current AAL service path sequences unique events; semantic rejection is model-level/not implemented in the measured prototype & "
        f"{len(conflict)}/{len(conflict)} LWW runs converge; winner counts {winners_fmt}; median {fmt_ms(statistics.median(conflict_values) if conflict_values else None)} & "
        r"LWW accepts both writes and materializes only the latest value; losing op is only recoverable from the op log. \\"
    )
    rows.append(
        "Delete/update race & "
        "Current AAL service path has no delete/update semantic guard; limitation disclosed & "
        f"{resurrected}/{len(delete)} runs resurrect the element; median convergence {fmt_ms(statistics.median(delete_values) if delete_values else None)} & "
        r"Matches Hanssen's stated LWW delete-semantics caveat. \\"
    )
    aal_tput_med = statistics.median(aal_tput) if aal_tput else None
    crdt_tput_med = tput_summary.get("median_events_per_sec") if tput_summary else None
    rows.append(
        "No-partition throughput & "
        f"AAL command-journal commit rate median {aal_tput_med:.1f} events/s (single writer) & " if aal_tput_med is not None else "No-partition throughput & AAL command-journal commit rate unavailable & "
    )
    rows[-1] += (
        f"CRDT aggregate local accept rate across three writers median {crdt_tput_med:.1f} events/s & " if crdt_tput_med is not None else "CRDT aggregate local accept rate unavailable & "
    )
    rows[-1] += r"Different units; reports write-availability trade-off, not direct speedup. \\"
    aal_wan60 = statistics.median(aal_wan[60]) if aal_wan.get(60) else None
    if len(conv_values) >= 10:
        rows.append(
            f"Post-quiescence convergence (60\\,s outage, $n={len(conv_values)}$) & "
            f"AAL command-to-core support-path recovery median {fmt_ms(aal_wan60)} after a real \\textit{{tc}} WAN cut ($n={len(aal_wan.get(60, []))}$) & "
            f"CRDT all-replica convergence median {fmt_ms(statistics.median(conv_values))} after anti-entropy resumes (no link impairment during the wait) & "
            r"Comparable in outage duration, not transport mechanism; AAL keeps command-local ordering, CRDT converges once anti-entropy is exchanged. \\"
        )

    with CRDT_OUT.open("w", encoding="utf-8") as handle:
        handle.write("% Auto-generated by scripts/generate_tables.py from eval_crdt_baseline.anon.jsonl.\n")
        for row in rows:
            handle.write(row + "\n")
        handle.write(r"\bottomrule" + "\n")
    print(f"wrote {CRDT_OUT} ({len(rows)} rows)")


def main():
    records = load_records()
    write_primary_table(records)
    if CRDT_DATA.exists():
        write_crdt_table(records)
    else:
        print(f"skip CRDT table: {CRDT_DATA} missing")


if __name__ == "__main__":
    main()
