#!/usr/bin/env python3
"""
Structural validation harness for Rescue OIS.

The current repository is a prototype scaffold, so this runner records the
planned evaluation scenarios without inventing latency values. When a scenario
is backed by real service instrumentation, replace the stub note with a timed
call and write the measured value to eval_metrics.jsonl.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path


METRICS_PATH = Path("eval_metrics.jsonl")


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def write_record(
    handle,
    *,
    run_id: str,
    scenario: str,
    metric_name: str,
    value_ms: float | None,
    notes: str,
) -> None:
    handle.write(
        json.dumps(
            {
                "run_id": run_id,
                "scenario": scenario,
                "metric_name": metric_name,
                "value_ms": value_ms,
                "timestamp_iso": now_iso(),
                "notes": notes,
            },
            sort_keys=True,
        )
        + "\n"
    )


def run_pilot() -> None:
    run_id = str(uuid.uuid4())
    records_written = 0
    measured_records = 0

    scenarios = [
        {
            "scenario": "incident_bootstrap",
            "metric_name": "incident_bootstrap_latency",
            "notes": "stub: command-edge bootstrap is not wired to a live core/edge service path in this harness",
        },
        {
            "scenario": "field_edit",
            "metric_name": "field_edit_propagation",
            "notes": "stub: responder outbox forwarding and command journal commit are scaffolded but not instrumented",
        },
        {
            "scenario": "wan_partition",
            "metric_name": "wan_recovery",
            "notes": "stub: partition script is a sleep-based scaffold and does not measure command-to-core backfill",
        },
        {
            "scenario": "command_promotion",
            "metric_name": "command_promotion_latency",
            "notes": "stub: promotion script requires an interactive Docker context and is not invoked by this non-interactive harness",
        },
        {
            "scenario": "offline_survivability",
            "metric_name": "offline_survivability",
            "notes": "stub: no sustained tablet offline, battery, or thermal scenario exists yet",
        },
        {
            "scenario": "duplicate_replay",
            "metric_name": "duplicate_idempotency_behavior",
            "notes": "stub: client_event_id duplicate replay is not yet validated under crash-injection testing",
        },
    ]

    with METRICS_PATH.open("w", encoding="utf-8") as handle:
        for item in scenarios:
            write_record(handle, run_id=run_id, value_ms=None, **item)
            records_written += 1

    print(
        f"Wrote {records_written} records to {METRICS_PATH} "
        f"({measured_records} with non-null values)."
    )


if __name__ == "__main__":
    run_pilot()
