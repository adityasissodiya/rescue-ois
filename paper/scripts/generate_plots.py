#!/usr/bin/env python3
"""Generate paper figures from paper/data/eval_metrics.jsonl.

Per ADR-0006, this script is the single transformation from measurements
to figures. It does not embed default values; if the data file is missing
or empty, it exits non-zero.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.rcParams["pdf.fonttype"] = 42
matplotlib.rcParams["ps.fonttype"] = 42
matplotlib.use("Agg")
import matplotlib.pyplot as plt

DATA = Path("paper/data/eval_metrics.jsonl")
OUT = Path("paper/figures")
OUT.mkdir(exist_ok=True)


def load_records():
    if not DATA.exists() or DATA.stat().st_size == 0:
        sys.exit(f"ERROR: {DATA} missing or empty. Run scripts/evaluate-pilot.py first.")
    with DATA.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def fig_recovery(records):
    by_dur = defaultdict(list)
    for record in records:
        if record.get("scenario") != "wan_recovery":
            continue
        if record.get("value_ms") is None:
            continue
        dur = record["scenario_params"].get("partition_s")
        by_dur[dur].append(record["value_ms"])
    if not by_dur:
        sys.exit("ERROR: no wan_recovery records with non-null value_ms")

    durations = sorted(by_dur.keys())
    data = [by_dur[duration] for duration in durations]
    n_per = [len(duration_data) for duration_data in data]

    fig, ax = plt.subplots(figsize=(3.4, 2.4))
    ax.boxplot(
        data,
        labels=[f"{duration}s" for duration in durations],
        widths=0.5,
        medianprops={"color": "black", "linewidth": 1.2},
        boxprops={"linewidth": 0.8},
        whiskerprops={"linewidth": 0.8},
        capprops={"linewidth": 0.8},
        flierprops={"marker": "+", "markersize": 4, "markeredgecolor": "black"},
    )
    ax.set_xlabel("Partition duration")
    ax.set_ylabel("Recovery time (ms, log scale)")
    ax.set_yscale("log")
    ax.grid(axis="y", linestyle=":", linewidth=0.5, alpha=0.6)
    ax.set_axisbelow(True)
    for i, n in enumerate(n_per):
        ax.text(i + 1, ax.get_ylim()[0] * 1.5, f"n={n}", ha="center", fontsize=7)

    fig.tight_layout(pad=0.3)
    fig.savefig(OUT / "fig_recovery.pdf", bbox_inches="tight")
    plt.close(fig)


def main():
    records = load_records()
    fig_recovery(records)
    print(f"figures written to {OUT}/")


if __name__ == "__main__":
    main()
