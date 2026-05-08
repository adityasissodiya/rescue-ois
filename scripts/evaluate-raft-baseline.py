#!/usr/bin/env python3
"""Phase 4 Raft baseline evaluator.

Drives the Rescue OIS comparison scenarios against the 3-node hashicorp/raft
cluster in baseline-raft/. Output goes to paper/data/eval_metrics_raft.jsonl
following the same schema as paper/data/eval_metrics.jsonl with one extra
field: scenario_params.baseline = "raft".
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

import httpx

METRICS_PATH = Path("paper/data/eval_metrics_raft.jsonl")
RUNS_PER_CELL = int(os.environ.get("RUNS_PER_CELL", "30"))

NODES = {
    "raftd-1": {
        "url": "http://127.0.0.1:18001",
        "container": "baseline-raft-raftd-1-1",
        "aliases": ["raftd-1", "raftd.baseline-1"],
    },
    "raftd-2": {
        "url": "http://127.0.0.1:18002",
        "container": "baseline-raft-raftd-2-1",
        "aliases": ["raftd-2", "raftd.baseline-2"],
    },
    "raftd-3": {
        "url": "http://127.0.0.1:18003",
        "container": "baseline-raft-raftd-3-1",
        "aliases": ["raftd-3", "raftd.baseline-3"],
    },
}


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def write_record(handle, **fields) -> None:
    handle.write(json.dumps(fields, sort_keys=True, default=str) + "\n")
    handle.flush()


async def cluster_roles(client: httpx.AsyncClient) -> dict[str, dict]:
    roles: dict[str, dict] = {}
    for node, info in NODES.items():
        try:
            response = await client.get(f"{info['url']}/health", timeout=2.0)
            if response.status_code == 200:
                roles[node] = response.json()
        except httpx.RequestError:
            continue
    return roles


async def find_leader(client: httpx.AsyncClient) -> tuple[str, str]:
    roles = await cluster_roles(client)
    for node, health in roles.items():
        if health.get("role") == "Leader":
            return node, NODES[node]["url"]
    raise RuntimeError(f"no Raft leader reachable; roles={roles}")


async def wait_for_leader(client: httpx.AsyncClient, timeout_s: float = 15.0) -> tuple[str, str]:
    deadline = time.perf_counter() + timeout_s
    last_error: Exception | None = None
    while time.perf_counter() <= deadline:
        try:
            return await find_leader(client)
        except Exception as exc:
            last_error = exc
            await asyncio.sleep(0.2)
    raise RuntimeError(f"no Raft leader reachable after {timeout_s:.1f}s: {last_error}")


async def choose_follower(client: httpx.AsyncClient) -> str:
    await wait_for_leader(client)
    roles = await cluster_roles(client)
    for node, health in roles.items():
        if health.get("role") == "Follower":
            return node
    raise RuntimeError(f"no Raft follower reachable; roles={roles}")


async def post_with_leader_retry(client: httpx.AsyncClient, body: dict, max_retries: int = 5) -> dict:
    _, leader_url = await wait_for_leader(client)
    for _ in range(max_retries):
        response = await client.post(f"{leader_url}/accept/event-batch", json=body, timeout=10.0)
        if response.status_code == 200:
            return response.json()
        if response.status_code == 503:
            await asyncio.sleep(0.2)
            _, leader_url = await wait_for_leader(client)
            continue
        response.raise_for_status()
    raise RuntimeError("no leader after retries")


def event(incident_id: uuid.UUID, index: int) -> dict:
    return {
        "incident_id": str(incident_id),
        "event_seq": 0,
        "event_type": "observation",
        "payload": {"j": index},
        "device_id": "tab-eval",
        "user_id": "u",
        "client_event_id": str(uuid.uuid4()),
        "created_at": now_iso(),
    }


def disconnect(node: str) -> None:
    subprocess.run(
        ["docker", "network", "disconnect", "rescue-ois-net", NODES[node]["container"]],
        check=False,
    )


def connect(node: str) -> None:
    args = ["docker", "network", "connect"]
    for alias in NODES[node]["aliases"]:
        args.extend(["--alias", alias])
    args.extend(["rescue-ois-net", NODES[node]["container"]])
    subprocess.run(args, check=False)


async def scenario_propagation(handle, run_id: str) -> None:
    async with httpx.AsyncClient() as client:
        for queue_depth in (1, 10, 100):
            for run_index in range(RUNS_PER_CELL):
                incident_id = uuid.uuid4()
                events = [event(incident_id, index) for index in range(queue_depth)]
                t0 = time.perf_counter_ns()
                try:
                    await post_with_leader_retry(client, {"events": events})
                    t1 = time.perf_counter_ns()
                    value_ms = (t1 - t0) / 1e6
                    notes = ""
                except Exception as exc:
                    value_ms = None
                    notes = f"error: {type(exc).__name__}: {exc}"
                write_record(
                    handle,
                    run_id=run_id,
                    scenario="baseline_raft_propagation",
                    metric_name="end_to_end_propagation_ms",
                    value_ms=value_ms,
                    timestamp_iso=now_iso(),
                    scenario_params={"baseline": "raft", "queue_depth": queue_depth},
                    run_index=run_index,
                    notes=notes,
                )


async def scenario_recovery(handle, run_id: str) -> None:
    async with httpx.AsyncClient() as client:
        for partition_s in (10, 60):
            for run_index in range(RUNS_PER_CELL):
                incident_id = uuid.uuid4()
                isolated = await choose_follower(client)
                disconnect(isolated)
                try:
                    events = [event(incident_id, index) for index in range(20)]
                    await post_with_leader_retry(client, {"events": events})
                    notes = "quorum maintained throughout"
                except Exception as exc:
                    notes = f"writes failed during partition: {type(exc).__name__}: {exc}"

                await asyncio.sleep(partition_s)
                connect(isolated)
                try:
                    await wait_for_leader(client)
                except Exception:
                    pass

                t0 = time.perf_counter_ns()
                deadline = t0 + int(120e9)
                catch_up = False
                while time.perf_counter_ns() <= deadline:
                    try:
                        follower = await client.get(
                            f"{NODES[isolated]['url']}/journal/count?incident_id={incident_id}",
                            timeout=2.0,
                        )
                        _, leader_url = await find_leader(client)
                        leader = await client.get(
                            f"{leader_url}/journal/count?incident_id={incident_id}",
                            timeout=2.0,
                        )
                        if follower.status_code == 200 and leader.status_code == 200:
                            if follower.json()["count"] >= leader.json()["count"]:
                                catch_up = True
                                break
                    except Exception:
                        pass
                    await asyncio.sleep(0.05)
                t1 = time.perf_counter_ns()

                write_record(
                    handle,
                    run_id=run_id,
                    scenario="baseline_raft_follower_catch_up",
                    metric_name="follower_catch_up_ms",
                    value_ms=(t1 - t0) / 1e6 if catch_up else None,
                    timestamp_iso=now_iso(),
                    scenario_params={
                        "baseline": "raft",
                        "partition_s": partition_s,
                        "isolated_count": 1,
                        "isolated_node": isolated,
                    },
                    run_index=run_index,
                    notes=notes if catch_up else f"{notes}; follower catch-up timed out",
                )


async def scenario_quorum_lost(handle, run_id: str) -> None:
    async with httpx.AsyncClient() as client:
        for partition_s in (30,):
            for run_index in range(min(RUNS_PER_CELL, 10)):
                leader_node, _ = await wait_for_leader(client)
                isolated = [node for node in NODES if node != leader_node]
                incident_id = uuid.uuid4()
                for node in isolated:
                    disconnect(node)
                try:
                    events = [event(incident_id, 0)]
                    t0 = time.perf_counter_ns()
                    write_succeeded = False
                    try:
                        await post_with_leader_retry(client, {"events": events}, max_retries=1)
                        write_succeeded = True
                    except Exception:
                        pass
                    t1 = time.perf_counter_ns()

                    write_record(
                        handle,
                        run_id=run_id,
                        scenario="baseline_raft_quorum_lost",
                        metric_name="write_attempt_during_quorum_loss_ms",
                        value_ms=(t1 - t0) / 1e6,
                        timestamp_iso=now_iso(),
                        scenario_params={
                            "baseline": "raft",
                            "partition_s": partition_s,
                            "isolated_count": 2,
                            "isolated_nodes": isolated,
                            "write_succeeded": write_succeeded,
                        },
                        run_index=run_index,
                        notes="expected: write_succeeded == false (quorum lost)",
                    )

                    await asyncio.sleep(partition_s)
                finally:
                    for node in isolated:
                        connect(node)
                    await asyncio.sleep(3.0)


async def main() -> None:
    run_id = str(uuid.uuid4())
    print(f"run_id={run_id}, runs_per_cell={RUNS_PER_CELL}")
    METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with METRICS_PATH.open("w", encoding="utf-8") as handle:
        for scenario in (scenario_propagation, scenario_recovery, scenario_quorum_lost):
            print(f"running {scenario.__name__}...")
            try:
                await scenario(handle, run_id)
            except Exception as exc:
                print(f"  {scenario.__name__} failed: {exc}")
                write_record(
                    handle,
                    run_id=run_id,
                    scenario=scenario.__name__,
                    metric_name="harness_error",
                    value_ms=None,
                    timestamp_iso=now_iso(),
                    scenario_params={"baseline": "raft"},
                    run_index=-1,
                    notes=f"{type(exc).__name__}: {exc}",
                )
    print(f"done. records in {METRICS_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
