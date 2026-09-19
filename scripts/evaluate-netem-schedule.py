#!/usr/bin/env python3
"""NET-02: propagation across *transitions* between connectivity regimes.

Answers the reviewer criticism that the evaluation covers only two static
`tc-netem` profiles applied for the whole of a run. The existing harness
(`evaluate-netem-propagation.py`) measures steady state: apply a profile, take
n measurements, remove it. Real vehicle-edge connectivity is not steady -- it
alternates between wide-area backhaul, mesh-only contact, and total isolation,
and what matters operationally is what happens *at the transitions*: whether
anything is lost, how far the outbox backs up while isolated, and how long the
backlog takes to drain once the link returns.

This harness therefore runs one continuous submission stream at a fixed low
rate while walking a schedule of regimes within a single run, and attributes
every event to the regime in force when it was submitted.

What is measured per phase:
  * delivery success ratio (did the event reach the authoritative journal)
  * time-to-authoritative-journal-visibility
  * outbox backlog as a time series (not just its end state)
  * drain time after connectivity is restored

Explicitly NOT claimed: this is a connectivity-regime schedule, not a mobility
model. No vehicle positions, path loss or RAN topology are simulated. The
regime durations and impairment parameters are literature-informed (the same
citations the paper already uses for its static profiles); the transitions are
synthetic and reproducible, which is the point -- a reviewer can re-run them.

Prerequisites:
    core + edge-cmd + edge-resp-1 running, with the responder ops-api reachable
    (RESP_OPS) and CAP_NET_ADMIN on both syncd containers.

Output:
    artifacts/data/eval_netem_schedule.jsonl
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
import threading
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARTIFACT = ROOT / "artifacts" / "data" / "eval_netem_schedule.jsonl"

RESP_OPS = os.environ.get("RESP_OPS", "http://127.0.0.1:18101")
CMD_PG_CONTAINER = os.environ.get("CMD_PG_CONTAINER", "edge-cmd-postgres-1")
RESP_PG_CONTAINER = os.environ.get("RESP_PG_CONTAINER", "edge-resp-1-postgres-1")
RESP_SYNCD_CONTAINER = os.environ.get("RESP_SYNCD_CONTAINER", "edge-resp-1-syncd-1")
CMD_SYNCD_CONTAINER = os.environ.get("CMD_SYNCD_CONTAINER", "edge-cmd-syncd-1")
NETEM_CONTAINERS = (RESP_SYNCD_CONTAINER, CMD_SYNCD_CONTAINER)
EDGE_DB = "rescue_ois_edge"

# Connectivity regimes. "clear" removes impairment entirely; "isolated" drops
# everything, which is how a vehicle out of mesh range behaves from the
# responder's point of view.
REGIMES: dict[str, dict[str, str] | None] = {
    "clear": None,
    "mesh_stressed": {"delay": "80ms", "jitter": "30ms", "loss": "2%"},
    "mesh_degraded": {"delay": "200ms", "jitter": "80ms", "loss": "8%"},
    "isolated": {"delay": "0ms", "jitter": "0ms", "loss": "100%"},
}

# Drain detection cadence. Deliberately decoupled from submit_interval_s: the
# recovery measurement's resolution must not be an artifact of how often the
# workload happens to submit.
DRAIN_POLL_S = 0.25

# The schedule walked within a single run. Durations are deliberately short
# enough to keep a full run practical while still crossing every transition.
DEFAULT_SCHEDULE: list[tuple[str, int]] = [
    ("clear", 30),
    ("mesh_stressed", 45),
    ("mesh_degraded", 45),
    ("isolated", 60),
    ("clear", 90),
]


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def run(args: list[str], *, check: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=ROOT, check=check, capture_output=True, text=True)


def docker_exec(container: str, *args: str) -> subprocess.CompletedProcess[str]:
    return run(["docker", "exec", container, *args])


def psql(container: str, sql: str) -> str:
    return docker_exec(container, "psql", "-U", "postgres", EDGE_DB, "-tAc", sql).stdout.strip()


def container_ip(container: str) -> str:
    out = run(
        [
            "docker", "inspect", "-f",
            '{{(index .NetworkSettings.Networks "rescue-ois-net").IPAddress}}',
            container,
        ]
    ).stdout.strip()
    if not out:
        raise RuntimeError(f"could not resolve rescue-ois-net IP for {container}")
    return out


def apply_regime(name: str) -> None:
    """Impair only the responder<->command path, not everything on eth0.

    A root netem qdisc applies to *all* egress on the interface, which on this
    topology includes the container's own Postgres -- both edges reach their
    database over the same bridge. Impairing that does not emulate a degraded
    mesh link; it emulates a vehicle losing its own local storage, which is a
    different failure and contradicts R1 (local work continues while the link
    is bad). It would also inflate measured propagation latency with database
    round-trip delay that has nothing to do with the mesh.

    So traffic is classified with a prio qdisc and only packets destined for
    the peer edge are pushed into the impaired band, mirroring the surgical
    approach `scripts/inject-partition.sh wan` already uses.
    """
    remove_netem()
    spec = REGIMES[name]
    if spec is None:
        return

    peer_of = {
        RESP_SYNCD_CONTAINER: container_ip(CMD_SYNCD_CONTAINER),
        CMD_SYNCD_CONTAINER: container_ip(RESP_SYNCD_CONTAINER),
    }
    for container, peer_ip in peer_of.items():
        steps = [
            ["tc", "qdisc", "add", "dev", "eth0", "root", "handle", "1:",
             "prio", "bands", "3", "priomap", *(["0"] * 16)],
            ["tc", "qdisc", "add", "dev", "eth0", "parent", "1:2", "handle", "20:",
             "netem", "delay", spec["delay"], spec["jitter"], "loss", spec["loss"]],
            ["tc", "filter", "add", "dev", "eth0", "protocol", "ip", "parent", "1:0",
             "prio", "1", "u32", "match", "ip", "dst", f"{peer_ip}/32", "flowid", "1:2"],
        ]
        for step in steps:
            proc = docker_exec(container, *step)
            if proc.returncode != 0:
                raise RuntimeError(
                    f"apply_regime({name}) on {container} failed at {' '.join(step)}: "
                    f"{proc.stderr.strip() or proc.stdout.strip()}"
                )


def remove_netem() -> None:
    for container in NETEM_CONTAINERS:
        docker_exec(container, "tc", "qdisc", "del", "dev", "eth0", "root")


def outbox_backlog(incident_id: str) -> int:
    raw = psql(
        RESP_PG_CONTAINER,
        f"SELECT count(*) FROM outbox.device_outbox "
        f"WHERE incident_id = '{incident_id}' AND forwarded_at IS NULL",
    )
    return int(raw or "0")


def journal_seqs(incident_id: str) -> set[str]:
    raw = psql(
        CMD_PG_CONTAINER,
        f"SELECT COALESCE(string_agg(client_event_id::text, ','), '') "
        f"FROM incident.journal WHERE incident_id = '{incident_id}'",
    )
    return {c for c in raw.split(",") if c}


def submit(incident_id: str, index: int, regime: str) -> tuple[str, bool]:
    client_event_id = str(uuid.uuid4())
    body = {
        "client_event_id": client_event_id,
        "incident_id": incident_id,
        "event_type": "observation",
        "payload": {"i": index, "regime": regime},
        "device_id": "tab-netem-schedule",
        "user_id": "u",
        "occurred_at": now_iso(),
    }
    req = Request(
        f"{RESP_OPS}/api/events",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(req, timeout=10.0) as resp:
            return client_event_id, resp.status in (200, 201)
    except HTTPError as exc:
        return client_event_id, exc.code in (200, 201)
    except (URLError, TimeoutError, OSError):
        # A submission that cannot even reach the local ops-api is itself a
        # datum: the responder's own API should stay available under mesh
        # impairment, because the outbox is local. Narrow to transport errors
        # so a bug in this harness surfaces instead of being scored as a loss.
        return client_event_id, False


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
        "docker_compose_version": compose_v.stdout.strip() or None,
        "docker_server_version": docker_v.stdout.strip() or None,
        "git_commit": git_commit,
        "git_tree_dirty": git_dirty,
        "host_cpu_count": os.cpu_count(),
        "host_uname": " ".join(platform.uname()),
        "timestamp_iso": now_iso(),
    }


def reset_tables() -> None:
    psql(CMD_PG_CONTAINER, "TRUNCATE incident.journal, incident.state CASCADE; DELETE FROM sync.state;")
    psql(RESP_PG_CONTAINER, "TRUNCATE outbox.device_outbox CASCADE;")


class BacklogSampler(threading.Thread):
    """Samples outbox depth on a timer so backlog is a curve, not an endpoint."""

    def __init__(self, incident_id: str, interval_s: float = 2.0) -> None:
        super().__init__(daemon=True)
        self.incident_id = incident_id
        self.interval_s = interval_s
        self.samples: list[dict] = []
        # NOT `self._stop`: threading.Thread defines a real `_stop()` method
        # that join() calls internally, so binding an Event to that name makes
        # join() raise "TypeError: 'Event' object is not callable" -- after the
        # measurement has completed but before any result is written.
        self._stop_event = threading.Event()
        self.regime = "clear"

    def run(self) -> None:
        while not self._stop_event.is_set():
            try:
                depth = outbox_backlog(self.incident_id)
            except (ValueError, OSError, subprocess.SubprocessError):
                # -1 marks a sample we failed to take, so a gap in the backlog
                # curve is visible in the artifact rather than looking like a
                # genuine drop to zero.
                depth = -1
            self.samples.append(
                {"t": time.time(), "regime": self.regime, "unforwarded": depth}
            )
            self._stop_event.wait(self.interval_s)

    def stop(self) -> None:
        self._stop_event.set()


def run_schedule(handle, args: argparse.Namespace, env_meta: dict) -> dict:
    incident_id = str(uuid.uuid4())
    reset_tables()
    remove_netem()

    submitted: list[dict] = []
    sampler = BacklogSampler(incident_id)
    sampler.start()
    t_start = time.time()

    try:
        index = 0
        prev_regime: str | None = None
        phase_within: dict[int, dict] = {}
        restore_t0: float | None = None
        restore_from: str | None = None
        pending: set[str] = set()
        pending_at_restore = 0
        drain_time_s: float | None = None
        last_drain_poll = 0.0
        for phase_ordinal, (regime, duration_s) in enumerate(args.schedule):
            sampler.regime = regime
            apply_regime(regime)
            phase_t0 = time.time()
            phase_end = phase_t0 + duration_s
            phase_first = index

            # Recovery is measured from the moment connectivity returns, not
            # from the end of the run. The backlog accumulated while isolated
            # drains *during* the clear phase, so a timer started afterwards
            # measures "time to confirm an empty queue" (previously 0.12 s),
            # not recovery. The target set is frozen at the transition: events
            # submitted after the link is back are not part of the backlog
            # being recovered.
            if regime == "clear" and prev_regime not in (None, "clear"):
                restore_t0 = phase_t0
                restore_from = prev_regime
                pending = {
                    s["client_event_id"] for s in submitted if s["locally_accepted"]
                }
                pending_at_restore = len(pending)

            while time.time() < phase_end:
                cid, accepted = submit(incident_id, index, regime)
                submitted.append(
                    {
                        "client_event_id": cid,
                        "index": index,
                        "regime": regime,
                        "submitted_at": time.time(),
                        "locally_accepted": accepted,
                    }
                )
                index += 1
                # Sleep in slices rather than one submit_interval_s block, so
                # the drain check runs on its own cadence. Tying it to the
                # submission loop quantised drain_time_s to whole submit
                # intervals: a 10-run sweep reported a bimodal {0.14 s, 5.25 s}
                # with nothing in between, which is the sampling grid, not the
                # system. The backlog curve showed 0 at the first post-restore
                # sampler tick in every one of those runs.
                slept = 0.0
                while slept < args.submit_interval_s:
                    step = min(DRAIN_POLL_S, args.submit_interval_s - slept)
                    time.sleep(step)
                    slept += step
                    if (
                        restore_t0 is not None
                        and drain_time_s is None
                        and time.time() - last_drain_poll >= DRAIN_POLL_S
                    ):
                        last_drain_poll = time.time()
                        if pending.issubset(journal_seqs(incident_id)):
                            drain_time_s = round(time.time() - restore_t0, 3)
                            print(
                                f"  recovered in {drain_time_s}s "
                                f"({pending_at_restore} pending at restore)"
                            )

            # Delivery *within* the phase: of the events submitted under this
            # regime, how many were journal-visible by the time it ended. The
            # end-of-run ratio alone always reads 1.0 once the drain succeeds,
            # which makes isolation look inconsequential; this is the column
            # that shows it is not.
            arrived_now = journal_seqs(incident_id)
            in_phase = [s for s in submitted if s["index"] >= phase_first]
            within = sum(1 for s in in_phase if s["client_event_id"] in arrived_now)
            # Keyed by phase ordinal, not regime name: "clear" appears twice in
            # the default schedule and the two phases mean different things.
            phase_within[phase_ordinal] = {
                "phase": phase_ordinal,
                "regime": regime,
                "submitted_in_phase": len(in_phase),
                "delivered_by_phase_end": within,
                "delivered_within_phase_ratio": (
                    round(within / len(in_phase), 4) if in_phase else None
                ),
            }
            prev_regime = regime

            # Checkpoint each phase as it completes. Every other record for
            # this run is written after the measurement loop, so a failure
            # anywhere in it previously discarded the whole run -- which is
            # exactly what happened when a bug in the sampler's cleanup threw
            # after all four phases had already been measured. Losing one
            # phase is recoverable; losing the run is not.
            write_record(
                handle,
                run_id=incident_id,
                scenario="netem_schedule",
                metric_name="phase_complete",
                value_ms=None,
                timestamp_iso=now_iso(),
                scenario_params={
                    "regime": regime,
                    "phase": phase_ordinal,
                    "regime_params": REGIMES[regime],
                    "duration_s": duration_s,
                    "first_index": phase_first,
                    "last_index": index - 1,
                    "submitted_in_phase": index - phase_first,
                    "backlog_at_phase_end": sampler.samples[-1]["unforwarded"]
                    if sampler.samples
                    else None,
                    **phase_within[phase_ordinal],
                },
                notes="",
            )
            print(f"  phase {regime} done ({duration_s}s, {index} submitted so far)")

        # Final settle: every event, including those submitted after the link
        # returned. This is a completeness check ("nothing was lost"), NOT the
        # recovery measurement -- that is drain_time_s, measured from the
        # restoration transition above.
        print("  settling...")
        drain_t0 = time.time()
        expected = {s["client_event_id"] for s in submitted if s["locally_accepted"]}
        drained_at = None
        while time.time() - drain_t0 < args.drain_timeout_s:
            if expected.issubset(journal_seqs(incident_id)):
                drained_at = time.time()
                break
            time.sleep(1.0)
    finally:
        sampler.stop()
        sampler.join(timeout=5.0)
        remove_netem()

    arrived = journal_seqs(incident_id)
    per_regime: dict[str, dict] = {}
    for s in submitted:
        r = per_regime.setdefault(
            s["regime"], {"submitted": 0, "locally_accepted": 0, "reached_journal": 0}
        )
        r["submitted"] += 1
        r["locally_accepted"] += int(s["locally_accepted"])
        r["reached_journal"] += int(s["client_event_id"] in arrived)

    for regime, counts in per_regime.items():
        write_record(
            handle,
            run_id=incident_id,
            scenario="netem_schedule",
            metric_name="phase_delivery",
            value_ms=None,
            timestamp_iso=now_iso(),
            scenario_params={
                "regime": regime,
                "regime_params": REGIMES[regime],
                **counts,
                # Renamed from "delivery_ratio": measured after the final
                # settle, this is always ~1.0 and is the *durability* claim
                # (nothing lost), not a statement about behaviour during the
                # regime. Per-phase within-regime delivery is carried by the
                # phase_complete records.
                "delivered_eventually_ratio": (
                    counts["reached_journal"] / counts["submitted"] if counts["submitted"] else None
                ),
            },
            notes="",
        )

    for sample in sampler.samples:
        write_record(
            handle,
            run_id=incident_id,
            scenario="netem_schedule",
            metric_name="outbox_backlog",
            value_ms=None,
            timestamp_iso=datetime.fromtimestamp(sample["t"], UTC).isoformat(),
            scenario_params={
                "regime": sample["regime"],
                "t_offset_s": round(sample["t"] - t_start, 2),
                "unforwarded": sample["unforwarded"],
            },
            notes="",
        )

    peak = max((s["unforwarded"] for s in sampler.samples), default=0)
    summary = {
        "incident_id": incident_id,
        "schedule": [{"regime": r, "duration_s": d} for r, d in args.schedule],
        "submitted_total": len(submitted),
        "locally_accepted_total": sum(1 for s in submitted if s["locally_accepted"]),
        "reached_journal_total": len(arrived),
        "peak_unforwarded": peak,
        # Recovery: measured from the moment connectivity was restored until
        # every event pending at that instant was journal-visible.
        "drain_time_s": drain_time_s,
        "restored_from_regime": restore_from,
        "pending_at_restore": pending_at_restore,
        # Completeness after the run, not recovery time.
        "settle_time_s": round(drained_at - drain_t0, 2) if drained_at else None,
        "drained": drained_at is not None,
        "per_phase": [phase_within[k] for k in sorted(phase_within)],
        "per_regime": per_regime,
        "environment": env_meta,
    }
    write_record(
        handle,
        run_id=incident_id,
        scenario="netem_schedule",
        metric_name="summary",
        value_ms=None,
        timestamp_iso=now_iso(),
        scenario_params=summary,
        notes="",
    )
    return summary


def parse_schedule(raw: str) -> list[tuple[str, int]]:
    out: list[tuple[str, int]] = []
    for part in raw.split(","):
        name, _, dur = part.strip().partition(":")
        if name not in REGIMES:
            raise SystemExit(f"unknown regime {name!r}; valid: {list(REGIMES)}")
        out.append((name, int(dur)))
    return out


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=int, default=10)
    parser.add_argument("--submit-interval-s", type=float, default=5.0)
    parser.add_argument("--drain-timeout-s", type=float, default=180.0)
    parser.add_argument("--schedule", type=str, default=None,
                        help="e.g. clear:30,mesh_degraded:45,isolated:60,clear:90")
    parser.add_argument("--smoke", action="store_true",
                        help="1 run over a short schedule, as a sanity gate")
    parser.add_argument("--artifact", default=str(DEFAULT_ARTIFACT))
    args = parser.parse_args()
    args.schedule = parse_schedule(args.schedule) if args.schedule else list(DEFAULT_SCHEDULE)
    if args.smoke:
        args.runs = 1
        args.submit_interval_s = 2.0
        args.schedule = [("clear", 10), ("mesh_degraded", 10), ("isolated", 20), ("clear", 25)]
    return args


def main() -> int:
    args = parse_args()
    artifact = Path(args.artifact)
    artifact.parent.mkdir(parents=True, exist_ok=True)
    env_meta = collect_environment()
    total_s = sum(d for _, d in args.schedule)
    print(f"schedule={args.schedule} (~{total_s}s/run) runs={args.runs}")

    summaries = []
    with artifact.open("w", encoding="utf-8") as handle:
        write_record(
            handle,
            run_id="env",
            scenario="netem_schedule",
            metric_name="environment",
            value_ms=None,
            timestamp_iso=now_iso(),
            scenario_params={
                "runs": args.runs,
                "schedule": [{"regime": r, "duration_s": d} for r, d in args.schedule],
                "submit_interval_s": args.submit_interval_s,
            },
            environment=env_meta,
            notes="connectivity-regime schedule; not a mobility model",
        )
        for i in range(args.runs):
            print(f"run {i}...")
            summaries.append(run_schedule(handle, args, env_meta))

    print(json.dumps({"runs": summaries}, indent=2, sort_keys=True, default=str))
    ok = all(s["drained"] and s["reached_journal_total"] == s["locally_accepted_total"] for s in summaries)
    if not ok:
        print("WARNING: at least one run lost events or failed to drain", file=sys.stderr)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    finally:
        remove_netem()
