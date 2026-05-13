#!/usr/bin/env python3
"""Measure direct command syncd accept-path commits during responder isolation.

This is a focused preflight harness for the bounded paper claim that
command-originated writes submitted directly to the command syncd
/accept/event-batch endpoint can commit while a responder syncd process is
isolated, provided the command node and its local storage remain available.

The script starts the normal dev compose emulation when needed, applies the
existing migrations if the fresh databases do not have the required tables,
resets evaluation tables, partitions responder syncd using the existing mesh
partition helper, posts command-originated writes directly to command syncd's
accept endpoint, and records per-attempt plus summary JSONL records.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
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


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARTIFACT = ROOT / "paper" / "data" / "eval_command_local_partition.jsonl"
NETWORK_NAME = "rescue-ois-net"
CMD_SYNCD = os.environ.get("CMD_SYNCD", "http://127.0.0.1:18081")


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def run(
    args: list[str],
    *,
    cwd: Path = ROOT,
    env: dict[str, str] | None = None,
    check: bool = True,
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=cwd,
        env=env,
        input=input_text,
        check=check,
        capture_output=True,
        text=True,
    )


def docker_exec(container: str, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return run(["docker", "exec", container, *args], check=check)


def psql(container: str, db: str, sql: str, *, check: bool = True) -> str:
    proc = docker_exec(container, "psql", "-U", "postgres", db, "-tAc", sql, check=check)
    return proc.stdout.strip()


def write_record(handle, **fields: Any) -> None:
    handle.write(json.dumps(fields, sort_keys=True, default=str) + "\n")
    handle.flush()


def compose_projects() -> set[str]:
    proc = run(["docker", "compose", "ls", "--format", "json"], check=False)
    if proc.returncode != 0 or not proc.stdout.strip():
        return set()
    return {item["Name"] for item in json.loads(proc.stdout)}


def docker_container_names() -> list[str]:
    proc = run(["docker", "ps", "--format", "{{.Names}}"])
    return [line for line in proc.stdout.splitlines() if line]


def start_stack() -> None:
    projects = compose_projects()
    if {"core", "edge-cmd", "edge-resp-1"}.issubset(projects):
        return
    env = {**os.environ, "RESPONDERS": "1"}
    proc = run(["./scripts/dev-up.sh"], env=env, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"dev-up failed: {proc.stderr.strip() or proc.stdout.strip()}")


def wait_for_postgres(container: str, db: str, timeout_s: float = 60.0) -> None:
    deadline = time.monotonic() + timeout_s
    last = ""
    while time.monotonic() < deadline:
        proc = docker_exec(container, "psql", "-U", "postgres", db, "-tAc", "SELECT 1", check=False)
        if proc.returncode == 0 and proc.stdout.strip() == "1":
            return
        last = proc.stderr.strip() or proc.stdout.strip()
        time.sleep(1.0)
    raise TimeoutError(f"{container}/{db} did not become ready: {last}")


def wait_for_http(url: str, timeout_s: float = 90.0) -> None:
    deadline = time.monotonic() + timeout_s
    last = ""
    while time.monotonic() < deadline:
        try:
            with urlopen(url, timeout=3.0) as resp:
                if resp.status == 200:
                    return
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            last = str(exc)
        time.sleep(1.0)
    raise TimeoutError(f"{url} did not become healthy: {last}")


def required_edge_schema_present(container: str) -> bool:
    sql = """
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = 'incident'
              AND table_name = 'journal'
              AND column_name = 'client_event_id'
        )
    """
    return psql(container, "rescue_ois_edge", sql, check=False) == "t"


def required_core_schema_present() -> bool:
    sql = """
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = 'master'
              AND table_name = 'incident_events'
              AND column_name = 'client_event_id'
        )
    """
    return psql("core-postgres-1", "rescue_ois", sql, check=False) == "t"


def apply_migrations_if_needed() -> None:
    wait_for_postgres("core-postgres-1", "rescue_ois")
    edge_postgres = sorted(
        name for name in docker_container_names() if name.startswith("edge-") and name.endswith("-postgres-1")
    )
    for container in edge_postgres:
        wait_for_postgres(container, "rescue_ois_edge")

    if not required_core_schema_present():
        proc = run(["./scripts/run-migrations.sh", "core"], check=False)
        if proc.returncode != 0:
            raise RuntimeError(f"core migrations failed: {proc.stderr.strip() or proc.stdout.strip()}")

    if any(not required_edge_schema_present(container) for container in edge_postgres):
        proc = run(["./scripts/run-migrations.sh", "edge"], check=False)
        if proc.returncode != 0:
            raise RuntimeError(f"edge migrations failed: {proc.stderr.strip() or proc.stdout.strip()}")


def reset_eval_tables() -> None:
    psql(
        "edge-cmd-postgres-1",
        "rescue_ois_edge",
        "TRUNCATE incident.journal, incident.state, outbox.device_outbox CASCADE; DELETE FROM sync.state;",
    )
    psql(
        "core-postgres-1",
        "rescue_ois",
        "TRUNCATE master.incident_events, master.incidents CASCADE;",
    )
    for container in docker_container_names():
        if container.startswith("edge-resp-") and container.endswith("-postgres-1"):
            psql(container, "rescue_ois_edge", "TRUNCATE outbox.device_outbox CASCADE;")


def get_git_commit() -> str | None:
    proc = run(["git", "rev-parse", "HEAD"], check=False)
    return proc.stdout.strip() if proc.returncode == 0 else None


def collect_environment() -> dict[str, Any]:
    docker_version = run(["docker", "version", "--format", "{{.Server.Version}}"], check=False)
    compose_version = run(["docker", "compose", "version", "--short"], check=False)
    mem_total_kb = None
    cpu_model = None
    try:
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            if line.startswith("MemTotal:"):
                mem_total_kb = int(line.split()[1])
                break
    except OSError:
        pass
    try:
        for line in Path("/proc/cpuinfo").read_text(encoding="utf-8").splitlines():
            if line.startswith("model name"):
                cpu_model = line.split(":", 1)[1].strip()
                break
    except OSError:
        pass
    return {
        "git_commit": get_git_commit(),
        "timestamp_iso": now_iso(),
        "docker_server_version": docker_version.stdout.strip() or None,
        "docker_compose_version": compose_version.stdout.strip() or None,
        "host_uname": " ".join(platform.uname()),
        "host_cpu_model": cpu_model,
        "host_cpu_count": os.cpu_count(),
        "host_mem_total_kb": mem_total_kb,
    }


def http_post_json(url: str, body: dict[str, Any], timeout_s: float = 10.0) -> tuple[int, dict[str, Any], str]:
    data = json.dumps(body).encode("utf-8")
    req = Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(req, timeout=timeout_s) as resp:
            raw = resp.read().decode("utf-8")
            parsed = json.loads(raw) if raw else {}
            return resp.status, parsed, raw
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        parsed = json.loads(raw) if raw.startswith("{") else {}
        return exc.code, parsed, raw


def network_aliases(container: str) -> list[str]:
    proc = run(["docker", "inspect", container], check=True)
    info = json.loads(proc.stdout)[0]
    network = info["NetworkSettings"]["Networks"].get(NETWORK_NAME)
    if not network:
        return []
    return network.get("Aliases") or []


def container_connected(container: str) -> bool:
    proc = run(["docker", "inspect", container], check=False)
    if proc.returncode != 0:
        return False
    info = json.loads(proc.stdout)[0]
    return NETWORK_NAME in info["NetworkSettings"]["Networks"]


def reconnect_if_needed(container: str, aliases: list[str]) -> None:
    if container_connected(container):
        return
    args = ["docker", "network", "connect"]
    for alias in aliases:
        args.extend(["--alias", alias])
    args.extend([NETWORK_NAME, container])
    run(args, check=True)


def fetch_journal(incident_id: str) -> list[dict[str, Any]]:
    rows_json = psql(
        "edge-cmd-postgres-1",
        "rescue_ois_edge",
        f"""
        SELECT COALESCE(json_agg(row_to_json(t) ORDER BY event_seq), '[]'::json)
        FROM (
            SELECT event_seq, client_event_id::text AS client_event_id,
                   event_type, device_id, user_id, payload
            FROM incident.journal
            WHERE incident_id = '{incident_id}'
            ORDER BY event_seq
        ) AS t
        """,
    )
    return json.loads(rows_json or "[]")


def duplicate_sequence_count(incident_id: str) -> int:
    value = psql(
        "edge-cmd-postgres-1",
        "rescue_ois_edge",
        f"""
        SELECT COALESCE(SUM(c - 1), 0)
        FROM (
            SELECT event_seq, COUNT(*) AS c
            FROM incident.journal
            WHERE incident_id = '{incident_id}'
            GROUP BY event_seq
            HAVING COUNT(*) > 1
        ) AS d
        """,
    )
    return int(value or "0")


def core_count(incident_id: str) -> int:
    value = psql(
        "core-postgres-1",
        "rescue_ois",
        f"SELECT count(*) FROM master.incident_events WHERE incident_id = '{incident_id}'",
        check=False,
    )
    return int(value or "0")


def run_experiment(args: argparse.Namespace) -> dict[str, Any]:
    if not args.assume_running:
        start_stack()
    apply_migrations_if_needed()
    wait_for_http(f"{CMD_SYNCD}/health")
    reset_eval_tables()

    artifact = Path(args.artifact)
    artifact.parent.mkdir(parents=True, exist_ok=True)

    run_id = str(uuid.uuid4())
    incident_id = str(uuid.uuid4())
    env_meta = collect_environment()
    partition_container = f"edge-resp-{args.responder_index}-syncd-1"
    aliases = network_aliases(partition_container)
    attempts: list[dict[str, Any]] = []
    partition_proc: subprocess.Popen[str] | None = None

    with artifact.open("w", encoding="utf-8") as handle:
        write_record(
            handle,
            run_id=run_id,
            scenario="command_accept_path_during_responder_syncd_isolation",
            metric_name="environment",
            value_ms=None,
            timestamp_iso=now_iso(),
            scenario_params={
                "attempts": args.attempts,
                "partition_s": args.partition_s,
                "partition_target": "mesh",
                "partition_container": partition_container,
                "command_endpoint": CMD_SYNCD,
            },
            environment=env_meta,
            notes="",
        )

        try:
            partition_env = {
                **os.environ,
                "RESPONDER_INDEX": str(args.responder_index),
                "RESCUE_OIS_RUN_ID": run_id,
                "RESCUE_OIS_PARTITION_AUDIT_PATH": str(artifact.with_suffix(".audit.jsonl")),
            }
            partition_proc = subprocess.Popen(
                ["./scripts/inject-partition.sh", "mesh", str(args.partition_s)],
                cwd=ROOT,
                env=partition_env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            deadline = time.monotonic() + 15.0
            while time.monotonic() < deadline and container_connected(partition_container):
                if partition_proc.poll() is not None:
                    stdout, stderr = partition_proc.communicate()
                    raise RuntimeError(
                        f"partition helper exited early: {stderr.strip() or stdout.strip()}"
                    )
                time.sleep(0.1)
            if container_connected(partition_container):
                raise TimeoutError(f"{partition_container} did not disconnect from {NETWORK_NAME}")

            for index in range(args.attempts):
                client_event_id = str(uuid.uuid4())
                created_at = now_iso()
                body = {
                    "events": [
                        {
                            "id": str(uuid.uuid4()),
                            "incident_id": incident_id,
                            "client_event_id": client_event_id,
                            "device_id": "command-local-preflight",
                            "user_id": "command",
                            "event_type": "command_note",
                            "payload": {"attempt_index": index, "origin": "command-local"},
                            "created_at": created_at,
                        }
                    ]
                }
                t0 = time.perf_counter_ns()
                failure_reason = None
                status_code = None
                response_json: dict[str, Any] = {}
                try:
                    status_code, response_json, response_text = http_post_json(
                        f"{CMD_SYNCD}/accept/event-batch",
                        body,
                        timeout_s=args.write_timeout_s,
                    )
                    if status_code != 200:
                        failure_reason = f"http_status={status_code} body={response_text}"
                    elif int(response_json.get("accepted", 0)) != 1:
                        failure_reason = f"accepted={response_json.get('accepted')}"
                except (URLError, TimeoutError, OSError) as exc:
                    failure_reason = f"{type(exc).__name__}: {exc}"
                t1 = time.perf_counter_ns()
                latency_ms = (t1 - t0) / 1e6
                success = failure_reason is None
                attempt = {
                    "attempt_index": index,
                    "client_event_id": client_event_id,
                    "success": success,
                    "failure_reason": failure_reason,
                    "status_code": status_code,
                    "response": response_json,
                    "latency_ms": latency_ms,
                }
                attempts.append(attempt)
                write_record(
                    handle,
                    run_id=run_id,
                    scenario="command_accept_path_during_responder_syncd_isolation",
                    metric_name="command_local_commit_latency_ms",
                    value_ms=latency_ms if success else None,
                    timestamp_iso=now_iso(),
                    scenario_params={
                        "attempt_index": index,
                        "incident_id": incident_id,
                        "client_event_id": client_event_id,
                    },
                    notes="" if success else failure_reason,
                    status_code=status_code,
                    response=response_json,
                )

            journal_before = fetch_journal(incident_id)
            partition_stdout, partition_stderr = partition_proc.communicate(timeout=args.partition_s + 30)
            if partition_proc.returncode != 0:
                raise RuntimeError(
                    f"partition helper failed: {partition_stderr.strip() or partition_stdout.strip()}"
                )
            wait_deadline = time.monotonic() + args.recovery_observe_s
            while time.monotonic() < wait_deadline:
                time.sleep(0.1)
            journal_after = fetch_journal(incident_id)
            core_events_after = core_count(incident_id)

            successful = [a for a in attempts if a["success"]]
            failed = [a for a in attempts if not a["success"]]
            latencies = [a["latency_ms"] for a in successful]
            seqs = [int(row["event_seq"]) for row in journal_after]
            expected = list(range(1, len(seqs) + 1))
            continuous = seqs == expected and len(seqs) == len(successful)
            duplicate_count = duplicate_sequence_count(incident_id)
            recovery_changed = journal_before != journal_after
            p95 = None
            if len(latencies) >= 20:
                p95 = statistics.quantiles(latencies, n=20, method="inclusive")[18]

            summary = {
                "implemented_path": "direct command syncd /accept/event-batch",
                "attempted_writes": args.attempts,
                "successful_commits": len(journal_after),
                "failed_writes": len(failed),
                "failure_reasons": [a["failure_reason"] for a in failed],
                "median_latency_ms": statistics.median(latencies) if latencies else None,
                "p95_latency_ms": p95,
                "sequence_numbers": seqs,
                "sequence_continuous": continuous,
                "duplicate_sequence_count": duplicate_count,
                "recovery_changed_journal_state": recovery_changed,
                "journal_before_recovery": journal_before,
                "journal_after_recovery": journal_after,
                "core_events_after_recovery_observation": core_events_after,
                "partition_recovered": container_connected(partition_container),
                "partition_stdout": partition_stdout.strip(),
                "partition_stderr": partition_stderr.strip(),
                "run_id": run_id,
                "incident_id": incident_id,
                "environment": env_meta,
                "artifact_path": str(artifact),
                "audit_artifact_path": str(artifact.with_suffix(".audit.jsonl")),
            }
            write_record(
                handle,
                run_id=run_id,
                scenario="command_accept_path_during_responder_syncd_isolation",
                metric_name="summary",
                value_ms=None,
                timestamp_iso=now_iso(),
                scenario_params=summary,
                notes="",
            )
            return summary
        finally:
            reconnect_if_needed(partition_container, aliases)
            if partition_proc is not None and partition_proc.poll() is None:
                try:
                    partition_proc.wait(timeout=args.partition_s + 30)
                except subprocess.TimeoutExpired:
                    partition_proc.kill()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attempts", type=int, default=20)
    parser.add_argument("--partition-s", type=int, default=10)
    parser.add_argument("--recovery-observe-s", type=float, default=3.0)
    parser.add_argument("--write-timeout-s", type=float, default=5.0)
    parser.add_argument("--responder-index", type=int, default=1)
    parser.add_argument("--assume-running", action="store_true")
    parser.add_argument("--artifact", default=str(DEFAULT_ARTIFACT))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.attempts < 1:
        raise SystemExit("--attempts must be >= 1")
    summary = run_experiment(args)
    print(json.dumps(summary, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise
