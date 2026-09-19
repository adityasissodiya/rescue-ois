# Rescue OIS Reference Material

This repository backs the NCA 2026 paper **Authority-Aligned Linearization
(AAL) for Rescue-Service Incident Response over Intermittent Edge Networks**. It
contains the prototype services, Docker Compose emulation, evaluation harnesses,
CRDT baseline, formal models, architecture notes, deployment notes, and tablet
scaffold. The manuscript source and PDF are submitted separately and are not part
of this reference-material repository.

The core protocol rule is:

> Core owns master data. The current command edge owns authority-bearing
> incident-journal writes. Responders accept field submissions into a durable
> outbox and forward them to the command edge.

The repository is a research artifact, not a production deployment. The measured
path covers the service paths used by the evaluation: command-edge journal
serialization, responder outbox forwarding, idempotent replay, fenced promotion,
command-to-core recovery, CRDT-LWW comparison, and bounded formal safety checks.
It does not claim physical Rajant radio behavior, Android end-to-end validation,
measured WireGuard/mTLS overhead, or automatic failover.

## Fast Reviewer Path

To inspect the artifact without rerunning long measurements:

1. Read the architecture and protocol notes in `docs/architecture/` and
   `docs/adr/`.
2. Inspect the service implementations under `core/`, `edge/`, and `baseline/`.
3. Inspect the formal models under `formal/`.
4. Use the smoke run below if you only want to validate wiring.

## Repository Map

| Path | Reviewer use |
| --- | --- |
| `core/` | Regional core services and database migrations. |
| `edge/` | Vehicle-edge services: `ops-api`, `syncd`, local Postgres, outbox, journal, WireGuard/Nginx scaffolding. |
| `scripts/` | Docker stack helpers and AAL evaluation harnesses. |
| `baseline/crdt/` | Hanssen-style operation-based CRDT-LWW baseline service. |
| `baseline/scripts/` | CRDT baseline evaluation harness. |
| `baseline-raft/` | Three-voter Raft baseline (Go `raftd`). Drives the leader-isolation comparison via `scripts/evaluate-raft-authority.py`. |
| `formal/tla/` | TLA+ safety model, strict and weak configs, recorded run notes. |
| `formal/python/` | Hypothesis state-machine tests mirroring the TLA+ safety properties. |
| `docs/` | Architecture notes, ADRs, deployment notes, and runbooks. |
| `tablet/` | Android tablet scaffold; not part of the reported end-to-end evaluation. |
| `ui_kits/` | Tablet UI click-through prototype. |
| `preview/` | Static visual previews used during design. |

## Prerequisites

Install only the tools needed for the path you will run.

- Docker Engine with Docker Compose v2.
- Python 3.11+ on the host for harness scripts; Python 3.12 is used inside the
  service containers. Host scripts need `httpx` and plot generation needs
  `matplotlib` only if you run local plotting scripts of your own.
- Java plus `tla2tools.jar` for TLA+ checks.
- `pytest` and `hypothesis` for `formal/python`.

A minimal host Python setup is:

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install httpx matplotlib pytest hypothesis
```

## Start the AAL Emulation Stack

The evaluation setup uses one core, one command edge, and three responder edges
on the shared Docker network `rescue-ois-net`.

```bash
RESPONDERS=3 ./scripts/dev-up.sh
./scripts/run-migrations.sh
./scripts/run-migrations.sh edge
```

Default host endpoints:

| Service | URL |
| --- | --- |
| Core `sync-api` | `http://127.0.0.1:18000` |
| Command edge `ops-api` | `http://127.0.0.1:18080` |
| Command edge `syncd` | `http://127.0.0.1:18081` |
| Responder 1 `ops-api` | `http://127.0.0.1:18101` |
| Responder 1 `syncd` | `http://127.0.0.1:18201` |

Stop and remove the emulation stack:

```bash
./scripts/dev-down.sh
```

The evaluation scripts reset tables and may stop/restart containers. Do not run
them against a stack that contains data you want to keep.

## Re-run the AAL Evaluation Harnesses

Run from the repository root after starting the stack and applying migrations.
These commands write generated JSONL files under `artifacts/data/` by default.
The `artifacts/` directory is ignored by Git.

```bash
python3 scripts/evaluate-pilot.py
python3 scripts/evaluate-command-local-partition.py
python3 scripts/evaluate-fenced-promotion.py --n 5 --writes-per-phase 20
python3 scripts/evaluate-outbox-crash-restart.py
python3 scripts/evaluate-netem-propagation.py
python3 scripts/evaluate-netem-schedule.py
python3 scripts/evaluate-fleet-scaling.py
```

`evaluate-raft-authority.py` is listed with the Raft baseline below, because it
drives `baseline-raft/` rather than the AAL stack.

What each harness drives:

| Evaluation cell | Script | Default output |
| --- | --- | --- |
| Propagation, recovery, throughput, idempotency | `scripts/evaluate-pilot.py` | `artifacts/data/eval_metrics.jsonl` |
| Responder-isolation command commits | `scripts/evaluate-command-local-partition.py` | `artifacts/data/eval_command_local_partition.jsonl` |
| Fenced promotion phases A/B/C | `scripts/evaluate-fenced-promotion.py --n 5 --writes-per-phase 20` | `artifacts/data/eval_fenced_promotion.jsonl` |
| Outbox survives responder DB restart | `scripts/evaluate-outbox-crash-restart.py` | `artifacts/data/eval_outbox_crash_restart.jsonl` |
| Stressed/degraded `tc-netem` propagation | `scripts/evaluate-netem-propagation.py` | `artifacts/data/eval_netem_propagation.jsonl` |
| Transitions between connectivity regimes | `scripts/evaluate-netem-schedule.py` | `artifacts/data/eval_netem_schedule.jsonl` |
| Propagation and journal throughput vs fleet size | `scripts/evaluate-fleet-scaling.py` | `artifacts/data/eval_fleet_scaling.jsonl` |

Important details:

- `evaluate-pilot.py` uses `RUNS_PER_CELL=30` by default. Set
  `RUNS_PER_CELL=1` for a fast sanity run.
- Throughput inside `evaluate-pilot.py` uses 1000 concurrent submissions and
  emits both direct command `/accept/event-batch` and end-to-end responder
  `/api/events` measurements. The first run is a warm-up and is excluded from
  downstream summary calculations.
- `evaluate-fenced-promotion.py --n 5 --writes-per-phase 20` produces 300
  attempts total: 100 per phase.
- `evaluate-netem-propagation.py` installs `tc-netem` on the responder and
  command `syncd` containers. If it fails, run `./scripts/dev-down.sh` and start
  a clean stack before retrying.
- `evaluate-netem-schedule.py` runs one continuous submission stream while
  walking a schedule of connectivity regimes inside a single run, and attributes
  every event to the regime in force when it was submitted. The default schedule
  is `clear:30,mesh_stressed:45,mesh_degraded:45,isolated:60,clear:90` (seconds);
  override it with `--schedule`. Ten runs take roughly 45 minutes. Impairment is
  destination-filtered (`prio` + `u32 match ip dst`), not a blanket root qdisc,
  so the edge's own Postgres path is not impaired -- see the note below.
- `evaluate-fleet-scaling.py` sweeps `--sizes` (default `1,3,5,10`) by bringing
  responder edges up and down, so it needs headroom for roughly 230 MiB per
  edge. It projects that cost against **host** memory before each bring-up and
  refuses an unaffordable fleet with a recorded `ceiling` record rather than
  risking an out-of-memory kill mid-run. `docker info` and `docker stats` report
  the WSL2 guest, not the host, so on Docker Desktop they will look comfortable
  while the host starves. It also applies edge migrations itself: `dev-up.sh`
  does not, and a fresh edge otherwise comes up with an empty database while
  still reporting healthy.
- Its percentiles are **arrival-curve** percentiles -- the time at which the
  journal had accepted k% of the batch -- not a per-event latency distribution,
  because `incident.journal.created_at` is client-supplied. Resolution is one
  poll interval (`--poll-interval-s`, default 250 ms).
- Its throughput figures are not comparable with the `evaluate-pilot.py`
  saturation rate. A 200-event batch is dominated by fixed per-event latency
  rather than serializer throughput; both are lower bounds on different axes.

A note on `tc` scope that cost real debugging time: a **root qdisc** impairs all
egress from the container, including its own Postgres connection over the same
bridge, which silently inflates any latency measured through that container. Use
a destination-filtered qdisc (`prio` + `u32 match ip dst`), as
`scripts/inject-partition.sh wan` and `evaluate-netem-schedule.py` both do,
whenever the impaired container has a co-located database.

## Re-run the CRDT-LWW Baseline

The semantic falsification comparison uses the CRDT-LWW baseline under
`baseline/crdt`. The separate leader-isolation comparison uses `baseline-raft/`
and is documented in the next section.

Start the CRDT baseline:

```bash
docker compose -f baseline/docker-compose.yml up -d --build
```

Run the main CRDT baseline cells (`n=30`, throughput target 300):

```bash
python3 baseline/scripts/evaluate-crdt-baseline.py \
  --runs 30 \
  --throughput-events 300 \
  --partition-s 60 \
  --partition-runs 1 \
  --output data/eval_crdt_baseline.jsonl
```

Run the 60-second post-quiescence convergence case (`n=10` for the long-wait
comparison, with only smoke-size values for the other cells in that file):

```bash
python3 baseline/scripts/evaluate-crdt-baseline.py \
  --runs 1 \
  --throughput-events 30 \
  --partition-s 60 \
  --partition-runs 10 \
  --output data/eval_crdt_partition_n10.jsonl
```

Stop the CRDT baseline:

```bash
docker compose -f baseline/docker-compose.yml down -v
```

The CRDT harness models four FastAPI replicas (`a`, `b`, `c`, `core`) using an
operation-based LWW element set with physical-clock timestamps. It has no
background gossip; convergence is driven by harness-triggered `full_sync()`.

## Re-run the Raft Leader-Isolation Baseline

This is the producer for the paper's "Leader-minority partition" row. It is a
separate script from `scripts/evaluate-raft-baseline.py` on purpose: that
harness has three scenarios (propagation, follower catch-up, quorum loss), none
of which isolates the *leader*, and it writes different scenario names to a
different artifact. Conflating them would make the provenance worse, not better.

Start the three-voter Raft stack:

```bash
cd baseline-raft && docker compose -p baseline-raft up -d --build && cd ..
```

Run the harness (a leader must be electable on `127.0.0.1:18001-18003`):

```bash
python3 scripts/evaluate-raft-authority.py --runs 12 --writes-per-run 5
```

| Evaluation cell | Script | Default output |
| --- | --- | --- |
| Leader-minority partition, both arrival phases | `scripts/evaluate-raft-authority.py --runs 12` | `artifacts/data/eval_raft_baseline.jsonl` |

Stop it:

```bash
cd baseline-raft && docker compose -p baseline-raft down -v && cd ..
```

What it does, and why it does it that way:

- Each run severs the current leader L0 from its peers with
  `docker network disconnect`, then probes L0 with a write **twice**: once
  during the election window and once after the new leader L1 has been elected.
  Both arrival times are reported. The two phases behave completely differently
  -- in-window the write stalls and fails with HTTP 500 `leadership lost while
  committing log`; post-step-down it is refused instantly with HTTP 503
  `not leader` -- and reporting only the first would be cherry-picking Raft's
  worst phase.
- `l0_isolated_write_*` is bound to the **in-window** probe, which is the phase
  the paper reports and `generate_raft_table.py` consumes. The post-step-down
  reading is recorded alongside as `l0_poststepdown_write_*`. The schema the
  table generator reads is unchanged.
- **The probe runs inside L0 over its own loopback** (`docker exec ... curl
  127.0.0.1:8000`), not from the host. `docker network disconnect` tears the
  published-port forward down immediately, so a host-side probe of an isolated
  container can only ever record "unreachable" -- it measures the probe's own
  network path, not Raft. Probing from inside is also the better deployment
  analogue: the client sits on the isolated vehicle's own network, not across
  the break. `curl` is present in the `raftd` image; `tc` is not, so in-container
  traffic shaping is not an option here.
- The election timer starts at `disconnect` and the in-window probe runs
  concurrently with the election, so the probe's own duration is not added to
  `time_to_new_leader_ms`.
- `summarise()` **raises** if any in-window probe was unreachable rather than
  letting it through. An unreachable probe would quietly turn the isolated-write
  column into a statement about connectivity instead of about Raft.
- Election timings are hardware- and Docker-version-dependent and will not match
  the paper's to the millisecond. The qualitative results -- 12/12 runs elect an
  L1 distinct from L0, every in-window isolated write fails -- do reproduce.

## Smoke Run Instead of Full Reproduction

A reviewer who only wants to validate wiring can run a small destructive smoke
pass. These commands do not reproduce evaluation statistics.

```bash
RESPONDERS=3 ./scripts/dev-up.sh
./scripts/run-migrations.sh
./scripts/run-migrations.sh edge

RUNS_PER_CELL=1 python3 scripts/evaluate-pilot.py
python3 scripts/evaluate-command-local-partition.py --attempts 3 --partition-s 2
python3 scripts/evaluate-fenced-promotion.py --n 1 --writes-per-phase 3
python3 scripts/evaluate-outbox-crash-restart.py --events 5
python3 scripts/evaluate-netem-propagation.py --smoke
python3 scripts/evaluate-netem-schedule.py --smoke
python3 scripts/evaluate-fleet-scaling.py --smoke

./scripts/dev-down.sh
```

## Formal-Methods Checks

TLA+ model checking requires Java and `tla2tools.jar`:

```bash
cd formal/tla
java -jar "$TLA_TOOLS_JAR" -workers auto -config RescueOIS_small.cfg RescueOIS.tla
java -jar "$TLA_TOOLS_JAR" -workers auto -config RescueOIS_medium.cfg RescueOIS.tla
java -jar "$TLA_TOOLS_JAR" -workers auto -config RescueOIS_large.cfg RescueOIS.tla
java -jar "$TLA_TOOLS_JAR" -workers auto -config RescueOIS_weak.cfg RescueOIS.tla
java -jar "$TLA_TOOLS_JAR" -workers auto -config RescueOIS_weak_epoch.cfg RescueOIS.tla
java -jar "$TLA_TOOLS_JAR" -workers auto -config RescueOIS_weak_journal.cfg RescueOIS.tla
cd ../..
```

Expected behavior: strict configs verify; weak configs fail by design and expose
counterexamples. Recorded run notes live in `formal/tla/RUNS.md` and
`formal/tla/weak_counterexample.md`.

Run the Python Hypothesis mirrors:

```bash
cd formal/python
python3 -m pip install -e .
pytest
cd ../..
```

Opt-in real-stack tests require a running AAL Docker stack:

```bash
cd formal/python
RESCUE_OIS_REAL_STACK=1 pytest tests/test_against_real.py
cd ../..
```

## Current Evidence Boundaries

The manuscript and repository intentionally separate implemented evidence from
non-claims:

- The service path sequences and fences incident-journal writes, but semantic
  rejection for application-level status/delete conflicts is not implemented in
  the measured service path.
- Promotion is operator-initiated and single-edge in the service-path harness;
  multi-edge operator races are model-level or future work.
- The Android tablet directory is a scaffold; the evaluation uses Python/tablet
  stubs and service APIs.
- The Docker evaluation is single-host emulation with `tc-netem`, not a physical
  mesh or measured WireGuard/mTLS deployment.
- `evaluate-netem-schedule.py` is a connectivity-regime schedule, not a mobility
  model. No vehicle positions, path loss or RAN topology are simulated. The
  regime durations are literature-informed; the transitions are synthetic, which
  is the point -- a reviewer can re-run exactly them.
- The fleet sweep stops at ten responder edges because that is where a 16 GB
  host runs out of memory, not where AAL runs out of headroom. It is a measured
  limit of the test bed, not a scaling result.

## Troubleshooting

- If Docker names or networks collide, run `./scripts/dev-down.sh` and retry.
- If an evaluation script reports a missing output directory, confirm
  `artifacts/data/` can be created by your user.
- If netem results look stuck, remove the stack with `./scripts/dev-down.sh`;
  the netem harness cleans up on normal exit, but a killed run can leave qdiscs
  in a bad state.
- If a harness that shells out to `./scripts/*.sh` dies with
  `$'': command not found`, your checkout has CRLF line endings. `.gitattributes`
  pins `*.sh text eol=lf`; re-clone or run `git add --renormalize .`.
- On Windows, Python's `subprocess` resolves a bare `bash` to WSL's bash, whose
  distro usually has no Docker integration (`The command 'docker' could not be
  found in this WSL 2 distro`). `shutil.which` does not predict this. The
  harnesses that need a shell resolve the interpreter explicitly and verify it
  can reach `docker` before using it.
- A fleet run killed with no traceback is almost certainly the host
  out-of-memory killer, not a bug. `docker info` and `docker stats` describe the
  WSL2 guest and will read comfortable while the host starves; check host memory
  separately. `evaluate-fleet-scaling.py` projects the cost before bring-up and
  refuses rather than being killed.
- If a newly created responder edge reports healthy and accepts events but its
  journal count comes up short, its database has no schema: `dev-up.sh` does not
  run migrations. Note that a blanket `./scripts/run-migrations.sh edge` is not a
  fix -- only some edge migrations are `IF NOT EXISTS` guarded under
  `ON_ERROR_STOP=1`, so re-applying them to an already-migrated edge fails.

## License

This project is licensed under the Apache License 2.0. See `LICENSE`.
