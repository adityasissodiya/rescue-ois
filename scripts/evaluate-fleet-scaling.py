#!/usr/bin/env python3
"""NET-03: propagation and journal throughput as a function of fleet size.

Why this file exists
--------------------
The evaluation measures one responder edge. Reviewer comment 1 asks for an
evaluation that covers diverse intermittent-communication scenarios, and fleet
size is the axis `evaluate-netem-schedule.py` (NET-02, time-varying
connectivity) does not touch. It is also where the paper's own claim is most
exposed: the command edge is a single-writer serializer measured at
356.3 events/s, argued to exceed plausible incident demand by three orders of
magnitude. That argument is only as good as its behaviour when responders
multiply, so this harness sweeps N and reports what actually happens.

What is measured per fleet size:
  * batch propagation time -- first submit to last event journaled
  * arrival-curve percentiles (p50/p95) across the batch
  * journal commit throughput (events/s) at the linearization point
  * delivery ratio and per-responder local acceptance

Measurement precision, stated plainly
-------------------------------------
There is no server-side arrival timestamp on `incident.journal` -- `created_at`
is client-supplied -- so arrival is detected by polling `count(*)` on a timer.
The percentiles below are therefore **arrival-curve percentiles**: the time at
which the journal had accepted k% of the batch, not a per-event latency
distribution. Resolution is one poll interval (default 250 ms). This is
adequate for comparing fleet sizes, whose effects are expected at the
hundreds-of-milliseconds scale, and it is one query per tick rather than per
event -- which matters, because the harness must not itself become the load.

Explicitly NOT claimed: this is a fleet-size sweep on a single host, not a
deployment study. Every edge shares one kernel, one disk and one bridge, so
absolute numbers are a lower bound on real-vehicle behaviour. What transfers is
the *shape* of the curve against N.

Prerequisites:
    Nothing running is required -- the harness brings each fleet size up itself
    via scripts/dev-up.sh. Docker must have headroom for the largest size
    requested; see MEMORY_HEADROOM_FRACTION.

Output:
    artifacts/data/eval_fleet_scaling.jsonl
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
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARTIFACT = ROOT / "artifacts" / "data" / "eval_fleet_scaling.jsonl"

CMD_PG_CONTAINER = os.environ.get("CMD_PG_CONTAINER", "edge-cmd-postgres-1")
EDGE_DB = "rescue_ois_edge"

DEFAULT_SIZES = [1, 3, 5, 10]

# Refuse to measure above this fraction of the Docker VM's memory. A fleet that
# is swapping measures host contention, not fleet scaling -- the same class of
# contamination that made the old Table V unusable (blanket netem qdisc also
# impairing syncd->Postgres). Better to report a measured ceiling than a
# plausible-looking number that means something else.
MEMORY_HEADROOM_FRACTION = 0.85

# Minimum free memory on the *host*, checked separately. The guest-side fraction
# above cannot see host pressure: at N=10 it read 33% while the sweep was being
# killed from outside for host memory exhaustion.
HOST_FREE_FLOOR_MIB = 2048

# Measured host cost of one responder edge (6 containers). Derived from this
# host: vmmemWSL sat at 3.68 GB with 1 responder and 5.72 GB with 10, so nine
# extra edges cost ~2.04 GB. Used only for the pre-flight projection, which is
# why a rough figure is adequate.
PER_EDGE_HOST_MIB = 230


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def run(args: list[str], *, check: bool = False, timeout: float | None = None):
    return subprocess.run(
        args, cwd=ROOT, check=check, capture_output=True, text=True, timeout=timeout
    )


def psql(container: str, sql: str) -> str:
    return run(
        ["docker", "exec", container, "psql", "-U", "postgres", EDGE_DB, "-tAc", sql]
    ).stdout.strip()


def resp_ops(i: int) -> str:
    """Responder i's ops-api. dev-up.sh assigns OPS_API_PORT=18100+i."""
    return f"http://127.0.0.1:{18100 + i}"


def resp_pg(i: int) -> str:
    return f"edge-resp-{i}-postgres-1"


# --------------------------------------------------------------------------
# fleet lifecycle
# --------------------------------------------------------------------------


def running_responder_indices() -> list[int]:
    out = run(["docker", "ps", "--format", "{{.Names}}"]).stdout
    found = set()
    for name in out.split():
        if name.startswith("edge-resp-") and name.endswith("-syncd-1"):
            try:
                found.add(int(name.split("-")[2]))
            except (IndexError, ValueError):
                continue
    return sorted(found)


def teardown_responder(i: int) -> None:
    run(
        ["docker", "compose", "-p", f"edge-resp-{i}", "down", "-v", "--remove-orphans"],
        timeout=180,
    )


def resolve_bash() -> str:
    """Find a bash that can actually see docker.

    On Windows `subprocess` resolves a bare "bash" to `C:\\Windows\\System32\\bash.exe`
    -- the WSL launcher -- which runs inside the default WSL distro. Unless that
    distro has Docker Desktop's WSL integration enabled, dev-up.sh then fails
    with "The command 'docker' could not be found in this WSL 2 distro", and
    `shutil.which` does not predict it because CreateProcess and PATH search
    disagree on ordering. Pick the interpreter explicitly and prove it can reach
    docker before relying on it.
    """
    candidates = [
        os.environ.get("RESCUE_OIS_BASH"),
        r"C:\Program Files\Git\bin\bash.exe",
        r"C:\Program Files\Git\usr\bin\bash.exe",
        shutil.which("bash"),
        "/bin/bash",
    ]
    tried = []
    for candidate in candidates:
        if not candidate or not Path(candidate).exists():
            continue
        tried.append(candidate)
        probe = subprocess.run(
            [candidate, "-c", "command -v docker"],
            capture_output=True, text=True, timeout=60, check=False,
        )
        if probe.returncode == 0 and probe.stdout.strip():
            return candidate
    raise RuntimeError(
        "no bash on this host can reach docker. Tried: "
        + ", ".join(tried or ["<none found>"])
        + ". Set RESCUE_OIS_BASH to a bash that has docker on its PATH "
          "(Git Bash), or enable Docker Desktop's WSL integration for the "
          "default distro."
    )


EDGE_MIGRATIONS = ROOT / "edge" / "db" / "migrations"


def wait_for_postgres(container: str, deadline_s: float = 240.0, stable_checks: int = 3) -> None:
    """Wait for a *stable* Postgres, not merely a responsive one.

    The official image starts a temporary server to run its init scripts, shuts
    it down, then starts the real one. A single successful probe can land on
    that temporary server, after which the next statement dies with "the
    database system is shutting down" -- which is exactly how the first
    migration attempt against a freshly created edge failed. Requiring several
    consecutive successful real queries rides out the restart.
    """
    deadline = time.time() + deadline_s
    consecutive = 0
    while time.time() < deadline:
        probe = run(
            ["docker", "exec", container, "psql", "-U", "postgres", EDGE_DB, "-tAc", "SELECT 1"]
        )
        if probe.returncode == 0 and probe.stdout.strip() == "1":
            consecutive += 1
            if consecutive >= stable_checks:
                return
        else:
            consecutive = 0
        time.sleep(2.0)
    raise RuntimeError(f"{container} never became stably ready within {deadline_s:.0f}s")


def ensure_edge_schema(i: int) -> bool:
    """Apply edge migrations to responder i if its schema is missing.

    dev-up.sh does not migrate -- `scripts/run-migrations.sh edge` is a separate
    step -- so a responder edge created for the first time comes up with an
    empty database. That is not loud: its ops-api reports healthy, events are
    accepted, and only the journal count reveals the loss. It cost a smoke run
    that read exactly 20/30 at N=3, because edge-resp-3 was new while 1 and 2
    had been migrated in an earlier session.

    Migrating only the edges that need it: `run-migrations.sh edge` applies to
    every running edge-*-postgres-1, and only 3 of the 6 edge migrations are
    guarded with IF NOT EXISTS, so blanket re-application fails under
    ON_ERROR_STOP=1 on an already-migrated edge.
    """
    container = resp_pg(i)
    wait_for_postgres(container)
    present = psql(container, "SELECT to_regclass('outbox.device_outbox') IS NOT NULL")
    if present.strip().lower().startswith("t"):
        return False
    for sql_path in sorted(EDGE_MIGRATIONS.glob("*.sql")):
        sql = sql_path.read_text(encoding="utf-8")
        for attempt in range(3):
            proc = subprocess.run(
                ["docker", "exec", "-i", container, "psql", "-U", "postgres",
                 "rescue_ois_edge", "-v", "ON_ERROR_STOP=1"],
                input=sql, capture_output=True, text=True, timeout=300, check=False,
            )
            if proc.returncode == 0:
                break
            detail = (proc.stderr or proc.stdout).strip()
            # Only connection-lifecycle errors are retried. A genuine SQL error
            # must fail loudly rather than be masked by a retry.
            transient = any(
                s in detail
                for s in ("shutting down", "starting up", "the database system is",
                          "could not connect", "connection to server")
            )
            if not transient or attempt == 2:
                raise RuntimeError(
                    f"migration {sql_path.name} failed on {container}: {detail[-300:]}"
                )
            wait_for_postgres(container)
    return True


def ensure_fleet(n: int, *, settle_s: float) -> None:
    """Bring the fleet to exactly n responder edges.

    dev-up.sh only *starts* responders 1..n; it never stops extras, so sweeping
    downwards would silently leave a larger fleet running and attribute its load
    to the smaller size. Extras are torn down explicitly.
    """
    for i in running_responder_indices():
        if i > n:
            print(f"    tearing down edge-resp-{i}")
            teardown_responder(i)

    # Pre-flight, before anything is started. guard_memory() runs *after*
    # ensure_fleet, which is too late: bringing the fleet up is itself the
    # memory-hungry step, and at N=10 the process was killed during bring-up
    # before any guard could report a ceiling. Projecting the cost first turns
    # that into a clean, explained refusal.
    already = len(running_responder_indices())
    to_add = max(0, n - already)
    host = host_memory_state()
    free = host.get("host_mem_available_mib")
    if free is not None and to_add:
        projected = free - to_add * PER_EDGE_HOST_MIB
        if projected < HOST_FREE_FLOOR_MIB:
            raise MemoryError(
                f"refusing to start fleet size {n}: {to_add} more edge(s) at about "
                f"{PER_EDGE_HOST_MIB} MiB each would leave ~{projected:.0f} MiB free on the "
                f"host, below the {HOST_FREE_FLOOR_MIB} MiB floor (currently {free:.0f} MiB "
                f"free). Close other applications or cap the sweep below N={n}."
            )
        print(f"    pre-flight: {free:.0f} MiB free, {to_add} edge(s) to add, "
              f"~{projected:.0f} MiB projected")

    env = dict(os.environ, RESPONDERS=str(n))
    proc = subprocess.run(
        [resolve_bash(), "scripts/dev-up.sh"],
        cwd=ROOT, env=env, capture_output=True, text=True, timeout=900, check=False,
    )
    if proc.returncode != 0:
        # stdout as well as stderr: dev-up.sh pipes docker's own diagnostics to
        # stdout, so a stderr-only message reported an empty reason for the one
        # failure that mattered (wrong bash -> no docker in that WSL distro).
        detail = (proc.stderr.strip() or proc.stdout.strip())[-500:]
        raise RuntimeError(f"dev-up.sh RESPONDERS={n} failed (rc={proc.returncode}): {detail}")

    for i in range(1, n + 1):
        if ensure_edge_schema(i):
            print(f"    migrated edge-resp-{i} (new edge, empty database)")

    wait_for_fleet(n, settle_s=settle_s)


def http_get_ok(url: str, timeout_s: float = 3.0) -> bool:
    try:
        with urlopen(Request(url, method="GET"), timeout=timeout_s) as r:
            return 200 <= r.status < 300
    except (HTTPError, URLError, OSError):
        return False


def wait_for_fleet(n: int, *, settle_s: float, deadline_s: float = 300.0) -> None:
    deadline = time.time() + deadline_s
    pending = {i for i in range(1, n + 1)}
    while pending and time.time() < deadline:
        pending = {i for i in pending if not http_get_ok(f"{resp_ops(i)}/health")}
        if pending:
            time.sleep(2.0)
    if pending:
        raise RuntimeError(f"responder edges never became healthy: {sorted(pending)}")
    # Compose reports "started" well before Postgres has finished recovery and
    # syncd has opened its pool; measuring through that window would charge
    # container startup to the fleet size.
    time.sleep(settle_s)


# --------------------------------------------------------------------------
# resource guard
# --------------------------------------------------------------------------


def parse_mem_usage(stats_output: str) -> tuple[float, int]:
    """Sum the left-hand side of `docker stats` MemUsage lines, in MiB.

    Separated out so the guard's arithmetic is testable without Docker: a silent
    bug here means the headroom check never fires, which is worse than no check
    at all.
    """
    used_mib = 0.0
    counted = 0
    for line in stats_output.splitlines():
        value = line.split("/")[0].strip()
        if not value:
            continue
        number = "".join(c for c in value if c.isdigit() or c == ".")
        unit = "".join(c for c in value if c.isalpha()).upper()
        try:
            mib = float(number)
        except ValueError:
            continue
        if unit.startswith("G"):
            mib *= 1024
        elif unit.startswith("K"):
            mib /= 1024
        elif unit.startswith("B"):
            mib /= 1024 * 1024
        used_mib += mib
        counted += 1
    return used_mib, counted


def memory_state() -> dict[str, Any]:
    total_raw = run(["docker", "info", "--format", "{{.MemTotal}}"]).stdout.strip()
    total_mib = int(total_raw) / (1024 * 1024) if total_raw.isdigit() else None

    stats = run(["docker", "stats", "--no-stream", "--format", "{{.MemUsage}}"], timeout=120)
    used_mib, counted = parse_mem_usage(stats.stdout)
    return {
        "docker_mem_total_mib": round(total_mib, 1) if total_mib else None,
        "docker_mem_used_mib": round(used_mib, 1),
        "containers_counted": counted,
        "used_fraction": round(used_mib / total_mib, 4) if total_mib else None,
    }


def host_memory_state() -> dict[str, Any]:
    """Host memory, which the in-VM figures cannot see.

    Docker runs in a WSL2 VM here, so `docker info`/`docker stats` describe the
    *guest*. At N=10 the guest read a comfortable 33% while the host was
    starving -- vmmemWSL had ballooned to 5.72 GB and the sweep was killed from
    outside. A guard that only watches the guest cannot report that ceiling; it
    just dies.
    """
    meminfo = Path("/proc/meminfo")
    if meminfo.exists():
        vals = {}
        for line in meminfo.read_text().splitlines():
            key, _, rest = line.partition(":")
            vals[key] = float(rest.strip().split()[0]) / 1024.0
        return {
            "host_mem_total_mib": round(vals.get("MemTotal", 0.0), 1) or None,
            "host_mem_available_mib": round(vals.get("MemAvailable", 0.0), 1) or None,
        }
    probe = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         ("$o=Get-CimInstance Win32_OperatingSystem;"
          "'{0} {1}' -f $o.TotalVisibleMemorySize,$o.FreePhysicalMemory")],
        capture_output=True, text=True, timeout=120, check=False,
    )
    parts = probe.stdout.split()
    if len(parts) == 2:
        try:
            return {
                "host_mem_total_mib": round(float(parts[0]) / 1024.0, 1),
                "host_mem_available_mib": round(float(parts[1]) / 1024.0, 1),
            }
        except ValueError:
            pass
    return {"host_mem_total_mib": None, "host_mem_available_mib": None}


def guard_memory(n: int) -> dict[str, Any]:
    state = memory_state()
    state.update(host_memory_state())

    host_free = state.get("host_mem_available_mib")
    if host_free is not None and host_free < HOST_FREE_FLOOR_MIB:
        raise MemoryError(
            f"fleet size {n} leaves only {host_free:.0f} MiB free on the host, below the "
            f"{HOST_FREE_FLOOR_MIB} MiB floor. The Docker VM still looks healthy from inside "
            f"({state.get('used_fraction', 0):.0%} of the guest), but the host is the binding "
            f"constraint: WSL2 balloons toward its configured maximum and everything outside "
            f"it competes for the remainder. Lower [wsl2] memory in %USERPROFILE%\\.wslconfig, "
            f"close other applications, or cap the sweep below N={n}."
        )

    frac = state.get("used_fraction")
    if frac is not None and frac > MEMORY_HEADROOM_FRACTION:
        raise MemoryError(
            f"fleet size {n} uses {frac:.0%} of the Docker VM's memory "
            f"({state['docker_mem_used_mib']:.0f} of {state['docker_mem_total_mib']:.0f} MiB), "
            f"above the {MEMORY_HEADROOM_FRACTION:.0%} ceiling. Measuring here would report "
            f"host contention as fleet scaling. Raise the WSL2 memory allocation "
            f"(%USERPROFILE%\\.wslconfig, [wsl2] memory=...) or cap the sweep below N={n}."
        )
    return state


# --------------------------------------------------------------------------
# workload
# --------------------------------------------------------------------------


def reset_tables(n: int) -> None:
    psql(CMD_PG_CONTAINER, "TRUNCATE incident.journal, incident.state CASCADE;")
    for i in range(1, n + 1):
        psql(resp_pg(i), "TRUNCATE outbox.device_outbox CASCADE;")


def journal_count(incident_id: str) -> int:
    raw = psql(
        CMD_PG_CONTAINER,
        f"SELECT count(*) FROM incident.journal WHERE incident_id = '{incident_id}'",
    )
    try:
        return int(raw or "0")
    except ValueError:
        return 0


def submit(responder: int, incident_id: str, index: int) -> bool:
    body = {
        "client_event_id": str(uuid.uuid4()),
        "incident_id": incident_id,
        "event_type": "observation",
        "payload": {"i": index, "responder": responder},
        "device_id": f"tab-fleet-{responder}",
        "user_id": "u",
        "occurred_at": now_iso(),
    }
    req = Request(
        f"{resp_ops(responder)}/api/events",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(req, timeout=15.0) as r:
            return 200 <= r.status < 300
    except HTTPError as exc:
        return 200 <= exc.code < 300
    except (URLError, OSError):
        return False


def percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    k = (len(ordered) - 1) * (p / 100.0)
    lo, hi = int(k), min(int(k) + 1, len(ordered) - 1)
    if lo == hi:
        return ordered[lo]
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (k - lo)


def measure_fleet(n: int, args: argparse.Namespace, run_index: int) -> dict[str, Any]:
    """One measurement at fleet size n: all responders submit concurrently."""
    reset_tables(n)
    incident_id = str(uuid.uuid4())
    expected = n * args.events_per_responder

    t0 = time.perf_counter()
    # Concurrent, not round-robin: the question is what the single-writer
    # boundary does under simultaneous pressure from N edges, which a serialized
    # submission loop would never produce.
    with ThreadPoolExecutor(max_workers=n) as pool:
        futures = [
            pool.submit(submit, i, incident_id, j)
            for i in range(1, n + 1)
            for j in range(args.events_per_responder)
        ]
        accepted = sum(1 for f in futures if f.result())
    submit_done = time.perf_counter()

    # Arrival curve: count-over-time. Each observed increase attributes the
    # newly seen events to this tick, which is what the percentiles are built
    # from -- see the module docstring on precision.
    curve: list[tuple[float, int]] = []
    arrivals: list[float] = []
    seen = 0
    deadline = time.perf_counter() + args.arrival_timeout_s
    while time.perf_counter() < deadline:
        count = journal_count(incident_id)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        curve.append((round(elapsed_ms, 1), count))
        if count > seen:
            arrivals.extend([elapsed_ms] * (count - seen))
            seen = count
        if count >= expected:
            break
        time.sleep(args.poll_interval_s)

    all_done_ms = arrivals[-1] if seen >= expected and arrivals else None
    elapsed_s = (arrivals[-1] / 1000.0) if arrivals else None
    return {
        "fleet_size": n,
        "run_index": run_index,
        "incident_id": incident_id,
        "events_per_responder": args.events_per_responder,
        "expected_events": expected,
        "locally_accepted": accepted,
        "journaled": seen,
        "delivery_ratio": round(seen / expected, 4) if expected else None,
        "complete": seen >= expected,
        "submit_wall_ms": round((submit_done - t0) * 1000.0, 1),
        "all_journaled_ms": round(all_done_ms, 1) if all_done_ms else None,
        "arrival_p50_ms": round(percentile(arrivals, 50), 1) if arrivals else None,
        "arrival_p95_ms": round(percentile(arrivals, 95), 1) if arrivals else None,
        "journal_throughput_eps": (
            round(seen / elapsed_s, 1) if elapsed_s and elapsed_s > 0 else None
        ),
        "arrival_curve": curve,
        "poll_interval_s": args.poll_interval_s,
    }


# --------------------------------------------------------------------------
# driver
# --------------------------------------------------------------------------


def write_record(handle, **fields: Any) -> None:
    handle.write(json.dumps(fields, sort_keys=True, default=str) + "\n")
    handle.flush()


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
        "git_commit": git_commit,
        "git_tree_dirty": git_dirty,
        "docker_server_version": docker_v.stdout.strip() or None,
        "docker_compose_version": compose_v.stdout.strip() or None,
        "host_cpu_count": os.cpu_count(),
        "host_uname": " ".join(platform.uname()),
        "timestamp_iso": now_iso(),
        **memory_state(),
    }


def summarise(size: int, results: list[dict]) -> dict[str, Any]:
    done = [r for r in results if r["complete"]]
    def med(key: str) -> float | None:
        vals = [r[key] for r in done if r.get(key) is not None]
        return round(statistics.median(vals), 1) if vals else None
    return {
        "fleet_size": size,
        "n_runs": len(results),
        "n_complete": len(done),
        "median_all_journaled_ms": med("all_journaled_ms"),
        "median_arrival_p50_ms": med("arrival_p50_ms"),
        "median_arrival_p95_ms": med("arrival_p95_ms"),
        "median_journal_throughput_eps": med("journal_throughput_eps"),
        "min_delivery_ratio": min((r["delivery_ratio"] for r in results), default=None),
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--sizes", default=",".join(str(s) for s in DEFAULT_SIZES),
                   help="comma-separated fleet sizes, e.g. 1,3,5,10")
    p.add_argument("--runs", type=int, default=5, help="measurements per fleet size")
    p.add_argument("--events-per-responder", type=int, default=20)
    p.add_argument("--poll-interval-s", type=float, default=0.25)
    p.add_argument("--arrival-timeout-s", type=float, default=180.0)
    p.add_argument("--settle-s", type=float, default=15.0,
                   help="pause after a fleet reports healthy, before measuring")
    p.add_argument("--smoke", action="store_true", help="sizes 1,3 with 2 runs -- a sanity gate")
    p.add_argument("--artifact", default=str(DEFAULT_ARTIFACT))
    args = p.parse_args()
    if args.smoke:
        args.sizes, args.runs, args.events_per_responder = "1,3", 2, 10
    args.sizes = [int(s) for s in args.sizes.split(",") if s.strip()]
    return args


def main() -> int:
    args = parse_args()
    artifact = Path(args.artifact)
    artifact.parent.mkdir(parents=True, exist_ok=True)
    run_id = str(uuid.uuid4())
    env_meta = collect_environment()
    print(f"run_id={run_id} sizes={args.sizes} runs={args.runs} "
          f"events/responder={args.events_per_responder}")
    print(f"docker memory: {env_meta['docker_mem_used_mib']:.0f} / "
          f"{env_meta['docker_mem_total_mib']:.0f} MiB in use")

    rc = 0
    with artifact.open("a", encoding="utf-8") as handle:
        write_record(handle, run_id=run_id, scenario="fleet_scaling",
                     metric_name="environment", value_ms=None, timestamp_iso=now_iso(),
                     scenario_params={"sizes": args.sizes, "runs_per_size": args.runs},
                     environment=env_meta, notes="single-host fleet sweep")

        for size in args.sizes:
            print(f"fleet size {size}: bringing up...")
            # ensure_fleet is inside the guarded block too: its pre-flight
            # projection raises the same MemoryError, and a measured ceiling is
            # a result worth recording, not a traceback. Leaving it outside
            # produced an unhandled crash and no artifact record for exactly the
            # case the guard exists to report.
            try:
                ensure_fleet(size, settle_s=args.settle_s)
                mem = guard_memory(size)
            except MemoryError as exc:
                print(f"ABORT at N={size}: {exc}", file=sys.stderr)
                write_record(handle, run_id=run_id, scenario="fleet_scaling",
                             metric_name="ceiling", value_ms=None, timestamp_iso=now_iso(),
                             scenario_params={"fleet_size": size, "reason": str(exc),
                                              **memory_state(), **host_memory_state()},
                             notes="sweep stopped: insufficient memory headroom")
                rc = 3
                break
            print(f"  memory {mem['docker_mem_used_mib']:.0f}/"
                  f"{mem['docker_mem_total_mib']:.0f} MiB ({mem['used_fraction']:.0%})")

            results = []
            for run_index in range(args.runs):
                r = measure_fleet(size, args, run_index)
                r["memory"] = mem
                results.append(r)
                write_record(handle, run_id=run_id, scenario="fleet_scaling",
                             metric_name="run", value_ms=r["all_journaled_ms"],
                             timestamp_iso=now_iso(), scenario_params=r, notes="")
                print(f"  run {run_index}: journaled {r['journaled']}/{r['expected_events']} "
                      f"all_done={r['all_journaled_ms']}ms "
                      f"p95={r['arrival_p95_ms']}ms "
                      f"tput={r['journal_throughput_eps']}/s")

            summary = summarise(size, results)
            write_record(handle, run_id=run_id, scenario="fleet_scaling",
                         metric_name="size_summary", value_ms=summary["median_all_journaled_ms"],
                         timestamp_iso=now_iso(), scenario_params=summary, notes="")
            print(f"  -> {json.dumps(summary, sort_keys=True)}")

    print(f"done. records in {artifact}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
