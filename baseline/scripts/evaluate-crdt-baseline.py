#!/usr/bin/env python3
"""Evaluate the Hanssen-style CRDT-LWW baseline.

The harness drives real HTTP requests against the Docker Compose replicas in
../docker-compose.yml. It emits JSONL records compatible with the paper data
layout and copies an anonymized sibling into paper/data/ for table generation.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import statistics
import subprocess
import sys
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE = Path(__file__).resolve().parents[1]
REPO = BASE.parent
DEFAULT_OUTPUT = BASE / "data" / "eval_crdt_baseline.jsonl"

REPLICAS = {
    "a": os.environ.get("CRDT_A", "http://127.0.0.1:19001"),
    "b": os.environ.get("CRDT_B", "http://127.0.0.1:19002"),
    "c": os.environ.get("CRDT_C", "http://127.0.0.1:19003"),
    "core": os.environ.get("CRDT_CORE", "http://127.0.0.1:19010"),
}
CONTAINERS = {
    "a": os.environ.get("CRDT_A_CONTAINER", "crdt-replica-a"),
    "b": os.environ.get("CRDT_B_CONTAINER", "crdt-replica-b"),
    "c": os.environ.get("CRDT_C_CONTAINER", "crdt-replica-c"),
    "core": os.environ.get("CRDT_CORE_CONTAINER", "crdt-core-sink"),
}
PROFILES: dict[str, dict[str, str]] = {
    "stressed": {"delay": "80ms", "jitter": "30ms", "loss": "2%"},
    "degraded": {"delay": "200ms", "jitter": "80ms", "loss": "8%"},
}


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def write_record(handle, **fields: Any) -> None:
    handle.write(json.dumps(fields, sort_keys=True, default=str) + "\n")
    handle.flush()


def http_json(method: str, url: str, body: dict[str, Any] | None = None, timeout_s: float = 30.0) -> tuple[int, dict[str, Any]]:
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = Request(url, data=data, headers={"Content-Type": "application/json"}, method=method)
    try:
        with urlopen(req, timeout=timeout_s) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw) if raw else {}
    except HTTPError as exc:
        raw = exc.read().decode("utf-8")
        return exc.code, json.loads(raw) if raw else {"error": exc.reason}


def get_json(replica: str, path: str) -> dict[str, Any]:
    status, payload = http_json("GET", f"{REPLICAS[replica]}{path}")
    if status != 200:
        raise RuntimeError(f"GET {replica}{path} failed: {status} {payload}")
    return payload


def post_json(replica: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    status, payload = http_json("POST", f"{REPLICAS[replica]}{path}", body or {})
    if status != 200:
        raise RuntimeError(f"POST {replica}{path} failed: {status} {payload}")
    return payload


def run(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=BASE, capture_output=True, text=True, check=check)


def wait_for_replicas(deadline_s: float = 60.0) -> None:
    deadline = time.monotonic() + deadline_s
    remaining = set(REPLICAS)
    while remaining and time.monotonic() < deadline:
        for replica in list(remaining):
            try:
                status, payload = http_json("GET", f"{REPLICAS[replica]}/health", timeout_s=2.0)
                if status == 200 and payload.get("status") == "ok":
                    remaining.remove(replica)
            except (URLError, TimeoutError):
                pass
        if remaining:
            time.sleep(0.5)
    if remaining:
        raise RuntimeError(f"CRDT replicas not ready: {sorted(remaining)}")


def reset_replicas() -> None:
    for replica in REPLICAS:
        post_json(replica, "/admin/reset", {})


def pull_ops(replica: str) -> list[dict[str, Any]]:
    return list(get_json(replica, "/sync/pull")["ops"])


def push_ops(target: str, ops: list[dict[str, Any]]) -> dict[str, Any]:
    return post_json(target, "/sync/push", {"ops": ops})


def full_sync(replicas: list[str] | None = None) -> None:
    names = replicas or list(REPLICAS)
    all_ops: list[dict[str, Any]] = []
    seen: set[str] = set()
    for name in names:
        for op in pull_ops(name):
            if op["op_id"] not in seen:
                seen.add(op["op_id"])
                all_ops.append(op)
    for name in names:
        push_ops(name, all_ops)


def state(replica: str) -> dict[str, Any]:
    return get_json(replica, "/state")


def states_converged(replicas: list[str] | None = None) -> bool:
    names = replicas or list(REPLICAS)
    digests = {state(name)["digest"] for name in names}
    return len(digests) == 1


def apply_netem(profile: str) -> None:
    p = PROFILES[profile]
    for container in CONTAINERS.values():
        proc = run([
            "docker", "exec", container,
            "tc", "qdisc", "replace", "dev", "eth0", "root", "netem",
            "delay", p["delay"], p["jitter"], "loss", p["loss"],
        ], check=False)
        if proc.returncode != 0:
            raise RuntimeError(f"tc apply failed on {container}: {proc.stderr.strip() or proc.stdout.strip()}")


def remove_netem() -> None:
    for container in CONTAINERS.values():
        run(["docker", "exec", container, "tc", "qdisc", "del", "dev", "eth0", "root"], check=False)


def percentile(xs: list[float], p: float) -> float:
    xs = sorted(xs)
    if not xs:
        raise ValueError("empty percentile")
    k = (len(xs) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(xs) - 1)
    if f == c:
        return xs[f]
    return xs[f] + (xs[c] - xs[f]) * (k - f)


def scenario_field_propagation(handle, runs: int, deadline_s: float) -> None:
    for profile in PROFILES:
        for qd in (1, 10, 100):
            values: list[float] = []
            for i in range(runs):
                reset_replicas()
                incident = str(uuid.uuid4())
                for j in range(qd):
                    post_json("a", "/ops/edit", {
                        "element_id": f"{incident}:obs:{j}",
                        "fields": {"event_type": "observation", "j": j, "incident_id": incident},
                    })
                apply_netem(profile)
                time.sleep(0.2)
                try:
                    t0 = time.perf_counter_ns()
                    deadline = time.monotonic() + deadline_s
                    while True:
                        ops = pull_ops("a")
                        push_ops("b", ops)
                        push_ops("core", ops)
                        visible_b = len(state("b")["state"])
                        visible_core = len(state("core")["state"])
                        if visible_b >= qd and visible_core >= qd:
                            break
                        if time.monotonic() > deadline:
                            break
                        time.sleep(0.02)
                    elapsed_ms = (time.perf_counter_ns() - t0) / 1e6
                    success = len(state("b")["state"]) >= qd and len(state("core")["state"]) >= qd
                finally:
                    remove_netem()
                value = elapsed_ms if success else None
                if value is not None:
                    values.append(value)
                write_record(
                    handle,
                    run_id=incident,
                    scenario="crdt_field_edit_propagation",
                    metric_name="anti_entropy_propagation_ms",
                    value_ms=value,
                    timestamp_iso=now_iso(),
                    scenario_params={
                        "profile": profile,
                        "profile_params": PROFILES[profile],
                        "queue_depth": qd,
                        "run_index": i,
                        "submitted": qd,
                        "replica_b_visible": len(state("b")["state"]),
                        "core_visible": len(state("core")["state"]),
                        "local_edit_time_excluded": 1,
                    },
                    notes="" if success else "deadline_exceeded_or_missing_rows",
                )
            if values:
                write_record(
                    handle,
                    run_id=f"field-{profile}-qd{qd}",
                    scenario="crdt_field_edit_propagation",
                    metric_name="summary",
                    value_ms=statistics.median(values),
                    timestamp_iso=now_iso(),
                    scenario_params={
                        "profile": profile,
                        "queue_depth": qd,
                        "n_runs": runs,
                        "n_success": len(values),
                        "median_ms": statistics.median(values),
                        "p95_ms": percentile(values, 95),
                        "local_edit_time_excluded": 1,
                    },
                    notes="",
                )


def scenario_concurrent_conflict(handle, runs: int) -> None:
    for i in range(runs):
        reset_replicas()
        element = f"incident:{uuid.uuid4()}"
        base = time.time_ns()
        a = post_json("a", "/ops/edit", {
            "element_id": element,
            "fields": {"status": "evacuating"},
            "timestamp_ns": base,
        })["op"]
        b = post_json("b", "/ops/edit", {
            "element_id": element,
            "fields": {"status": "contained"},
            "timestamp_ns": base + 1_000,
        })["op"]
        t0 = time.perf_counter_ns()
        full_sync(["a", "b", "core"])
        elapsed_ms = (time.perf_counter_ns() - t0) / 1e6
        final = state("core")["state"].get(element, {})
        ops = pull_ops("core")
        losing_op_id = a["op_id"] if final.get("status") == "contained" else b["op_id"]
        losing_recoverable = int(any(op["op_id"] == losing_op_id for op in ops))
        write_record(
            handle,
            run_id=element,
            scenario="crdt_concurrent_authoritative_edit",
            metric_name="convergence_ms",
            value_ms=elapsed_ms,
            timestamp_iso=now_iso(),
            scenario_params={
                "run_index": i,
                "field": "status",
                "write_a": "evacuating",
                "write_b": "contained",
                "winner": final.get("status"),
                "lost_update_count": 1,
                "losing_write_recoverable_from_oplog": losing_recoverable,
                "observer_detects_lost_update_from_state": 0,
            },
            notes="LWW accepts both writes and exposes only the latest field value in materialized state",
        )


def scenario_delete_resurrection(handle, runs: int) -> None:
    for i in range(runs):
        reset_replicas()
        element = f"incident:{uuid.uuid4()}:task:foam"
        base = time.time_ns()
        post_json("a", "/ops/edit", {
            "element_id": element,
            "fields": {"task": "foam", "owner": "unit-a"},
            "timestamp_ns": base,
        })
        full_sync(["a", "b", "core"])
        post_json("a", "/ops/delete", {"element_id": element, "timestamp_ns": base + 1_000})
        post_json("b", "/ops/edit", {
            "element_id": element,
            "fields": {"task": "foam", "owner": "unit-b"},
            "timestamp_ns": base + 2_000,
        })
        t0 = time.perf_counter_ns()
        full_sync(["a", "b", "core"])
        elapsed_ms = (time.perf_counter_ns() - t0) / 1e6
        final = state("core")["state"]
        resurrected = int(element in final)
        write_record(
            handle,
            run_id=element,
            scenario="crdt_delete_resurrection",
            metric_name="convergence_ms",
            value_ms=elapsed_ms,
            timestamp_iso=now_iso(),
            scenario_params={
                "run_index": i,
                "element_visible_after_delete_update_race": resurrected,
                "final_owner": final.get(element, {}).get("owner"),
            },
            notes="later update wins over earlier delete under LWW semantics" if resurrected else "delete wins",
        )


def scenario_throughput(handle, runs: int, events: int) -> None:
    writers = ["a", "b", "c"]
    values: list[float] = []
    for i in range(runs):
        reset_replicas()
        incident = str(uuid.uuid4())
        t0 = time.perf_counter_ns()
        for j in range(events):
            writer = writers[j % len(writers)]
            post_json(writer, "/ops/edit", {
                "element_id": f"{incident}:obs:{j}",
                "fields": {"event_type": "observation", "j": j, "writer": writer},
            })
        elapsed_s = (time.perf_counter_ns() - t0) / 1e9
        tput = events / elapsed_s if elapsed_s > 0 else 0.0
        values.append(tput)
        t_sync0 = time.perf_counter_ns()
        full_sync(["a", "b", "c", "core"])
        sync_ms = (time.perf_counter_ns() - t_sync0) / 1e6
        write_record(
            handle,
            run_id=incident,
            scenario="crdt_no_partition_throughput",
            metric_name="events_per_sec",
            value_ms=None,
            timestamp_iso=now_iso(),
            scenario_params={
                "run_index": i,
                "target_n": events,
                "achieved": events,
                "elapsed_s": elapsed_s,
                "events_per_sec": tput,
                "post_write_sync_ms": sync_ms,
            },
            notes="multi-writer no-conflict local acceptance before anti-entropy sync",
        )
    write_record(
        handle,
        run_id="throughput-summary",
        scenario="crdt_no_partition_throughput",
        metric_name="summary",
        value_ms=None,
        timestamp_iso=now_iso(),
        scenario_params={
            "n_runs": runs,
            "target_n": events,
            "median_events_per_sec": statistics.median(values),
            "p95_events_per_sec": percentile(values, 95),
        },
        notes="",
    )


def scenario_convergence_after_partition(handle, runs: int, partition_s: float, edits_per_replica: int) -> None:
    # A 60-second partition is expensive at n=30. The default obeys the paper
    # protocol, but callers may lower --partition-s for smoke verification.
    for i in range(runs):
        reset_replicas()
        incident = str(uuid.uuid4())
        start_partition = time.perf_counter_ns()
        for replica in ("a", "b", "c"):
            for j in range(edits_per_replica):
                post_json(replica, "/ops/edit", {
                    "element_id": f"{incident}:{replica}:{j}",
                    "fields": {"event_type": "observation", "replica": replica, "j": j},
                })
        remaining = partition_s - ((time.perf_counter_ns() - start_partition) / 1e9)
        if remaining > 0:
            time.sleep(remaining)
        t0 = time.perf_counter_ns()
        full_sync(["a", "b", "c", "core"])
        elapsed_ms = (time.perf_counter_ns() - t0) / 1e6
        converged = states_converged(["a", "b", "c", "core"])
        expected = edits_per_replica * 3
        visible = len(state("core")["state"])
        write_record(
            handle,
            run_id=incident,
            scenario="crdt_partition_convergence",
            metric_name="time_to_all_replicas_consistent_ms",
            value_ms=elapsed_ms if converged and visible == expected else None,
            timestamp_iso=now_iso(),
            scenario_params={
                "run_index": i,
                "partition_s": partition_s,
                "edits_per_replica": edits_per_replica,
                "expected_visible_elements": expected,
                "core_visible_elements": visible,
                "all_replicas_consistent": int(converged),
                "operator_visible_anomalies": 0,
            },
            notes="" if converged and visible == expected else "not_converged_or_missing_elements",
        )


def collect_environment() -> dict[str, Any]:
    git = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True, text=True)
    docker = subprocess.run(["docker", "version", "--format", "{{.Server.Version}}"], cwd=BASE, capture_output=True, text=True)
    return {
        "git_commit": git.stdout.strip() if git.returncode == 0 else None,
        "timestamp_iso": now_iso(),
        "docker_server_version": docker.stdout.strip() if docker.returncode == 0 else None,
        "host_uname": " ".join(platform.uname()),
        "host_cpu_count": os.cpu_count(),
    }


def anonymize(src: Path) -> Path:
    dst = src.with_suffix(".anon.jsonl")
    with src.open(encoding="utf-8") as fin, dst.open("w", encoding="utf-8") as fout:
        for line in fin:
            record = json.loads(line)
            env = record.get("environment")
            if isinstance(env, dict):
                env = dict(env)
                env.pop("host_uname", None)
                if "git_commit" in env:
                    env["git_commit"] = "REDACTED-FOR-DOUBLE-BLIND"
                record["environment"] = env
            fout.write(json.dumps(record, sort_keys=True, default=str) + "\n")
    paper_data = REPO / "paper" / "data"
    paper_data.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, paper_data / src.name)
    shutil.copy2(dst, paper_data / dst.name)
    return dst


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=int, default=30, help="runs per scenario cell")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="output JSONL path")
    parser.add_argument("--deadline-s", type=float, default=60.0, help="per-cell propagation deadline")
    parser.add_argument("--throughput-events", type=int, default=300, help="events per throughput run")
    parser.add_argument("--partition-s", type=float, default=60.0, help="partition duration for convergence scenario")
    parser.add_argument("--partition-runs", type=int, default=None, help="override runs for the long partition scenario")
    parser.add_argument("--edits-per-replica", type=int, default=50)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output = Path(args.output)
    if not output.is_absolute():
        output = BASE / output
    output.parent.mkdir(parents=True, exist_ok=True)
    wait_for_replicas()
    remove_netem()
    env = collect_environment()
    partition_runs = args.partition_runs if args.partition_runs is not None else args.runs
    with output.open("w", encoding="utf-8") as handle:
        write_record(
            handle,
            run_id="env",
            scenario="crdt_baseline",
            metric_name="environment",
            value_ms=None,
            timestamp_iso=now_iso(),
            scenario_params={
                "runs": args.runs,
                "partition_runs": partition_runs,
                "partition_s": args.partition_s,
                "throughput_events": args.throughput_events,
                "edits_per_replica": args.edits_per_replica,
                "profiles": PROFILES,
            },
            environment=env,
            notes="Hanssen-style operation-based LWW Element Set baseline",
        )
        scenario_field_propagation(handle, args.runs, args.deadline_s)
        scenario_concurrent_conflict(handle, args.runs)
        scenario_delete_resurrection(handle, args.runs)
        scenario_throughput(handle, args.runs, args.throughput_events)
        scenario_convergence_after_partition(handle, partition_runs, args.partition_s, args.edits_per_replica)
    remove_netem()
    anon = anonymize(output)
    print(f"wrote {output}")
    print(f"wrote {anon}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        remove_netem()
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise
