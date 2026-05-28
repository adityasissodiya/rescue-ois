#!/usr/bin/env python3
"""Measure R2 durability: the responder outbox survives a vehicle restart.

Boundary under test: an event accepted into the responder's local
outbox.device_outbox must (a) survive a full power-cycle of the responder
edge's Postgres, and (b) forward to the command incident journal exactly once
after the responder syncd restarts -- no loss, no duplicate.

Procedure (single responder edge, command edge, core already up):
  1. Reset the command journal/state and the responder outbox.
  2. Stop the responder syncd so nothing forwards.
  3. POST N events to the responder ops-api; they queue unforwarded in the
     local outbox.
  4. Snapshot: N unforwarded outbox rows, 0 forwarded, 0 command-journal rows.
  5. Restart (power-cycle) the responder Postgres, then start the responder
     syncd. Re-read the outbox: the N rows must still be present (durability).
  6. Wait for the resumed push loop to forward all N to the command journal.
  7. Verify: command journal holds exactly N rows for the incident with
     contiguous event_seq and no duplicates, and the outbox is fully drained
     (forwarded_at set on all N).

Emits per-phase plus summary JSONL records compatible with the paper data
layout.
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
DEFAULT_ARTIFACT = ROOT / "paper" / "data" / "eval_outbox_crash_restart.jsonl"
RESP_OPS = os.environ.get("RESP_OPS", "http://127.0.0.1:18101")
RESPONDER_INDEX = int(os.environ.get("RESPONDER_INDEX", "1"))
RESP_SYNCD = f"edge-resp-{RESPONDER_INDEX}-syncd-1"
RESP_POSTGRES = f"edge-resp-{RESPONDER_INDEX}-postgres-1"
CMD_POSTGRES = "edge-cmd-postgres-1"
SCENARIO = "outbox_durability_across_vehicle_restart"


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def run(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=ROOT, check=check, capture_output=True, text=True)


def docker_exec(container: str, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return run(["docker", "exec", container, *args], check=check)


def psql(container: str, db: str, sql: str, *, check: bool = True) -> str:
    return docker_exec(container, "psql", "-U", "postgres", db, "-tAc", sql, check=check).stdout.strip()


def write_record(handle, **fields: Any) -> None:
    handle.write(json.dumps(fields, sort_keys=True, default=str) + "\n")
    handle.flush()


def wait_for_postgres(container: str, db: str, timeout_s: float = 60.0) -> None:
    deadline = time.monotonic() + timeout_s
    last = ""
    while time.monotonic() < deadline:
        proc = docker_exec(container, "psql", "-U", "postgres", db, "-tAc", "SELECT 1", check=False)
        if proc.returncode == 0 and proc.stdout.strip() == "1":
            return
        last = proc.stderr.strip() or proc.stdout.strip()
        time.sleep(0.5)
    raise TimeoutError(f"{container}/{db} not ready: {last}")


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
        time.sleep(0.5)
    raise TimeoutError(f"{url} not healthy: {last}")


def post_event(incident_id: str, index: int, timeout_s: float = 10.0) -> int:
    body = {
        "client_event_id": str(uuid.uuid4()),
        "incident_id": incident_id,
        "event_type": "observation",
        "payload": {"j": index, "origin": "outbox-crash-test"},
        "device_id": "tab-eval",
        "user_id": "u",
        "occurred_at": now_iso(),
    }
    data = json.dumps(body).encode("utf-8")
    req = Request(f"{RESP_OPS}/api/events", data=data, headers={"Content-Type": "application/json"}, method="POST")
    with urlopen(req, timeout=timeout_s) as resp:
        return resp.status


def outbox_unforwarded(incident_id: str) -> int:
    return int(psql(RESP_POSTGRES, "rescue_ois_edge",
                    f"SELECT count(*) FROM outbox.device_outbox WHERE incident_id='{incident_id}' AND forwarded_at IS NULL") or "0")


def outbox_total(incident_id: str) -> int:
    return int(psql(RESP_POSTGRES, "rescue_ois_edge",
                    f"SELECT count(*) FROM outbox.device_outbox WHERE incident_id='{incident_id}'") or "0")


def journal_count(incident_id: str) -> int:
    return int(psql(CMD_POSTGRES, "rescue_ois_edge",
                    f"SELECT count(*) FROM incident.journal WHERE incident_id='{incident_id}'", check=False) or "0")


def journal_seqs(incident_id: str) -> list[int]:
    raw = psql(CMD_POSTGRES, "rescue_ois_edge",
               f"SELECT COALESCE(json_agg(event_seq ORDER BY event_seq), '[]'::json) FROM incident.journal WHERE incident_id='{incident_id}'")
    return [int(x) for x in json.loads(raw or "[]")]


def duplicate_seq_count(incident_id: str) -> int:
    return int(psql(CMD_POSTGRES, "rescue_ois_edge",
                    f"""SELECT COALESCE(SUM(c-1),0) FROM (
                        SELECT event_seq, COUNT(*) c FROM incident.journal
                        WHERE incident_id='{incident_id}' GROUP BY event_seq HAVING COUNT(*)>1) d""") or "0")


def reset_tables() -> None:
    psql(CMD_POSTGRES, "rescue_ois_edge",
         "TRUNCATE incident.journal, incident.state CASCADE; DELETE FROM sync.state;")
    psql(RESP_POSTGRES, "rescue_ois_edge", "TRUNCATE outbox.device_outbox CASCADE;")


def collect_environment() -> dict[str, Any]:
    def out(args: list[str]) -> str | None:
        p = run(args, check=False)
        return p.stdout.strip() if p.returncode == 0 else None
    mem_kb = cpu = None
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemTotal:"):
                mem_kb = int(line.split()[1]); break
    except OSError:
        pass
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("model name"):
                cpu = line.split(":", 1)[1].strip(); break
    except OSError:
        pass
    return {
        "git_commit": out(["git", "rev-parse", "HEAD"]),
        "timestamp_iso": now_iso(),
        "docker_server_version": out(["docker", "version", "--format", "{{.Server.Version}}"]),
        "docker_compose_version": out(["docker", "compose", "version", "--short"]),
        "host_uname": " ".join(platform.uname()),
        "host_cpu_model": cpu,
        "host_cpu_count": os.cpu_count(),
        "host_mem_total_kb": mem_kb,
    }


def run_experiment(args: argparse.Namespace) -> dict[str, Any]:
    artifact = Path(args.artifact)
    artifact.parent.mkdir(parents=True, exist_ok=True)
    run_id = str(uuid.uuid4())
    incident_id = str(uuid.uuid4())
    n = args.events

    with artifact.open("w", encoding="utf-8") as handle:
        env_meta = collect_environment()
        write_record(handle, run_id=run_id, scenario=SCENARIO, metric_name="environment",
                     value_ms=None, timestamp_iso=now_iso(),
                     scenario_params={"events": n, "responder_syncd": RESP_SYNCD,
                                      "responder_postgres": RESP_POSTGRES},
                     environment=env_meta, notes="")

        reset_tables()

        # 2. Stop the responder syncd so nothing forwards.
        run(["docker", "stop", RESP_SYNCD])

        # 3. Post N events; they queue unforwarded in the local outbox.
        for i in range(n):
            status = post_event(incident_id, i)
            if status not in (200, 201, 202):
                raise RuntimeError(f"ops-api POST returned {status} on event {i}")

        # 4. Pre-crash snapshot.
        pre_unforwarded = outbox_unforwarded(incident_id)
        pre_journal = journal_count(incident_id)
        write_record(handle, run_id=run_id, scenario=SCENARIO, metric_name="pre_restart_outbox_unforwarded",
                     value_ms=None, timestamp_iso=now_iso(),
                     scenario_params={"unforwarded": pre_unforwarded, "command_journal": pre_journal},
                     notes="" if (pre_unforwarded == n and pre_journal == 0) else "unexpected_pre_state")

        # 5. Power-cycle the responder Postgres, then re-read the outbox.
        t_restart = time.perf_counter_ns()
        run(["docker", "restart", RESP_POSTGRES])
        wait_for_postgres(RESP_POSTGRES, "rescue_ois_edge")
        survived = outbox_unforwarded(incident_id)
        write_record(handle, run_id=run_id, scenario=SCENARIO, metric_name="post_restart_outbox_survived",
                     value_ms=None, timestamp_iso=now_iso(),
                     scenario_params={"unforwarded_after_db_restart": survived, "expected": n},
                     notes="" if survived == n else "rows_lost_across_restart")

        # 6. Bring the responder syncd back and let it drain the outbox.
        run(["docker", "start", RESP_SYNCD])
        wait_for_http(f"http://127.0.0.1:{18200 + RESPONDER_INDEX}/health")
        deadline = time.monotonic() + args.forward_timeout_s
        got = 0
        while time.monotonic() < deadline:
            got = journal_count(incident_id)
            if got >= n:
                break
            time.sleep(0.25)
        recovery_ms = (time.perf_counter_ns() - t_restart) / 1e6

        # 7. Verify.
        seqs = journal_seqs(incident_id)
        duplicates = duplicate_seq_count(incident_id)
        remaining_unforwarded = outbox_unforwarded(incident_id)
        contiguous = seqs == list(range(1, len(seqs) + 1))
        success = (got == n and duplicates == 0 and remaining_unforwarded == 0
                   and contiguous and survived == n)

        summary = {
            "events": n,
            "pre_restart_unforwarded": pre_unforwarded,
            "survived_db_restart": survived,
            "forwarded_to_command_journal": got,
            "duplicate_sequence_count": duplicates,
            "sequence_contiguous": contiguous,
            "outbox_unforwarded_after_drain": remaining_unforwarded,
            "recovery_ms": recovery_ms,
            "success": success,
            "run_id": run_id,
            "incident_id": incident_id,
            "environment": env_meta,
            "artifact_path": str(artifact),
        }
        write_record(handle, run_id=run_id, scenario=SCENARIO, metric_name="summary",
                     value_ms=recovery_ms if success else None, timestamp_iso=now_iso(),
                     scenario_params=summary, notes="" if success else "R2_boundary_violation")
        return summary


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--events", type=int, default=50)
    p.add_argument("--forward-timeout-s", type=float, default=60.0)
    p.add_argument("--artifact", default=str(DEFAULT_ARTIFACT))
    return p.parse_args()


def main() -> int:
    args = parse_args()
    summary = run_experiment(args)
    print(json.dumps(summary, indent=2, sort_keys=True, default=str))
    return 0 if summary["success"] else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise
