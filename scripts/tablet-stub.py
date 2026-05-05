#!/usr/bin/env python3
"""Tablet stub: emit synthetic field edits at a configurable rate.

Used by evaluate-pilot.py to drive bootstrap, propagation, throughput, and
scaling scenarios. Not a replacement for the Android app; purely a workload
generator for the emulation harness.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from datetime import UTC, datetime
from uuid import UUID, uuid4

import httpx


async def submit_one(
    client: httpx.AsyncClient,
    base_url: str,
    incident_id: UUID,
    idx: int,
    device_id: str,
) -> dict:
    body = {
        "client_event_id": str(uuid4()),
        "incident_id": str(incident_id),
        "event_type": "observation",
        "payload": {"idx": idx, "note": f"event-{idx}"},
        "device_id": device_id,
        "user_id": "stub-user",
        "occurred_at": datetime.now(UTC).isoformat(),
    }
    t0 = time.perf_counter_ns()
    resp = await client.post(f"{base_url}/api/events", json=body, timeout=10.0)
    t1 = time.perf_counter_ns()
    return {
        "client_event_id": body["client_event_id"],
        "incident_id": body["incident_id"],
        "submit_ns": t0,
        "ack_ns": t1,
        "submit_latency_ms": (t1 - t0) / 1e6,
        "status_code": resp.status_code,
        "ack_status": resp.json().get("status"),
    }


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", required=True, help="Responder ops-api base URL")
    ap.add_argument("--incident-id", required=True)
    ap.add_argument("--count", type=int, default=100, help="Number of events to submit")
    ap.add_argument("--rate", type=float, default=10.0, help="Events per second target")
    ap.add_argument("--device-id", default="tab-stub-1")
    ap.add_argument("--out", default="/dev/stdout", help="JSONL file to write per-event records")
    args = ap.parse_args()

    incident_id = UUID(args.incident_id)
    interval = 1.0 / max(args.rate, 0.001)

    async with httpx.AsyncClient() as client:
        with open(args.out, "a", encoding="utf-8") as handle:
            for i in range(args.count):
                rec = await submit_one(client, args.base_url, incident_id, i, args.device_id)
                handle.write(json.dumps(rec) + "\n")
                handle.flush()
                await asyncio.sleep(interval)


if __name__ == "__main__":
    asyncio.run(main())
