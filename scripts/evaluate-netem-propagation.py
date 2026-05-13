#!/usr/bin/env python3
"""Measure field-edit propagation under emulated mesh impairment.

Phase 5 evaluation. Reuses the responder-edge ops-api -> outbox -> command
syncd accept path measured in scripts/evaluate-pilot.py's
scenario_propagation, but applies a tc-netem qdisc on the responder
syncd container's eth0 before each cell so the responder->command
egress traffic experiences delay + jitter + loss.

Two link-condition profiles, informed by published mesh-network
measurements~\\cite{zimbelman2022mesh,kumbhar2015legacy}:
  * stressed:  delay 80 ms +/- 30 ms, 2% loss
  * degraded:  delay 200 ms +/- 80 ms, 8% loss

Two queue depths (1 and 10) per profile. --smoke restricts each cell
to 5 runs at queue depth 1 only (intended as the Phase 5 Day 1
sanity gate; full sweep is 2 * 2 * 20 = 80 records).

Prerequisites:
    ./scripts/dev-up.sh    # at minimum core + edge-cmd + edge-resp-1
    The edge-resp-1 syncd container must have CAP_NET_ADMIN
    (edge/docker-compose.yml grants it) and iproute2 installed
    (edge/syncd/Dockerfile installs it). Rebuild edge-resp-1 syncd
    image before running this script if the changes are not yet
    baked into the image.

Output:
    paper/data/eval_netem_propagation.jsonl   (un-anonymized source)
    Anonymize with paper/scripts/anonymize_data.py to produce the
    .anon.jsonl version referenced by the paper.
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
DEFAULT_ARTIFACT = ROOT / "paper" / "data" / "eval_netem_propagation.jsonl"

RESP_OPS = os.environ.get("RESP_OPS", "http://127.0.0.1:18101")
CMD_PG_CONTAINER = os.environ.get("CMD_PG_CONTAINER", "edge-cmd-postgres-1")
RESP_SYNCD_CONTAINER = os.environ.get("RESP_SYNCD_CONTAINER", "edge-resp-1-syncd-1")
CMD_SYNCD_CONTAINER = os.environ.get("CMD_SYNCD_CONTAINER", "edge-cmd-syncd-1")
# tc qdisc on eth0 only impairs egress. To approximate a symmetric mesh
# link, apply the same netem rule on both responder and command syncd
# containers so each direction of the responder<->command traffic
# experiences the configured delay and loss.
NETEM_CONTAINERS = (RESP_SYNCD_CONTAINER, CMD_SYNCD_CONTAINER)
EDGE_DB = "rescue_ois_edge"

PROFILES: dict[str, dict[str, str]] = {
    "stressed": {
        "delay": "80ms",
        "jitter": "30ms",
        "loss": "2%",
    },
    "degraded": {
        "delay": "200ms",
        "jitter": "80ms",
        "loss": "8%",
    },
}


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def run(args: list[str], *, check: bool = True, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=ROOT,
        env=env,
        check=check,
        capture_output=True,
        text=True,
    )


def docker_exec(container: str, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return run(["docker", "exec", container, *args], check=check)


def psql(container: str, db: str, sql: str, *, check: bool = True) -> str:
    proc = docker_exec(container, "psql", "-U", "postgres", db, "-tAc", sql, check=check)
    return proc.stdout.strip()


def apply_netem(profile_name: str) -> None:
    """Install a tc-netem qdisc on both syncd containers' eth0.

    Uses `tc qdisc replace` so repeated calls are idempotent. Both
    containers get the same rule to approximate symmetric mesh
    impairment on the responder<->command path.
    """
    p = PROFILES[profile_name]
    for container in NETEM_CONTAINERS:
        proc = docker_exec(
            container,
            "tc", "qdisc", "replace", "dev", "eth0", "root",
            "netem",
            "delay", p["delay"], p["jitter"],
            "loss", p["loss"],
            check=False,
        )
        if proc.returncode != 0:
            raise RuntimeError(
                f"apply_netem({profile_name}) on {container} failed: "
                f"rc={proc.returncode} "
                f"stderr={proc.stderr.strip() or proc.stdout.strip()}"
            )


def remove_netem() -> None:
    """Remove any netem qdisc from both syncd containers' eth0."""
    for container in NETEM_CONTAINERS:
        docker_exec(
            container,
            "tc", "qdisc", "del", "dev", "eth0", "root",
            check=False,
        )


def reset_eval_tables() -> None:
    psql(
        CMD_PG_CONTAINER,
        EDGE_DB,
        "TRUNCATE incident.journal, incident.state CASCADE; DELETE FROM sync.state;",
    )
    psql(
        "edge-resp-1-postgres-1",
        EDGE_DB,
        "TRUNCATE outbox.device_outbox CASCADE;",
    )


def http_post_json(url: str, body: dict[str, Any], timeout_s: float = 10.0) -> int:
    data = json.dumps(body).encode("utf-8")
    req = Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(req, timeout=timeout_s) as resp:
            return resp.status
    except HTTPError as exc:
        return exc.code


def journal_count(incident_id: str) -> int:
    raw = psql(
        CMD_PG_CONTAINER,
        EDGE_DB,
        f"SELECT count(*) FROM incident.journal WHERE incident_id = '{incident_id}'",
    )
    return int(raw or "0")


def measure_cell(profile_name: str, queue_depth: int, run_index: int, deadline_s: float = 90.0) -> dict[str, Any]:
    reset_eval_tables()
    incident_id = str(uuid.uuid4())
    submit_t0 = time.perf_counter_ns()
    submitted = 0
    for j in range(queue_depth):
        body = {
            "client_event_id": str(uuid.uuid4()),
            "incident_id": incident_id,
            "event_type": "observation",
            "payload": {"j": j, "netem_profile": profile_name},
            "device_id": "tab-netem-eval",
            "user_id": "u",
            "occurred_at": now_iso(),
        }
        status = http_post_json(f"{RESP_OPS}/api/events", body, timeout_s=10.0)
        if status == 201 or status == 200:
            submitted += 1
    deadline_ns = time.perf_counter_ns() + int(deadline_s * 1e9)
    while time.perf_counter_ns() < deadline_ns:
        n = journal_count(incident_id)
        if n >= queue_depth:
            break
        time.sleep(0.05)
    journal_done_t = time.perf_counter_ns()
    n_final = journal_count(incident_id)
    success = n_final >= queue_depth
    value_ms = (journal_done_t - submit_t0) / 1e6 if success else None
    return {
        "profile": profile_name,
        "profile_params": PROFILES[profile_name],
        "queue_depth": queue_depth,
        "run_index": run_index,
        "incident_id": incident_id,
        "submitted": submitted,
        "journal_count": n_final,
        "value_ms": value_ms,
        "success": success,
    }


def collect_environment() -> dict[str, Any]:
    proc_docker = run(["docker", "version", "--format", "{{.Server.Version}}"], check=False)
    proc_compose = run(["docker", "compose", "version", "--short"], check=False)
    proc_git = run(["git", "rev-parse", "HEAD"], check=False)
    return {
        "git_commit": proc_git.stdout.strip() if proc_git.returncode == 0 else None,
        "timestamp_iso": now_iso(),
        "docker_server_version": proc_docker.stdout.strip() or None,
        "docker_compose_version": proc_compose.stdout.strip() or None,
        "host_uname": " ".join(platform.uname()),
        "host_cpu_count": os.cpu_count(),
    }


def write_record(handle, **fields: Any) -> None:
    handle.write(json.dumps(fields, sort_keys=True, default=str) + "\n")
    handle.flush()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--n",
        type=int,
        default=20,
        help="number of runs per (profile, queue_depth) cell (default 20, full sweep)",
    )
    parser.add_argument(
        "--queue-depths",
        type=str,
        default="1,10",
        help="comma-separated queue depths",
    )
    parser.add_argument(
        "--profiles",
        type=str,
        default="stressed,degraded",
        help="comma-separated profile names from PROFILES",
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Day-1 sanity gate: 5 runs per profile at queue depth 1 only",
    )
    parser.add_argument(
        "--artifact",
        default=str(DEFAULT_ARTIFACT),
        help="output JSONL path",
    )
    parser.add_argument(
        "--deadline-s",
        type=float,
        default=90.0,
        help="max seconds to wait for a cell to complete",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.smoke:
        args.n = 5
        args.queue_depths = "1"
    queue_depths = [int(x) for x in args.queue_depths.split(",") if x.strip()]
    profile_names = [p.strip() for p in args.profiles.split(",") if p.strip()]
    for p in profile_names:
        if p not in PROFILES:
            raise SystemExit(f"unknown profile: {p}; valid: {list(PROFILES)}")

    artifact = Path(args.artifact)
    artifact.parent.mkdir(parents=True, exist_ok=True)
    env_meta = collect_environment()

    summaries: list[dict[str, Any]] = []
    with artifact.open("w", encoding="utf-8") as handle:
        write_record(
            handle,
            run_id="env",
            scenario="netem_propagation",
            metric_name="environment",
            value_ms=None,
            timestamp_iso=now_iso(),
            scenario_params={
                "n_per_cell": args.n,
                "queue_depths": queue_depths,
                "profiles": profile_names,
                "smoke": args.smoke,
                "deadline_s": args.deadline_s,
            },
            environment=env_meta,
            notes="",
        )
        try:
            for profile in profile_names:
                apply_netem(profile)
                # Allow the rule to take effect before the first request.
                time.sleep(0.5)
                try:
                    for qd in queue_depths:
                        cell_values: list[float] = []
                        for i in range(args.n):
                            rec = measure_cell(profile, qd, i, deadline_s=args.deadline_s)
                            write_record(
                                handle,
                                run_id=rec["incident_id"],
                                scenario="netem_propagation",
                                metric_name="end_to_end_propagation_ms",
                                value_ms=rec["value_ms"],
                                timestamp_iso=now_iso(),
                                scenario_params={
                                    "profile": profile,
                                    "profile_params": PROFILES[profile],
                                    "queue_depth": qd,
                                    "run_index": i,
                                    "journal_count": rec["journal_count"],
                                    "submitted": rec["submitted"],
                                },
                                notes="" if rec["success"] else "deadline_exceeded_or_missing_rows",
                            )
                            if rec["value_ms"] is not None:
                                cell_values.append(rec["value_ms"])
                            print(
                                f"  profile={profile} qd={qd} i={i} "
                                f"value_ms={rec['value_ms']}"
                            )
                        if cell_values:
                            med = statistics.median(cell_values)
                            p95 = (
                                statistics.quantiles(cell_values, n=20, method="inclusive")[18]
                                if len(cell_values) >= 20
                                else None
                            )
                        else:
                            med, p95 = None, None
                        summary = {
                            "profile": profile,
                            "queue_depth": qd,
                            "n_runs": args.n,
                            "n_success": len(cell_values),
                            "median_ms": med,
                            "p95_ms": p95,
                        }
                        summaries.append(summary)
                        write_record(
                            handle,
                            run_id=f"{profile}-qd{qd}",
                            scenario="netem_propagation",
                            metric_name="summary",
                            value_ms=med,
                            timestamp_iso=now_iso(),
                            scenario_params=summary,
                            notes="",
                        )
                finally:
                    remove_netem()
        finally:
            remove_netem()

    print(json.dumps({"summaries": summaries}, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        try:
            subprocess.run(
                ["docker", "exec", RESP_SYNCD_CONTAINER, "tc", "qdisc", "del", "dev", "eth0", "root"],
                check=False, capture_output=True, text=True,
            )
        except Exception:
            pass
        for c in NETEM_CONTAINERS:
            try:
                subprocess.run(
                    ["docker", "exec", c, "tc", "qdisc", "del", "dev", "eth0", "root"],
                    check=False, capture_output=True, text=True,
                )
            except Exception:
                pass
        raise
