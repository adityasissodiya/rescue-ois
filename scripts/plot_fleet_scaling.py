#!/usr/bin/env python3
"""Plot journal throughput and arrival latency against fleet size.

Reads paper/data/eval_fleet_scaling.anon.jsonl and writes a column-width figure
replacing the former fleet-scaling table. The data is two series over one
ordered independent variable, which is a chart rather than a table: the claim
being made is about the *shape* of the curves -- throughput climbing while
latency stays flat -- and four rows of numbers state that shape without showing
it.

Percentiles are arrival-curve percentiles: the time by which the journal held
that share of the batch. There is no server-side arrival timestamp on
incident.journal (created_at is client-supplied), so arrival is detected by
polling; resolution is one poll interval. This is adequate for comparing fleet
sizes, whose effects are at the hundreds-of-milliseconds scale.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.rcParams["pdf.fonttype"] = 42
matplotlib.rcParams["ps.fonttype"] = 42
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "eval_fleet_scaling.anon.jsonl"
FIG_OUT = ROOT / "figures" / "fig_fleet_scaling.pdf"

C_TPUT = "#5b8db8"
C_P50 = "#4a7c4a"
C_P95 = "#c47b2c"


def load_sizes() -> list[dict]:
    rows = []
    for line in DATA.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        if rec.get("metric_name") == "size_summary":
            rows.append(rec["scenario_params"])
    return sorted(rows, key=lambda r: r["fleet_size"])


def main() -> int:
    sizes = load_sizes()
    if not sizes:
        print("no size_summary records found", file=sys.stderr)
        return 1

    n = [r["fleet_size"] for r in sizes]
    tput = [r["median_journal_throughput_eps"] for r in sizes]
    p50 = [r["median_arrival_p50_ms"] / 1000.0 for r in sizes]
    p95 = [r["median_arrival_p95_ms"] / 1000.0 for r in sizes]
    delivered = min(r["min_delivery_ratio"] for r in sizes)

    plt.rcParams.update({
        "font.size": 8,
        "axes.labelsize": 8,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "legend.fontsize": 7,
    })
    fig, ax = plt.subplots(figsize=(3.5, 2.05))

    ax.plot(n, tput, marker="o", markersize=4, linewidth=1.4, color=C_TPUT,
            label="Journal throughput")
    ax.set_xlabel("Concurrent responder edges")
    ax.set_ylabel("Events/s", color=C_TPUT)
    ax.tick_params(axis="y", labelcolor=C_TPUT)
    ax.set_xticks(n)
    ax.set_ylim(0, max(tput) * 1.18)
    ax.grid(axis="both", linestyle=":", linewidth=0.6, alpha=0.6)
    ax.spines["top"].set_visible(False)

    ax2 = ax.twinx()
    ax2.plot(n, p95, marker="s", markersize=3.5, linewidth=1.2, color=C_P95,
             linestyle="--", label="Arrival p95")
    ax2.plot(n, p50, marker="^", markersize=3.5, linewidth=1.2, color=C_P50,
             linestyle="-.", label="Arrival p50")
    ax2.set_ylabel("Arrival time (s)")
    ax2.set_ylim(0, max(p95) * 1.55)
    ax2.spines["top"].set_visible(False)

    handles = ax.get_lines() + ax2.get_lines()
    ax.legend(handles, [h.get_label() for h in handles],
              loc="upper left", frameon=False, ncol=1)

    fig.savefig(FIG_OUT, bbox_inches="tight")
    plt.close(fig)

    print(f"wrote {FIG_OUT}")
    print(f"  sizes {n}, throughput {tput} ev/s")
    print(f"  p50 {[round(x, 2) for x in p50]} s, p95 {[round(x, 2) for x in p95]} s")
    print(f"  minimum delivery ratio across every run: {delivered}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
