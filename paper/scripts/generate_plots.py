#!/usr/bin/env python3
"""Generate paper figures from data/eval_metrics.anon.jsonl.

Per ADR-0006, this script is the single transformation from measurements
to figures. It does not embed default values; if the data file is missing
or empty, it exits non-zero.
"""

from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.rcParams["pdf.fonttype"] = 42
matplotlib.rcParams["ps.fonttype"] = 42
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "eval_metrics.anon.jsonl"
OUT = ROOT / "figures"
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
        by_dur[dur].append(record["value_ms"] / 1000.0)
    if not by_dur:
        sys.exit("ERROR: no wan_recovery records with non-null value_ms")

    durations = sorted(by_dur.keys())
    data = [by_dur[duration] for duration in durations]

    plt.rcParams.update({
        "font.size": 8,
        "axes.labelsize": 8,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
    })
    fig, ax = plt.subplots(figsize=(3.45, 2.65))
    x_positions = [1.0 + 1.8 * i for i in range(len(durations))]

    for x_pos, values in zip(x_positions, data):
        sorted_values = sorted(values)
        count = len(sorted_values)
        offsets = [0.0] if count == 1 else [(-0.52 + 1.04 * j / (count - 1)) for j in range(count)]
        ax.scatter(
            [x_pos + offset for offset in offsets],
            sorted_values,
            s=18,
            facecolor="#5b8db8",
            edgecolor="black",
            linewidth=0.25,
            alpha=0.85,
            zorder=3,
        )
    ax.set_xlabel("WAN partition duration")
    ax.set_ylabel("Recovery time (s)")
    ax.set_xticks(x_positions)
    ax.set_xticklabels([f"{duration} s" for duration in durations])
    ax.set_xlim(x_positions[0] - 0.75, x_positions[-1] + 0.75)
    upper_tick = max(1, math.ceil(max(max(values) for values in data) * 1.1))
    ax.set_ylim(0, upper_tick)
    ax.set_yticks(range(0, upper_tick + 1))
    ax.grid(axis="y", linestyle=":", linewidth=0.6, alpha=0.7)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    fig.tight_layout(pad=0.5)
    fig.savefig(OUT / "fig_recovery.pdf", bbox_inches="tight")
    plt.close(fig)


def main():
    records = load_records()
    fig_recovery(records)
    print(f"figures written to {OUT}/")


if __name__ == "__main__":
    main()
