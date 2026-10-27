#!/usr/bin/env python3
"""Plot outbox backlog against time across the connectivity-regime schedule.

Reads paper/data/eval_netem_schedule.anon.jsonl and writes a column-width
figure. The claim of NET-02 is about a *shape over time* -- backlog pinned at
zero while the path is degraded but connected, rising monotonically while
isolated, collapsing within a poll cycle of restore -- and three paragraphs of
per-phase delivery ratios state that shape without showing it. The regime bands
carry the independent variable, so the figure also replaces the schedule table.

Runs poll at their own offsets, so each run is resampled onto a common grid
with previous-value (step) interpolation before the median and min-max envelope
are taken: backlog is a step function of time, not a continuous signal, and
linear interpolation would invent intermediate depths.
"""

from __future__ import annotations

import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.rcParams["pdf.fonttype"] = 42
matplotlib.rcParams["ps.fonttype"] = 42
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "eval_netem_schedule.anon.jsonl"
FIG_OUT = ROOT / "figures" / "fig_netem_schedule.pdf"
TEX_OUT = ROOT / "data" / "schedule_summary.tex"

C_BACKLOG = "#5b8db8"
C_RESTORE = "#c47b2c"

# Shorter than the prose names so the labels clear the 7 pt print floor inside
# a 30 s band; the caption carries the full regime names.
REGIME_LABEL = {
    "clear": "Clear",
    "mesh_stressed": "Stressed",
    "mesh_degraded": "Degraded",
    "isolated": "Isolated",
}
# Monotone in severity, so the bands are ordered without relying on hue.
REGIME_SHADE = {
    "clear": 0.00,
    "mesh_stressed": 0.07,
    "mesh_degraded": 0.13,
    "isolated": 0.22,
}

GRID_STEP_S = 0.5


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        sys.exit(f"ERROR: {path} missing")
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def step_resample(samples: list[tuple[float, int]], grid: list[float]) -> list[int]:
    """Previous-value interpolation of a step function onto `grid`."""
    out: list[int] = []
    idx = 0
    current = samples[0][1]
    for t in grid:
        while idx < len(samples) and samples[idx][0] <= t:
            current = samples[idx][1]
            idx += 1
        out.append(current)
    return out


def main() -> int:
    records = load_jsonl(DATA)

    summaries = [r["scenario_params"] for r in records if r.get("metric_name") == "summary"]
    if not summaries:
        sys.exit("ERROR: no netem_schedule summary records")
    schedule = summaries[0]["schedule"]

    by_run: dict[str, list[tuple[float, int]]] = defaultdict(list)
    for rec in records:
        if rec.get("metric_name") != "outbox_backlog":
            continue
        params = rec["scenario_params"]
        by_run[rec["run_id"]].append((params["t_offset_s"], params["unforwarded"]))
    if not by_run:
        sys.exit("ERROR: no outbox_backlog records")

    total_s = sum(phase["duration_s"] for phase in schedule)
    n_grid = int(total_s / GRID_STEP_S) + 1
    grid = [i * GRID_STEP_S for i in range(n_grid)]

    series = []
    for samples in by_run.values():
        samples.sort()
        series.append(step_resample(samples, grid))

    median = [statistics.median(col) for col in zip(*series)]
    lo = [min(col) for col in zip(*series)]
    hi = [max(col) for col in zip(*series)]

    drains = [s["drain_time_s"] for s in summaries if s.get("drain_time_s") is not None]
    peak = max(s["peak_unforwarded"] for s in summaries)
    submitted = sum(s["submitted_total"] for s in summaries)
    journaled = sum(s["reached_journal_total"] for s in summaries)

    # Restore instant: start of the phase that follows the isolated phase.
    restore_t = 0.0
    for phase in schedule:
        restore_t += phase["duration_s"]
        if phase["regime"] == "isolated":
            break

    plt.rcParams.update({
        "font.size": 8,
        "axes.labelsize": 8,
        "xtick.labelsize": 8,
        "ytick.labelsize": 8,
        "legend.fontsize": 7,
    })
    # Authored at the IEEEtran column width (252 pt) and included at
    # width=lumnwidth, so the figure renders at scale 1.0 and the 7 pt
    # annotations stay at 7 pt on the printed page.
    fig, ax = plt.subplots(figsize=(3.5, 1.88))

    # Regime bands: the independent variable, drawn behind the data. Labels
    # alternate between two rows because a 45 s band is narrower than the word
    # that names it at the 7 pt print floor.
    start = 0.0
    for ordinal, phase in enumerate(schedule):
        end = start + phase["duration_s"]
        shade = REGIME_SHADE[phase["regime"]]
        if shade:
            ax.axvspan(start, end, color="black", alpha=shade, linewidth=0, zorder=0)
        ax.annotate(
            REGIME_LABEL[phase["regime"]],
            xy=((start + end) / 2, 1.0), xycoords=("data", "axes fraction"),
            xytext=(0, 10 if ordinal % 2 == 0 else 2), textcoords="offset points",
            ha="center", va="bottom", fontsize=7,
        )
        start = end

    # No legend: two marks only, and the caption names both. A legend here
    # would cost a lookup and collide with the peak callout.
    ax.fill_between(grid, lo, hi, color=C_BACKLOG, alpha=0.22, linewidth=0,
                    zorder=2)
    ax.plot(grid, median, color=C_BACKLOG, linewidth=1.4, zorder=3)

    ax.axvline(restore_t, color=C_RESTORE, linewidth=1.1, linestyle="--", zorder=4)
    # Both callouts sit in empty plot area: the peak label left of the rising
    # edge, the restore label right of it where the backlog has already drained.
    ax.annotate(
        f"peak {peak}",
        xy=(restore_t - 2, peak), xytext=(restore_t - 34, peak * 1.26),
        fontsize=7, ha="right", va="center",
        arrowprops=dict(arrowstyle="-", linewidth=0.6, color="black",
                        shrinkA=1, shrinkB=1),
    )
    ax.annotate(
        "link restored",
        xy=(restore_t + 1, peak * 0.60), xytext=(restore_t + 12, peak * 0.60),
        fontsize=7, ha="left", va="center", color=C_RESTORE,
        arrowprops=dict(arrowstyle="->", linewidth=0.7, color=C_RESTORE,
                        shrinkA=1, shrinkB=0),
    )

    ax.set_xlabel("Time through schedule (s)")
    ax.set_ylabel("Unforwarded outbox events")
    ax.set_xlim(0, total_s)
    ax.set_ylim(0, peak * 1.52)
    ax.set_xticks([0, 60, 120, 180, 240])
    ax.grid(axis="y", linestyle=":", linewidth=0.6, alpha=0.6, zorder=1)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    fig.savefig(FIG_OUT, bbox_inches="tight")
    plt.close(fig)

    with TEX_OUT.open("w", encoding="utf-8") as handle:
        handle.write("% Auto-generated by scripts/plot_netem_schedule.py.\n")
        handle.write("% Do not edit; re-run the script after evaluation JSONL changes.\n")
        handle.write(f"\\newcommand{{\\scheduleRuns}}{{{len(summaries)}}}\n")
        handle.write(f"\\newcommand{{\\scheduleEvents}}{{{submitted}}}\n")
        handle.write(f"\\newcommand{{\\schedulePeakBacklog}}{{{peak}}}\n")
        handle.write(
            f"\\newcommand{{\\scheduleDrainMedian}}{{{statistics.median(drains):.2f}\\,s}}\n"
        )
        handle.write(f"\\newcommand{{\\scheduleDrainMax}}{{{max(drains):.2f}\\,s}}\n")

    print(f"wrote {FIG_OUT}")
    print(f"  {len(by_run)} runs, {journaled}/{submitted} events journaled")
    print(f"  peak backlog {peak}, restore at t={restore_t:.0f}s")
    print(f"  drain median {statistics.median(drains):.2f}s, max {max(drains):.2f}s")
    print(f"wrote {TEX_OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
