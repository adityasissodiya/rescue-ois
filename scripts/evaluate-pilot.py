#!/usr/bin/env python3
"""Phase 2 evaluation harness for Rescue OIS.

Drives six scenarios against the running Docker Compose stack and writes
measured records to eval_metrics.jsonl following the ADR-0006 schema with
two extensions: scenario_params (dict of per-cell parameters) and run_index
(0..N-1 within each cell). All numeric values are real measurements; null is
only used for explicitly unsupported phases.

Prerequisites:
    ./scripts/dev-up.sh
    DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:5432/rescue_ois ./scripts/run-migrations.sh core
    DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:5432/rescue_ois_edge ./scripts/run-migrations.sh edge

Run:
    python3 scripts/evaluate-pilot.py
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

RUNS_PER_CELL = int(os.environ.get("RUNS_PER_CELL", "30"))
METRICS_PATH = Path(os.environ.get("RESCUE_OIS_METRICS_PATH", "artifacts/data/eval_metrics.jsonl"))

CORE_BASE = os.environ.get("CORE_BASE", "http://127.0.0.1:18000")
RESP_OPS = os.environ.get("RESP_OPS", "http://127.0.0.1:18101")
CMD_SYNCD = os.environ.get("CMD_SYNCD", "http://127.0.0.1:18081")


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def write_record(handle, **fields: Any) -> None:
    handle.write(json.dumps(fields, sort_keys=True, default=str) + "\n")
    handle.flush()


def docker_exec(container: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["docker", "exec", container, *args],
        check=True,
        capture_output=True,
        text=True,
    )


def reset_dbs() -> None:
    """Truncate journal/outbox/state between scenarios for clean cells."""
    docker_exec(
        "edge-cmd-postgres-1",
        "psql",
        "-U",
        "postgres",
        "rescue_ois_edge",
        "-c",
        "TRUNCATE incident.journal, incident.state, outbox.device_outbox CASCADE; "
        "DELETE FROM sync.state;",
    )
    docker_exec(
        "core-postgres-1",
        "psql",
        "-U",
        "postgres",
        "rescue_ois",
        "-c",
        "TRUNCATE master.incident_events, master.incidents CASCADE;",
    )
    out = subprocess.run(
        ["docker", "ps", "--format", "{{.Names}}"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    for name in out:
        if name.startswith("edge-resp-") and name.endswith("-postgres-1"):
            docker_exec(
                name,
                "psql",
                "-U",
                "postgres",
                "rescue_ois_edge",
                "-c",
                "TRUNCATE outbox.device_outbox CASCADE;",
            )


async def scenario_bootstrap(handle, run_id: str) -> None:
    """Bootstrap latency vs incident size."""
    async with httpx.AsyncClient() as client:
        for aoi in (10, 50, 200, 1000):
            for i in range(RUNS_PER_CELL):
                inc_id = uuid.uuid4()
                t0 = time.perf_counter_ns()
                resp = await client.get(
                    f"{CORE_BASE}/sync/bootstrap",
                    params={"incident_id": str(inc_id), "aoi_polygons": aoi},
                    timeout=30.0,
                )
                t1 = time.perf_counter_ns()
                ok = resp.status_code == 200
                write_record(
                    handle,
                    run_id=run_id,
                    scenario="bootstrap_latency",
                    metric_name="bootstrap_latency_ms",
                    value_ms=(t1 - t0) / 1e6 if ok else None,
                    timestamp_iso=now_iso(),
                    scenario_params={"aoi_polygons": aoi},
                    run_index=i,
                    notes="" if ok else f"http_status={resp.status_code}",
                )


async def scenario_propagation(handle, run_id: str) -> None:
    """Field edit propagation latency: tablet -> outbox -> command journal."""
    async with httpx.AsyncClient() as client:
        for queue_depth in (1, 10, 100):
            for i in range(RUNS_PER_CELL):
                reset_dbs()
                inc_id = uuid.uuid4()
                t_submit_start = time.perf_counter_ns()
                for j in range(queue_depth):
                    body = {
                        "client_event_id": str(uuid.uuid4()),
                        "incident_id": str(inc_id),
                        "event_type": "observation",
                        "payload": {"j": j},
                        "device_id": "tab-eval",
                        "user_id": "u",
                        "occurred_at": now_iso(),
                    }
                    await client.post(f"{RESP_OPS}/api/events", json=body, timeout=10.0)
                deadline = time.perf_counter_ns() + int(60e9)
                while True:
                    out = docker_exec(
                        "edge-cmd-postgres-1",
                        "psql",
                        "-U",
                        "postgres",
                        "rescue_ois_edge",
                        "-tAc",
                        f"SELECT count(*) FROM incident.journal WHERE incident_id = '{inc_id}'",
                    )
                    n = int(out.stdout.strip() or "0")
                    if n >= queue_depth or time.perf_counter_ns() > deadline:
                        break
                    await asyncio.sleep(0.02)
                t_done = time.perf_counter_ns()
                value_ms = (t_done - t_submit_start) / 1e6 if n >= queue_depth else None
                write_record(
                    handle,
                    run_id=run_id,
                    scenario="field_edit_propagation",
                    metric_name="end_to_end_propagation_ms",
                    value_ms=value_ms,
                    timestamp_iso=now_iso(),
                    scenario_params={"queue_depth": queue_depth},
                    run_index=i,
                    notes="" if value_ms is not None else "deadline_exceeded",
                )


async def scenario_recovery(handle, run_id: str) -> None:
    """Recovery time after WAN partition of varying duration."""
    async with httpx.AsyncClient() as client:
        for partition_s in (1, 10, 60):
            for i in range(RUNS_PER_CELL):
                reset_dbs()
                inc_id = uuid.uuid4()
                proc = subprocess.Popen(
                    ["./scripts/inject-partition.sh", "wan", str(partition_s)],
                    env={**os.environ, "RESCUE_OIS_RUN_ID": run_id},
                )
                for j in range(20):
                    body = {
                        "client_event_id": str(uuid.uuid4()),
                        "incident_id": str(inc_id),
                        "event_type": "observation",
                        "payload": {"j": j},
                        "device_id": "tab-eval",
                        "user_id": "u",
                        "occurred_at": now_iso(),
                    }
                    await client.post(f"{RESP_OPS}/api/events", json=body, timeout=10.0)
                proc.wait()
                t0 = time.perf_counter_ns()
                deadline = t0 + int(120e9)
                while True:
                    out = docker_exec(
                        "core-postgres-1",
                        "psql",
                        "-U",
                        "postgres",
                        "rescue_ois",
                        "-tAc",
                        f"SELECT count(*) FROM master.incident_events WHERE incident_id = '{inc_id}'",
                    )
                    n = int(out.stdout.strip() or "0")
                    if n >= 20 or time.perf_counter_ns() > deadline:
                        break
                    await asyncio.sleep(0.05)
                t1 = time.perf_counter_ns()
                value_ms = (t1 - t0) / 1e6 if n >= 20 else None
                write_record(
                    handle,
                    run_id=run_id,
                    scenario="wan_recovery",
                    metric_name="recovery_to_core_ms",
                    value_ms=value_ms,
                    timestamp_iso=now_iso(),
                    scenario_params={"partition_s": partition_s},
                    run_index=i,
                    notes="" if value_ms is not None else "deadline_exceeded",
                )


def _journal_count(inc_id: uuid.UUID) -> int:
    out = docker_exec(
        "edge-cmd-postgres-1",
        "psql",
        "-U",
        "postgres",
        "rescue_ois_edge",
        "-tAc",
        f"SELECT count(*) FROM incident.journal WHERE incident_id = '{inc_id}'",
    )
    return int(out.stdout.strip() or "0")


def _current_command_epoch() -> int:
    """Read the command's current epoch so direct accept-path posts carry a
    matching X-Command-Epoch header (the responder push path self-corrects via
    409 bodies, but direct posts must supply it)."""
    out = docker_exec(
        "edge-cmd-postgres-1",
        "psql",
        "-U",
        "postgres",
        "rescue_ois_edge",
        "-tAc",
        "SELECT epoch_id FROM incident.current_epoch",
    )
    return int(out.stdout.strip() or "0")


async def scenario_throughput(handle, run_id: str) -> None:
    """Command-edge commit throughput at saturation, two endpoints.

    ``command_throughput`` (direct): 1000 concurrent single-event POSTs to the
    command syncd ``/accept/event-batch`` endpoint. This isolates the command
    accept handler and incident-journal serialization -- the prototype's
    linearization point -- with no responder, outbox, or push-batching in the
    path.

    ``command_throughput_endtoend``: the same 1000-concurrent load issued to
    the responder ``/api/events`` endpoint, traversing the full
    responder ops-api -> outbox -> push-batching -> command-accept pipeline.
    This characterizes M3 + M1/M2 together, not the journal serialization
    point, and includes the push poll/batch sleeps by construction.
    """
    n = 1000

    # --- direct: command syncd /accept/event-batch (linearization point) ---
    epoch = _current_command_epoch()
    epoch_headers = {"X-Command-Epoch": str(epoch)}
    # The journal write serializes on a FOR UPDATE of incident.state, so a
    # bounded in-flight count saturates the linearization point; an unbounded
    # 1000 only exhausts the client connection pool.
    direct_limits = httpx.Limits(max_connections=64, max_keepalive_connections=64)
    direct_sem = asyncio.Semaphore(64)
    async with httpx.AsyncClient(limits=direct_limits) as client:
        for i in range(RUNS_PER_CELL):
            reset_dbs()
            inc_id = uuid.uuid4()
            t0 = time.perf_counter_ns()

            async def one_direct(j: int) -> None:
                body = {
                    "events": [
                        {
                            "id": str(uuid.uuid4()),
                            "incident_id": str(inc_id),
                            "client_event_id": str(uuid.uuid4()),
                            "device_id": "tab-eval",
                            "user_id": "u",
                            "event_type": "observation",
                            "payload": {"j": j},
                            "created_at": now_iso(),
                        }
                    ]
                }
                async with direct_sem:
                    await client.post(
                        f"{CMD_SYNCD}/accept/event-batch",
                        json=body,
                        headers=epoch_headers,
                        timeout=15.0,
                    )

            await asyncio.gather(*[one_direct(j) for j in range(n)])
            deadline = time.perf_counter_ns() + int(120e9)
            while True:
                got = _journal_count(inc_id)
                if got >= n or time.perf_counter_ns() > deadline:
                    break
                await asyncio.sleep(0.02)
            t1 = time.perf_counter_ns()
            elapsed_s = (t1 - t0) / 1e9
            tput = got / elapsed_s if elapsed_s > 0 else None
            write_record(
                handle,
                run_id=run_id,
                scenario="command_throughput",
                metric_name="events_per_sec",
                value_ms=None,
                timestamp_iso=now_iso(),
                scenario_params={
                    "endpoint": "command-syncd /accept/event-batch (direct)",
                    "target_n": n,
                    "achieved": got,
                    "elapsed_s": elapsed_s,
                    "events_per_sec": tput,
                },
                run_index=i,
                notes="warmup_run: exclude from Section VI summaries" if i == 0 else "",
            )

        # --- end-to-end: responder /api/events -> outbox -> push -> command ---
        for i in range(RUNS_PER_CELL):
            reset_dbs()
            inc_id = uuid.uuid4()
            t0 = time.perf_counter_ns()

            async def one_e2e(j: int) -> None:
                body = {
                    "client_event_id": str(uuid.uuid4()),
                    "incident_id": str(inc_id),
                    "event_type": "observation",
                    "payload": {"j": j},
                    "device_id": "tab-eval",
                    "user_id": "u",
                    "occurred_at": now_iso(),
                }
                # ops-api closes idle keepalive connections under sustained
                # load; reusing one then yields RemoteProtocolError. Retry once
                # on a server-side disconnect so a dropped keepalive does not
                # abort the run.
                async with direct_sem:
                    for attempt in range(2):
                        try:
                            await e2e_client.post(f"{RESP_OPS}/api/events", json=body, timeout=15.0)
                            return
                        except httpx.RemoteProtocolError:
                            if attempt == 1:
                                raise

            # Fresh per-run client with keepalive disabled to avoid reusing a
            # connection the server may have already closed.
            async with httpx.AsyncClient(
                limits=httpx.Limits(max_connections=64, max_keepalive_connections=0)
            ) as e2e_client:
                await asyncio.gather(*[one_e2e(j) for j in range(n)])
            deadline = time.perf_counter_ns() + int(120e9)
            while True:
                got = _journal_count(inc_id)
                if got >= n or time.perf_counter_ns() > deadline:
                    break
                await asyncio.sleep(0.02)
            t1 = time.perf_counter_ns()
            elapsed_s = (t1 - t0) / 1e9
            tput = got / elapsed_s if elapsed_s > 0 else None
            write_record(
                handle,
                run_id=run_id,
                scenario="command_throughput_endtoend",
                metric_name="events_per_sec",
                value_ms=None,
                timestamp_iso=now_iso(),
                scenario_params={
                    "endpoint": "responder /api/events (full pipeline)",
                    "target_n": n,
                    "achieved": got,
                    "elapsed_s": elapsed_s,
                    "events_per_sec": tput,
                },
                run_index=i,
                notes="warmup_run: exclude from Section VI summaries" if i == 0 else "",
            )


async def scenario_idempotency(handle, run_id: str) -> None:
    """Replay every event 5x; expect exactly one journal row per client_event_id."""
    async with httpx.AsyncClient() as client:
        for i in range(RUNS_PER_CELL):
            reset_dbs()
            inc_id = uuid.uuid4()
            cids = [str(uuid.uuid4()) for _ in range(50)]
            for replay in range(5):
                for j, cid in enumerate(cids):
                    body = {
                        "client_event_id": cid,
                        "incident_id": str(inc_id),
                        "event_type": "observation",
                        "payload": {"j": j, "replay": replay},
                        "device_id": "tab-eval",
                        "user_id": "u",
                        "occurred_at": now_iso(),
                    }
                    await client.post(f"{RESP_OPS}/api/events", json=body, timeout=10.0)
            await asyncio.sleep(2.0)
            out = docker_exec(
                "edge-cmd-postgres-1",
                "psql",
                "-U",
                "postgres",
                "rescue_ois_edge",
                "-tAc",
                f"SELECT count(*) FROM incident.journal WHERE incident_id = '{inc_id}'",
            )
            stored = int(out.stdout.strip() or "0")
            write_record(
                handle,
                run_id=run_id,
                scenario="duplicate_replay",
                metric_name="stored_events",
                value_ms=None,
                timestamp_iso=now_iso(),
                scenario_params={
                    "unique_events": len(cids),
                    "replays_per_event": 5,
                    "stored": stored,
                },
                run_index=i,
                notes="ok" if stored == len(cids) else "violation",
            )


async def scenario_promotion(handle, run_id: str) -> None:
    """Manual promotion latency: invoke promote-responder.sh, time the role flip."""
    for i in range(RUNS_PER_CELL):
        write_record(
            handle,
            run_id=run_id,
            scenario="command_promotion",
            metric_name="command_promotion_latency_ms",
            value_ms=None,
            timestamp_iso=now_iso(),
            scenario_params={"i": i},
            run_index=i,
            notes="skipped: requires interactive promote-responder.sh; run that script directly to measure",
        )


async def main() -> None:
    run_id = str(uuid.uuid4())
    print(f"run_id={run_id}, runs_per_cell={RUNS_PER_CELL}")
    METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with METRICS_PATH.open("w", encoding="utf-8") as handle:
        for fn in (
            scenario_bootstrap,
            scenario_propagation,
            scenario_recovery,
            scenario_throughput,
            scenario_idempotency,
            scenario_promotion,
        ):
            print(f"running {fn.__name__}...")
            try:
                await fn(handle, run_id)
            except Exception as e:
                print(f"  {fn.__name__} failed: {e}")
                write_record(
                    handle,
                    run_id=run_id,
                    scenario=fn.__name__,
                    metric_name="harness_error",
                    value_ms=None,
                    timestamp_iso=now_iso(),
                    scenario_params={},
                    run_index=-1,
                    notes=f"{type(e).__name__}: {e}",
                )
    print(f"done. records in {METRICS_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
