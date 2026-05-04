#!/usr/bin/env python3
from __future__ import annotations

import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path


ERROR_NO_VALID = (
    "No valid measurements in eval_metrics.jsonl. "
    "Run scripts/evaluate-pilot.py first."
)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def load_records(metrics_path: Path) -> list[dict]:
    if not metrics_path.exists():
        print(ERROR_NO_VALID, file=sys.stderr)
        raise SystemExit(1)

    records: list[dict] = []
    with metrics_path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                records.append(json.loads(stripped))
            except json.JSONDecodeError as exc:
                print(
                    f"Invalid JSON in {metrics_path} at line {line_number}: {exc}",
                    file=sys.stderr,
                )
                raise SystemExit(1) from exc

    if not records:
        print(ERROR_NO_VALID, file=sys.stderr)
        raise SystemExit(1)
    return records


def valid_measurements(records: list[dict]) -> list[dict]:
    valid = []
    for record in records:
        value = record.get("value_ms")
        if isinstance(value, int | float):
            valid.append(record)
    if not valid:
        print(ERROR_NO_VALID, file=sys.stderr)
        raise SystemExit(1)
    return valid


def generate_plots() -> None:
    root = repo_root()
    metrics_path = root / "eval_metrics.jsonl"
    records = load_records(metrics_path)
    valid = valid_measurements(records)

    if len(valid) < 3:
        print(
            "Fewer than three valid measurements in eval_metrics.jsonl; "
            "not writing paper/figures/fig_evaluation.pdf because the paper "
            "does not currently embed numerical results."
        )
        return

    grouped: dict[str, list[float]] = defaultdict(list)
    for record in valid:
        grouped[str(record["metric_name"])].append(float(record["value_ms"]))

    metric_names = sorted(grouped)
    medians = [statistics.median(grouped[name]) for name in metric_names]
    latest_timestamp = max(str(record.get("timestamp_iso", "")) for record in valid)

    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(metric_names, medians, color="#4C72B0")
    ax.set_ylabel("Latency (ms)")
    ax.set_title("Evaluation Measurements")
    ax.tick_params(axis="x", rotation=20)
    ax.text(
        0.01,
        -0.24,
        f"Run timestamp: {latest_timestamp} | valid records: {len(valid)}",
        transform=ax.transAxes,
        fontsize=8,
    )

    figure_path = root / "paper" / "figures" / "fig_evaluation.pdf"
    figure_path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(figure_path)
    print(f"Plot saved as {figure_path}")


if __name__ == "__main__":
    generate_plots()
