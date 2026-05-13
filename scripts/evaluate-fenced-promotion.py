#!/usr/bin/env python3
"""Measure service-level command-epoch fencing on the command edge.

Modeled on scripts/evaluate-command-local-partition.py, but focused on the
Phase 4.2 enforcement (epoch validation at the /accept/event-batch endpoint
and per-event command_epoch stamping in incident.journal).

Each run executes three phases against a freshly-reset command edge:

  A. epoch=1 traffic at current epoch -> expected to be accepted.
  B. a new epoch row is installed and syncd is restarted so the cache
     advances to epoch=2; epoch=1 traffic (stale) is replayed -> expected
     to be rejected with HTTP 409.
  C. epoch=2 traffic at the new current epoch -> expected to be accepted.

The invariants checked per run match the paper claim:

  * duplicate_seqs_across_epochs == 0 -- no event_seq value appears with
    both command_epoch=1 and command_epoch=2 rows in the journal.
  * stale_epoch_rejections > 0 -- the stale-epoch path must be exercised.
  * new_epoch_commits > 0 -- the post-promotion epoch must be writable.
  * Within each epoch the surviving event_seq values are contiguous.

This experiment intentionally runs single-edge. The architectural reasons
are documented in paper/sections (Phase 4 limitations) and on the plan: each
edge has its own Postgres, so a cross-edge promotion exercises a different
shape of the property. The single-edge variant tests the journal-poisoning
invariant the paper actually claims: stale-epoch traffic cannot land in the
journal even when it is replayed against the current command.
"""

from __future__ import annotations

import argparse
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
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARTIFACT = ROOT / "paper" / "data" / "eval_fenced_promotion.jsonl"
CMD_SYNCD = os.environ.get("CMD_SYNCD", "http://127.0.0.1:18081")
CMD_PG_CONTAINER = os.environ.get("CMD_PG_CONTAINER", "edge-cmd-postgres-1")
CMD_SYNCD_CONTAINER = os.environ.get("CMD_SYNCD_CONTAINER", "edge-cmd-syncd-1")
EDGE_DB = "rescue_ois_edge"


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


def wait_for_http(url: str, timeout_s: float = 60.0) -> None:
    deadline = time.monotonic() + timeout_s
    last = ""
    while time.monotonic() < deadline:
        try:
            with urlopen(url, timeout=3.0) as resp:
                if resp.status == 200:
                    return
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            last = str(exc)
        time.sleep(0.5)
    raise TimeoutError(f"{url} did not become healthy: {last}")


def reset_eval_tables() -> None:
    psql(
        CMD_PG_CONTAINER,
        EDGE_DB,
        """
        TRUNCATE incident.journal, incident.state, outbox.device_outbox CASCADE;
        DELETE FROM sync.state;
        DELETE FROM incident.command_epoch;
        INSERT INTO incident.command_epoch (epoch_id, started_by, node_id)
        VALUES (1, 'bootstrap', 'edge-cmd');
        SELECT setval(pg_get_serial_sequence('incident.command_epoch', 'epoch_id'), 1, true);
        """,
    )


def install_new_epoch(operator: str, node_id: str) -> int:
    """Insert the next command_epoch row, restart syncd to refresh the cache."""
    new_epoch = int(
        psql(
            CMD_PG_CONTAINER,
            EDGE_DB,
            f"""
            INSERT INTO incident.command_epoch (started_by, node_id)
            VALUES ('{operator}', '{node_id}')
            RETURNING epoch_id
            """,
        )
    )
    # Restart syncd so accept.init_epoch_cache() picks the new value up.
    run(["docker", "restart", CMD_SYNCD_CONTAINER])
    wait_for_http(f"{CMD_SYNCD}/health", timeout_s=30.0)
    return new_epoch


def http_post_event(
    incident_id: str,
    epoch_header: int,
    attempt_index: int,
    timeout_s: float = 5.0,
) -> tuple[int, dict[str, Any], str, str, float]:
    """POST one event with the given X-Command-Epoch and return result + timing."""
    client_event_id = str(uuid.uuid4())
    body = {
        "events": [
            {
                "id": str(uuid.uuid4()),
                "incident_id": incident_id,
                "client_event_id": client_event_id,
                "device_id": "fenced-promotion-driver",
                "user_id": "operator",
                "event_type": "command_note",
                "payload": {"attempt_index": attempt_index, "phase_epoch": epoch_header},
                "created_at": now_iso(),
            }
        ]
    }
    data = json.dumps(body).encode("utf-8")
    req = Request(
        f"{CMD_SYNCD}/accept/event-batch",
        data=data,
        headers={
            "Content-Type": "application/json",
            "X-Command-Epoch": str(epoch_header),
        },
        method="POST",
    )
    t0 = time.perf_counter_ns()
    try:
        with urlopen(req, timeout=timeout_s) as resp:
            raw = resp.read().decode("utf-8")
            parsed = json.loads(raw) if raw else {}
            status = resp.status
    except HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        parsed = json.loads(raw) if raw.startswith("{") else {}
        status = exc.code
    t1 = time.perf_counter_ns()
    latency_ms = (t1 - t0) / 1e6
    return status, parsed, raw, client_event_id, latency_ms


def fetch_journal(incident_id: str) -> list[dict[str, Any]]:
    rows_json = psql(
        CMD_PG_CONTAINER,
        EDGE_DB,
        f"""
        SELECT COALESCE(json_agg(row_to_json(t) ORDER BY event_seq), '[]'::json)
        FROM (
            SELECT event_seq, command_epoch, client_event_id::text AS client_event_id
            FROM incident.journal
            WHERE incident_id = '{incident_id}'
            ORDER BY event_seq
        ) AS t
        """,
    )
    return json.loads(rows_json or "[]")


def get_git_commit() -> str | None:
    proc = run(["git", "rev-parse", "HEAD"], check=False)
    return proc.stdout.strip() if proc.returncode == 0 else None


def collect_environment() -> dict[str, Any]:
    docker_version = run(["docker", "version", "--format", "{{.Server.Version}}"], check=False)
    compose_version = run(["docker", "compose", "version", "--short"], check=False)
    return {
        "git_commit": get_git_commit(),
        "timestamp_iso": now_iso(),
        "docker_server_version": docker_version.stdout.strip() or None,
        "docker_compose_version": compose_version.stdout.strip() or None,
        "host_uname": " ".join(platform.uname()),
        "host_cpu_model": None,
        "host_cpu_count": os.cpu_count(),
        "host_mem_total_kb": None,
    }


def run_one(run_index: int, args: argparse.Namespace, handle, env_meta: dict[str, Any]) -> dict[str, Any]:
    reset_eval_tables()
    # Confirm baseline epoch is 1.
    baseline_epoch = int(psql(CMD_PG_CONTAINER, EDGE_DB, "SELECT epoch_id FROM incident.current_epoch"))
    # Restart syncd so its cache reflects this clean baseline.
    run(["docker", "restart", CMD_SYNCD_CONTAINER])
    wait_for_http(f"{CMD_SYNCD}/health", timeout_s=30.0)

    run_id = str(uuid.uuid4())
    incident_id = str(uuid.uuid4())
    per_phase: dict[str, list[dict[str, Any]]] = {"A_pre": [], "B_stale": [], "C_post": []}

    def record_attempt(phase: str, idx: int, epoch_header: int) -> dict[str, Any]:
        status, parsed, _raw, cid, latency_ms = http_post_event(
            incident_id, epoch_header, idx, timeout_s=args.write_timeout_s
        )
        ok = status == 200
        rec = {
            "phase": phase,
            "attempt_index": idx,
            "epoch_header": epoch_header,
            "status_code": status,
            "accepted": int(parsed.get("accepted", 0)) if ok else 0,
            "client_event_id": cid,
            "current_epoch_in_response": (parsed.get("current_epoch") if ok else None)
            or (parsed.get("detail", {}).get("current_epoch") if isinstance(parsed.get("detail"), dict) else None),
            "rejection_reason": (parsed.get("detail", {}).get("reason") if isinstance(parsed.get("detail"), dict) else None),
            "latency_ms": latency_ms,
        }
        write_record(
            handle,
            run_id=run_id,
            scenario="fenced_promotion_stale_rejection",
            metric_name="attempt",
            value_ms=latency_ms,
            timestamp_iso=now_iso(),
            scenario_params={**rec, "incident_id": incident_id, "run_index": run_index},
            notes="",
        )
        per_phase[phase].append(rec)
        return rec

    # Phase A: epoch=1 at current epoch -> accept.
    for i in range(args.writes_per_phase):
        record_attempt("A_pre", i, baseline_epoch)

    # Install new epoch and refresh syncd cache.
    new_epoch = install_new_epoch(operator=f"run-{run_index}-operator", node_id="edge-resp-2")

    # Phase B: epoch=1 (stale) -> reject 409.
    for i in range(args.writes_per_phase):
        record_attempt("B_stale", i, baseline_epoch)

    # Phase C: epoch=new_epoch (current) -> accept.
    for i in range(args.writes_per_phase):
        record_attempt("C_post", i, new_epoch)

    # Compute metrics.
    journal = fetch_journal(incident_id)
    epoch1_rows = [r for r in journal if int(r["command_epoch"]) == baseline_epoch]
    epoch2_rows = [r for r in journal if int(r["command_epoch"]) == new_epoch]
    other_rows = [r for r in journal if int(r["command_epoch"]) not in (baseline_epoch, new_epoch)]

    epoch1_seqs = sorted(int(r["event_seq"]) for r in epoch1_rows)
    epoch2_seqs = sorted(int(r["event_seq"]) for r in epoch2_rows)
    contiguity_epoch1 = epoch1_seqs == list(range(1, len(epoch1_seqs) + 1)) if epoch1_seqs else True
    contiguity_epoch2 = (
        bool(epoch2_seqs)
        and epoch2_seqs[0] == (epoch1_seqs[-1] + 1 if epoch1_seqs else 1)
        and epoch2_seqs == list(range(epoch2_seqs[0], epoch2_seqs[0] + len(epoch2_seqs)))
    )
    duplicate_seqs_across_epochs = len(set(epoch1_seqs) & set(epoch2_seqs))

    stale_rejections = sum(1 for r in per_phase["B_stale"] if r["status_code"] == 409 and r["rejection_reason"] == "stale_epoch")
    new_epoch_commits = sum(1 for r in per_phase["C_post"] if r["status_code"] == 200 and r["accepted"] == 1)
    pre_epoch_commits = sum(1 for r in per_phase["A_pre"] if r["status_code"] == 200 and r["accepted"] == 1)

    summary = {
        "run_id": run_id,
        "run_index": run_index,
        "incident_id": incident_id,
        "baseline_epoch": baseline_epoch,
        "new_epoch": new_epoch,
        "writes_per_phase": args.writes_per_phase,
        "pre_epoch_commits": pre_epoch_commits,
        "stale_epoch_rejections": stale_rejections,
        "new_epoch_commits": new_epoch_commits,
        "epoch1_journal_rows": len(epoch1_rows),
        "epoch2_journal_rows": len(epoch2_rows),
        "other_epoch_rows": len(other_rows),
        "epoch1_seqs": epoch1_seqs,
        "epoch2_seqs": epoch2_seqs,
        "contiguity_epoch1": contiguity_epoch1,
        "contiguity_epoch2": contiguity_epoch2,
        "duplicate_seqs_across_epochs": duplicate_seqs_across_epochs,
        "environment": env_meta,
    }
    write_record(
        handle,
        run_id=run_id,
        scenario="fenced_promotion_stale_rejection",
        metric_name="summary",
        value_ms=None,
        timestamp_iso=now_iso(),
        scenario_params=summary,
        notes="",
    )
    return summary


def write_record(handle, **fields: Any) -> None:
    handle.write(json.dumps(fields, sort_keys=True, default=str) + "\n")
    handle.flush()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, default=5, help="number of independent runs")
    parser.add_argument("--writes-per-phase", type=int, default=20)
    parser.add_argument("--write-timeout-s", type=float, default=5.0)
    parser.add_argument("--artifact", default=str(DEFAULT_ARTIFACT))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.n < 1:
        raise SystemExit("--n must be >= 1")
    if args.writes_per_phase < 1:
        raise SystemExit("--writes-per-phase must be >= 1")
    wait_for_http(f"{CMD_SYNCD}/health", timeout_s=30.0)
    artifact = Path(args.artifact)
    artifact.parent.mkdir(parents=True, exist_ok=True)
    env_meta = collect_environment()
    summaries: list[dict[str, Any]] = []
    with artifact.open("w", encoding="utf-8") as handle:
        write_record(
            handle,
            run_id="env",
            scenario="fenced_promotion_stale_rejection",
            metric_name="environment",
            value_ms=None,
            timestamp_iso=now_iso(),
            scenario_params={
                "n": args.n,
                "writes_per_phase": args.writes_per_phase,
                "command_endpoint": CMD_SYNCD,
            },
            environment=env_meta,
            notes="",
        )
        for i in range(args.n):
            summary = run_one(i, args, handle, env_meta)
            summaries.append(summary)
            print(
                f"run {i}: stale_rejections={summary['stale_epoch_rejections']} "
                f"new_epoch_commits={summary['new_epoch_commits']} "
                f"duplicate_seqs_across_epochs={summary['duplicate_seqs_across_epochs']}"
            )
    # Print a final aggregate for convenience.
    print(json.dumps({"runs": summaries}, indent=2, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise
