#!/usr/bin/env python3
"""Raft leader-isolation harness: the missing producer for the paper's Table VI.

Why this file exists
--------------------
The paper reports a "Leader-minority partition" row (12/12 runs elected
L1 != L0, new-leader median 2.23 s, p95 3.02 s). Its numbers are real and
traceable to ``data/eval_raft_baseline.jsonl`` plus
``scripts/generate_raft_table.py`` in the paper tree, but **no committed script
produces them**: the repository's ``scripts/evaluate-raft-baseline.py`` has
exactly three scenarios (propagation, follower catch-up, quorum loss), and none
isolates the *leader* -- ``scenario_recovery`` isolates a follower via
``choose_follower`` and ``scenario_quorum_lost`` isolates the two non-leader
nodes. The row was therefore un-reproducible, which is a provenance gap rather
than a fabrication.

This script closes that gap. It writes ``eval_raft_baseline.jsonl`` in exactly
the schema ``generate_raft_table.py`` consumes, so the table can be regenerated
from a fresh run instead of from an orphaned data file.

Deliberately a separate script, not a fourth scenario in
``evaluate-raft-baseline.py``: that harness writes different scenario names to
a different artifact (``eval_metrics_raft.jsonl``), and conflating the two
would make the provenance worse, not better.

Prerequisites:
    cd baseline-raft && docker compose -p baseline-raft up -d --build
    A leader must be electable on 127.0.0.1:18001-18003.

Output:
    artifacts/data/eval_raft_baseline.jsonl
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import platform
import subprocess
import sys
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARTIFACT = ROOT / "artifacts" / "data" / "eval_raft_baseline.jsonl"
NETWORK_NAME = os.environ.get("RESCUE_OIS_NETWORK", "rescue-ois-net")

NODES: dict[str, dict[str, Any]] = {
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


def write_record(handle, **fields: Any) -> None:
    handle.write(json.dumps(fields, sort_keys=True, default=str) + "\n")
    handle.flush()


def run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=ROOT, check=False, capture_output=True, text=True)


def disconnect(node: str) -> None:
    run(["docker", "network", "disconnect", NETWORK_NAME, NODES[node]["container"]])


def connect(node: str) -> None:
    args = ["docker", "network", "connect"]
    for alias in NODES[node]["aliases"]:
        args.extend(["--alias", alias])
    args.extend([NETWORK_NAME, NODES[node]["container"]])
    run(args)


async def node_health(client: httpx.AsyncClient, node: str) -> dict | None:
    try:
        response = await client.get(f"{NODES[node]['url']}/health", timeout=2.0)
    except httpx.RequestError:
        return None
    return response.json() if response.status_code == 200 else None


async def cluster_roles(client: httpx.AsyncClient, exclude: set[str] | None = None) -> dict[str, dict]:
    exclude = exclude or set()
    roles: dict[str, dict] = {}
    for node in NODES:
        if node in exclude:
            continue
        health = await node_health(client, node)
        if health is not None:
            roles[node] = health
    return roles


async def wait_for_leader(
    client: httpx.AsyncClient, *, exclude: set[str] | None = None, timeout_s: float = 20.0
) -> tuple[str, str]:
    """Wait until a node outside ``exclude`` reports itself Leader."""
    deadline = time.perf_counter() + timeout_s
    while time.perf_counter() <= deadline:
        roles = await cluster_roles(client, exclude=exclude)
        for node, health in roles.items():
            if health.get("role") == "Leader":
                return node, NODES[node]["url"]
        await asyncio.sleep(0.1)
    raise RuntimeError(f"no leader outside {exclude or set()} within {timeout_s:.1f}s")


def event(incident_id: str, index: int) -> dict:
    return {
        "incident_id": incident_id,
        "event_seq": 0,
        "event_type": "observation",
        "payload": {"j": index},
        "device_id": "raft-authority-eval",
        "user_id": "u",
        "client_event_id": str(uuid.uuid4()),
        "created_at": now_iso(),
    }


def classify_isolated_write(status: int | None, body: Any) -> str:
    """Name what the isolated former leader did, without editorialising.

    The observed behaviour on hashicorp/raft is that the old leader accepts the
    request, blocks trying to replicate, then fails the apply once it notices it
    has lost leadership. That is reported verbatim rather than as "rejected",
    because the distinction matters: the write was not refused up front.

    ``unreachable_while_isolated`` is a *harness* outcome, not a Raft one: it
    means the probe could not reach L0 at all, so nothing was learned about what
    L0 does with a write. It is classified here for the record but rejected by
    ``summarise`` rather than reported as a finding -- see ``probe_isolated``.
    """
    if status is None:
        return "unreachable_while_isolated"
    if status == 200:
        return "accepted_while_isolated"
    text = json.dumps(body) if not isinstance(body, str) else body
    if "leadership lost" in text.lower():
        return "stall_then_apply_timeout"
    return f"rejected_status_{status}"


PROBE_MARKER = "__PROBE_META__"


async def probe_isolated(node: str, incident_id: str, seq: int) -> dict[str, Any]:
    """Ask the isolated former leader to accept one write; report what it did.

    The probe runs *inside* L0 against its own loopback, not from the host.
    ``docker network disconnect`` tears down the published-port forward
    immediately -- measured: the host cannot reach L0 at all once it is cut,
    on either probe, so a host-side probe can only ever record
    ``unreachable_while_isolated``, which describes the harness's network and
    not Raft. Loopback survives any partition and is the right analogue for the
    deployment anyway: the responder tablet sits on the isolated vehicle's own
    local network, not across the break.

    Timing comes from curl's ``time_total`` inside the container, so the
    ``docker exec`` startup cost is excluded from the measurement.
    """
    payload = json.dumps({"events": [event(incident_id, seq)]})
    args = [
        "docker", "exec", "-i", NODES[node]["container"],
        "curl", "-s", "-m", "10", "-X", "POST",
        "-H", "Content-Type: application/json", "--data-binary", "@-",
        "-w", f"\\n{PROBE_MARKER} %{{http_code}} %{{time_total}}",
        "http://127.0.0.1:8000/accept/event-batch",
    ]
    proc = await asyncio.create_subprocess_exec(
        *args,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, err = await proc.communicate(payload.encode())
    text = out.decode(errors="replace")

    status: int | None = None
    latency_ms = 0.0
    body: Any = text.strip()
    if PROBE_MARKER in text:
        head, _, meta = text.rpartition(PROBE_MARKER)
        parts = meta.split()
        if len(parts) >= 2:
            code = int(parts[0])
            # curl reports 000 when it never got an HTTP response at all.
            status = code if code else None
            latency_ms = float(parts[1]) * 1000.0
        body = head.strip()
        try:
            body = json.loads(body) if body else {"error": "empty response"}
        except ValueError:
            pass
    if status is None and not body:
        body = {"error": (err.decode(errors="replace").strip() or "no response")}

    return {
        "behavior": classify_isolated_write(status, body),
        "latency_ms": latency_ms,
        "reachable": status is not None,
        "response": body,
        "status_code": status,
    }


async def sanity_check(handle, run_id: str, client: httpx.AsyncClient) -> bool:
    """event_seq assignment + client_event_id dedup, as Table VI row 1 reports."""
    _, leader_url = await wait_for_leader(client)
    incident_id = str(uuid.uuid4())
    duplicate_cid = str(uuid.uuid4())
    first = event(incident_id, 0)
    first["client_event_id"] = duplicate_cid
    second = event(incident_id, 1)
    second["client_event_id"] = duplicate_cid

    t0 = time.perf_counter_ns()
    response = await client.post(
        f"{leader_url}/accept/event-batch", json={"events": [first, second]}, timeout=10.0
    )
    t1 = time.perf_counter_ns()
    raw = response.text
    parsed = response.json() if response.status_code == 200 else {}

    count_resp = await client.get(
        f"{leader_url}/journal/count?incident_id={incident_id}", timeout=5.0
    )
    journal_count = count_resp.json().get("count") if count_resp.status_code == 200 else None

    success = (
        response.status_code == 200
        and parsed.get("accepted") == 1
        and parsed.get("duplicates") == 1
        and journal_count == 1
    )
    write_record(
        handle,
        run_id=run_id,
        scenario="raft_sanity_event_seq_dedup",
        metric_name="sanity_check",
        value_ms=(t1 - t0) / 1e6,
        timestamp_iso=now_iso(),
        scenario_params={
            "duplicate_client_event_id": duplicate_cid,
            "event_batch_size": 2,
            "journal_count": journal_count,
            "leader": _leader_name(leader_url),
            "raw": raw,
            "response": parsed,
            "status_code": response.status_code,
            "success": success,
        },
        notes="",
    )
    return success


def _leader_name(url: str) -> str:
    for node, info in NODES.items():
        if info["url"] == url:
            return node
    return "unknown"


async def scenario_leader_isolation(
    handle, run_id: str, client: httpx.AsyncClient, *, runs: int, writes_per_run: int
) -> list[dict]:
    """Isolate the current leader; measure the election and both sides' writes.

    The isolated former leader is probed **twice**, because what it does is a
    function of when the write arrives, not a constant:

    * *in-window* -- issued immediately after the partition, while L0 still
      believes it leads. It accepts the write, blocks replicating it, and fails
      the apply ("leadership lost while committing log", HTTP 500). The client
      cannot tell whether the write landed.
    * *post-step-down* -- issued after L1 is elected, by which point L0 has
      noticed it lost quorum and refuses up front (HTTP 503, "not leader").

    Reporting only one of these would state a timing artefact as *the* behaviour
    of Raft under leader isolation. The paper's Table VI numbers are the
    in-window phase (all 12 original runs resolved the isolated write in
    417-458 ms against elections of 1713-3140 ms), so ``l0_isolated_write_*``
    stays bound to that probe for comparability; the post-step-down phase is
    recorded alongside it under ``l0_poststepdown_*``.

    Both probes reach L0 over a path that survives the partition, matching the
    deployment: a responder tablet is co-located with the command edge, so when
    the vehicle drives out of range the tablet is still connected to it. A probe
    from the far side of the partition would just talk to the new leader and
    measures the client's own network path, not Raft.
    """
    results: list[dict] = []
    for run_index in range(runs):
        health_before = await cluster_roles(client)
        l0, _l0_url = await wait_for_leader(client)
        incident_id = f"raft-partition-{uuid.uuid4()}"

        disconnect(l0)
        try:
            # The in-window probe runs *concurrently* with the election, not
            # before it: awaited first, its own duration would be added to
            # elected_ms and the paper's 2.23 s / 3.02 s would no longer be
            # comparable. Started here, it still lands inside the election
            # window, which is the property being measured.
            t0 = time.perf_counter_ns()
            probe_task = asyncio.create_task(probe_isolated(l0, incident_id, 999))
            try:
                l1, l1_url = await wait_for_leader(client, exclude={l0}, timeout_s=30.0)
                elected_ms = (time.perf_counter_ns() - t0) / 1e6
            finally:
                in_window = await probe_task
            health_after = await cluster_roles(client, exclude={l0})

            events = [event(incident_id, i) for i in range(writes_per_run)]
            l1_resp = await client.post(
                f"{l1_url}/accept/event-batch", json={"events": events}, timeout=15.0
            )
            l1_body = l1_resp.json() if l1_resp.status_code == 200 else {}
            l1_count_resp = await client.get(
                f"{l1_url}/journal/count?incident_id={incident_id}", timeout=5.0
            )
            l1_journal_count = (
                l1_count_resp.json().get("count") if l1_count_resp.status_code == 200 else None
            )

            post_step_down = await probe_isolated(l0, incident_id, 998)

            params = {
                # Recorded here, not merged in at write time: summarise() reads
                # this list, and if the key were absent it would silently fall
                # back to the isolated-write latency and report a ~10s timeout
                # as the election time.
                "time_to_new_leader_ms": elected_ms,
                "health_after_election": health_after,
                "health_before_partition": health_before,
                "incident_id": incident_id,
                "l0": l0,
                "l0_count_while_isolated": None,
                # Bound to the in-window probe: this is the phase the paper's
                # Table VI row reports, and generate_raft_table.py consumes.
                "l0_isolated_write_behavior": in_window["behavior"],
                "l0_isolated_write_latency_ms": in_window["latency_ms"],
                "l0_isolated_write_reachable": in_window["reachable"],
                "l0_isolated_write_response": in_window["response"],
                "l0_isolated_write_status_code": in_window["status_code"],
                "l0_poststepdown_write_behavior": post_step_down["behavior"],
                "l0_poststepdown_write_latency_ms": post_step_down["latency_ms"],
                "l0_poststepdown_write_reachable": post_step_down["reachable"],
                "l0_poststepdown_write_response": post_step_down["response"],
                "l0_poststepdown_write_status_code": post_step_down["status_code"],
                "l1": l1,
                "l1_differs_from_l0": l1 != l0,
                "l1_journal_count": l1_journal_count,
                "l1_last_acked_seq": l1_body.get("last_acked_seq"),
                "l1_write_accepted": l1_body.get("accepted"),
                "l1_write_status_code": l1_resp.status_code,
                "l1_writes_committed": bool(
                    l1_resp.status_code == 200
                    and l1_journal_count is not None
                    and l1_journal_count >= writes_per_run
                ),
                "run_index": run_index,
                "writes_per_run": writes_per_run,
            }
            results.append(params)
            write_record(
                handle,
                run_id=run_id,
                scenario="raft_leader_minority_partition",
                metric_name="run",
                value_ms=elected_ms,
                timestamp_iso=now_iso(),
                scenario_params={**params, "time_to_new_leader_ms": elected_ms},
                notes="",
            )
            print(
                f"  run {run_index}: L0={l0} -> L1={l1} "
                f"elected={elected_ms:.1f}ms committed={params['l1_writes_committed']} "
                f"l0(in-window)={params['l0_isolated_write_behavior']} "
                f"l0(post-step-down)={params['l0_poststepdown_write_behavior']}"
            )
        finally:
            connect(l0)
            await asyncio.sleep(3.0)
            try:
                await wait_for_leader(client, timeout_s=30.0)
            except RuntimeError as exc:
                print(f"  warning: cluster did not settle after run {run_index}: {exc}")
    return results


def summarise(results: list[dict]) -> dict:
    # No silent fallback to a different measurement: if the election timings are
    # missing, that is a harness bug and must surface, not be papered over with
    # whatever other latency happens to be in the record.
    elections = sorted(
        r["time_to_new_leader_ms"] for r in results if r.get("time_to_new_leader_ms") is not None
    )
    if results and not elections:
        raise RuntimeError(
            "no time_to_new_leader_ms in any run record; refusing to summarise "
            "election timing from unrelated measurements"
        )
    # An unreachable probe measures the harness's own network path, not Raft.
    # Left to pass through it would quietly turn the isolated-write column into
    # a statement about connectivity -- the exact substitution CL-10 was raised
    # for -- so it fails the run instead of being averaged in.
    unreachable = [
        r["run_index"] for r in results if not r.get("l0_isolated_write_reachable", True)
    ]
    if unreachable:
        raise RuntimeError(
            f"in-window probe could not reach L0 in run(s) {unreachable}: the isolated "
            "write was never delivered, so l0_isolated_write_behavior would describe the "
            "probe path rather than Raft. Keep L0 reachable over a path that survives the "
            "partition (published port, or a probe-only docker network) and re-run."
        )

    behaviours: dict[str, int] = {}
    post_behaviours: dict[str, int] = {}
    for r in results:
        behaviours[r["l0_isolated_write_behavior"]] = (
            behaviours.get(r["l0_isolated_write_behavior"], 0) + 1
        )
        post = r["l0_poststepdown_write_behavior"]
        post_behaviours[post] = post_behaviours.get(post, 0) + 1

    def pct(p: float) -> float:
        if not elections:
            return 0.0
        k = (len(elections) - 1) * (p / 100.0)
        lo, hi = int(k), min(int(k) + 1, len(elections) - 1)
        return elections[lo] if lo == hi else elections[lo] + (elections[hi] - elections[lo]) * (k - lo)

    n = len(results)
    return {
        "all_l1_differ_from_l0": all(r["l1_differs_from_l0"] for r in results),
        "all_l1_writes_committed": all(r["l1_writes_committed"] for r in results),
        "l0_isolated_write_median_ms": (
            sorted(r["l0_isolated_write_latency_ms"] for r in results)[len(results) // 2]
            if results
            else None
        ),
        "l0_poststepdown_write_behaviors": post_behaviours,
        "l0_write_behaviors": behaviours,
        "max_time_to_new_leader_ms": elections[-1] if elections else None,
        "median_time_to_new_leader_ms": pct(50),
        "min_time_to_new_leader_ms": elections[0] if elections else None,
        "n_runs": n,
        "new_leader_committed_writes": sum(1 for r in results if r["l1_writes_committed"]),
        "new_leader_elected": sum(1 for r in results if r["l1_differs_from_l0"]),
        "p95_time_to_new_leader_ms": pct(95),
        "writes_per_run": results[0]["writes_per_run"] if results else None,
    }


def git_tree_state() -> tuple[str | None, bool | None]:
    """HEAD, plus whether the working tree differed from it at run time.

    `git rev-parse HEAD` alone is not provenance. If the tree is dirty the hash
    names code that is *not* what produced the run -- which is exactly what
    happened to the 2026-09-18 datasets, whose recorded 746bea9e sat under 22
    modified and 7 untracked files. Record the dirty bit so a reader can tell the
    difference instead of trusting a hash that does not hold.
    """
    head = run(["git", "rev-parse", "HEAD"])
    commit = head.stdout.strip() if head.returncode == 0 else None
    status = run(["git", "status", "--porcelain"])
    dirty = bool(status.stdout.strip()) if status.returncode == 0 else None
    return commit, dirty


def collect_environment() -> dict[str, Any]:
    docker_v = run(["docker", "version", "--format", "{{.Server.Version}}"])
    compose_v = run(["docker", "compose", "version", "--short"])
    git_commit, git_dirty = git_tree_state()
    return {
        "docker_compose_version": compose_v.stdout.strip() or None,
        "docker_server_version": docker_v.stdout.strip() or None,
        "git_commit": git_commit,
        "git_tree_dirty": git_dirty,
        "host_cpu_count": os.cpu_count(),
        "host_uname": " ".join(platform.uname()),
        "timestamp_iso": now_iso(),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=int, default=12, help="leader-isolation runs (paper used 12)")
    parser.add_argument("--writes-per-run", type=int, default=5)
    parser.add_argument("--smoke", action="store_true", help="2 runs, for a sanity gate")
    parser.add_argument("--artifact", default=str(DEFAULT_ARTIFACT))
    return parser.parse_args()


async def _collect(handle, run_id: str, args: argparse.Namespace, env_meta: dict) -> int:
    """Async half of the run.

    Kept separate from ``main`` so the artifact file is opened by synchronous
    code: opening it inside an ``async def`` is blocking I/O on the event loop
    (ruff ASYNC230).
    """
    write_record(
        handle,
        run_id=run_id,
        scenario="raft_baseline",
        metric_name="environment",
        value_ms=None,
        timestamp_iso=now_iso(),
        scenario_params={
            "nodes": {k: {"container": v["container"], "url": v["url"]} for k, v in NODES.items()},
            "partition_runs": args.runs,
            "writes_per_partition_run": args.writes_per_run,
        },
        environment=env_meta,
        notes="3-voter hashicorp/raft baseline; in-memory log/snapshot/FSM",
    )

    async with httpx.AsyncClient() as client:
        print("sanity check...")
        if not await sanity_check(handle, run_id, client):
            print("ERROR: sanity check failed; aborting before partition runs", file=sys.stderr)
            return 2

        print("leader-isolation runs...")
        results = await scenario_leader_isolation(
            handle, run_id, client, runs=args.runs, writes_per_run=args.writes_per_run
        )

    summary = summarise(results)
    write_record(
        handle,
        run_id=run_id,
        scenario="raft_leader_minority_partition",
        metric_name="summary",
        value_ms=summary["median_time_to_new_leader_ms"],
        timestamp_iso=now_iso(),
        scenario_params=summary,
        notes="",
    )
    print(json.dumps(summary, indent=2, sort_keys=True, default=str))
    return 0


def main() -> int:
    args = parse_args()
    if args.smoke:
        args.runs = 2
    run_id = str(uuid.uuid4())
    artifact = Path(args.artifact)
    artifact.parent.mkdir(parents=True, exist_ok=True)
    env_meta = collect_environment()
    print(f"run_id={run_id} runs={args.runs} writes_per_run={args.writes_per_run}")

    with artifact.open("w", encoding="utf-8") as handle:
        rc = asyncio.run(_collect(handle, run_id, args, env_meta))

    print(f"done. records in {artifact}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
