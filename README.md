# Rescue OIS Reviewer Guide

This repository backs the NCA 2026 paper **Authority-Aligned Linearization
(AAL) for Rescue-Service Incident Response over Intermittent Edge Networks**. It
contains the prototype services, Docker Compose emulation, evaluation harnesses,
CRDT baseline, formal models, generated paper tables/figures, and the LaTeX
paper.

**Reviewers who only want to read the paper:** the compiled, 9-page PDF is
checked in at [`paper/main.pdf`](paper/main.pdf). Nothing needs to be built to
read it.

The core protocol rule is:

> Core owns master data. The current command edge owns authority-bearing
> incident-journal writes. Responders accept field submissions into a durable
> outbox and forward them to the command edge.

The repository is a research artifact, not a production deployment. The measured
path covers the service paths used in Section V of the paper: command-edge
journal serialization, responder outbox forwarding, idempotent replay, fenced
promotion, command-to-core recovery, CRDT-LWW comparison, and bounded formal
safety checks. It does not claim physical Rajant radio behavior, Android
end-to-end validation, measured WireGuard/mTLS overhead, or automatic failover.

## Fast Reviewer Path

To inspect the artifact without rerunning long measurements:

1. Read the paper source in `paper/sections/`, especially
   `paper/sections/04_synchronization_protocol.tex`,
   `paper/sections/05_implementation.tex`, and
   `paper/sections/06_evaluation.tex`.
2. Inspect the generated evaluation artifacts in `paper/data/`, `paper/tables/`,
   and `paper/figures/`.
3. Build the paper from checked-in artifacts:

```bash
cd paper
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
pdfinfo main.pdf
cd ..
```

## Repository Map

| Path | Reviewer use |
| --- | --- |
| `paper/` | LaTeX paper, generated figures/tables, and JSONL evaluation data. |
| `core/` | Regional core services and database migrations. |
| `edge/` | Vehicle-edge services: `ops-api`, `syncd`, local Postgres, outbox, journal, WireGuard/Nginx scaffolding. |
| `scripts/` | Docker stack helpers and AAL evaluation harnesses. |
| `baseline/crdt/` | Hanssen-style operation-based CRDT-LWW baseline service. |
| `baseline/scripts/` | CRDT baseline evaluation harness. |
| `formal/tla/` | TLA+ safety model, strict and weak configs, recorded run notes. |
| `formal/python/` | Hypothesis state-machine tests mirroring the TLA+ safety properties. |
| `docs/` | Architecture notes, ADRs, deployment notes, and runbooks. |
| `tablet/` | Android tablet scaffold; not part of the reported end-to-end evaluation. |
| `baseline-raft/` | Historical/contextual baseline code, not used by the current Section V CRDT comparison. |

## Prerequisites

Install only the tools needed for the path you will run.

- Docker Engine with Docker Compose v2.
- Python 3.11+ on the host for harness scripts; Python 3.12 is used inside the
  service containers. Host scripts need `httpx` and plot generation needs
  `matplotlib`.
- LaTeX (`latexmk`, `pdflatex`, BibTeX) for the paper build.
- Java plus `tla2tools.jar` for TLA+ checks.
- `pytest` and `hypothesis` for `formal/python`.

A minimal host Python setup is:

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install httpx matplotlib pytest hypothesis
```

## Start the AAL Emulation Stack

The paper setup uses one core, one command edge, and three responder edges on the
shared Docker network `rescue-ois-net`.

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
These commands overwrite their corresponding `paper/data/*.jsonl` files.

```bash
python3 scripts/evaluate-pilot.py
python3 scripts/evaluate-command-local-partition.py
python3 scripts/evaluate-fenced-promotion.py --n 5 --writes-per-phase 20
python3 scripts/evaluate-outbox-crash-restart.py
python3 scripts/evaluate-netem-propagation.py
```

What each harness drives:

| Paper cell | Script | Default output |
| --- | --- | --- |
| V-A/V-D/V-F plus throughput/idempotency | `scripts/evaluate-pilot.py` | `paper/data/eval_metrics.jsonl` |
| V-C responder-isolation command commits | `scripts/evaluate-command-local-partition.py` | `paper/data/eval_command_local_partition.jsonl` |
| V-B fenced promotion phases A/B/C | `scripts/evaluate-fenced-promotion.py --n 5 --writes-per-phase 20` | `paper/data/eval_fenced_promotion.jsonl` |
| V-D outbox survives responder DB restart | `scripts/evaluate-outbox-crash-restart.py` | `paper/data/eval_outbox_crash_restart.jsonl` |
| V-D stressed/degraded `tc-netem` propagation | `scripts/evaluate-netem-propagation.py` | `paper/data/eval_netem_propagation.jsonl` |

Important details:

- `evaluate-pilot.py` uses `RUNS_PER_CELL=30` by default. Set
  `RUNS_PER_CELL=1` for a fast sanity run.
- Throughput inside `evaluate-pilot.py` uses 1000 concurrent submissions and
  emits both direct command `/accept/event-batch` and end-to-end responder
  `/api/events` measurements. The first run is a warm-up and is excluded by the
  table generator.
- `evaluate-fenced-promotion.py --n 5 --writes-per-phase 20` produces 300
  attempts total: 100 per phase.
- `evaluate-netem-propagation.py` installs `tc-netem` on the responder and
  command `syncd` containers. If it fails, run `./scripts/dev-down.sh` and start
  a clean stack before retrying.

## Re-run the CRDT-LWW Baseline

The current paper comparison uses the CRDT-LWW baseline under `baseline/crdt`,
not the historical `baseline-raft` stack.

Start the CRDT baseline:

```bash
docker compose -f baseline/docker-compose.yml up -d --build
```

Run the main CRDT baseline cells (`n=30`, throughput target 300). This writes
baseline outputs under `baseline/data/` and copies table inputs into `paper/data/`:

```bash
python3 baseline/scripts/evaluate-crdt-baseline.py \
  --runs 30 \
  --throughput-events 300 \
  --partition-s 60 \
  --partition-runs 1 \
  --output data/eval_crdt_baseline.jsonl
```

Run the 60-second post-quiescence convergence file used by the comparison table
(`n=10` for the long wait row, with only smoke-size values for the other cells in
that file):

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

## Regenerate Paper Tables and Figures

After rerunning data:

```bash
python3 paper/scripts/generate_plots.py
python3 paper/scripts/plot_promotion_cdf.py
python3 paper/scripts/generate_tables.py
```

Generated outputs:

| Generator | Inputs | Outputs |
| --- | --- | --- |
| `paper/scripts/generate_plots.py` | evaluation metrics JSONL in `paper/data/` | `paper/figures/fig_recovery.pdf` |
| `paper/scripts/plot_promotion_cdf.py` | fenced-promotion JSONL in `paper/data/` | `paper/figures/fig_promotion_cost.pdf`, `paper/data/promotion_summary.tex` |
| `paper/scripts/generate_tables.py` | evaluation JSONL files in `paper/data/` | `paper/tables/tab_evaluation.tex`, `paper/tables/tab_crdt_comparison.tex` |

Then rebuild the paper:

```bash
cd paper
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
pdfinfo main.pdf
cd ..
```

## Smoke Run Instead of Full Reproduction

A reviewer who only wants to validate wiring can run a small destructive smoke
pass. These commands do not reproduce paper statistics.

```bash
RESPONDERS=3 ./scripts/dev-up.sh
./scripts/run-migrations.sh
./scripts/run-migrations.sh edge

RUNS_PER_CELL=1 python3 scripts/evaluate-pilot.py
python3 scripts/evaluate-command-local-partition.py --attempts 3 --partition-s 2
python3 scripts/evaluate-fenced-promotion.py --n 1 --writes-per-phase 3
python3 scripts/evaluate-outbox-crash-restart.py --events 5
python3 scripts/evaluate-netem-propagation.py --smoke

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

The paper and repository intentionally separate implemented evidence from
non-claims:

- The service path sequences and fences incident-journal writes, but semantic
  rejection for application-level status/delete conflicts is not implemented in
  the measured service path.
- Promotion is operator-initiated and single-edge in the service-path harness;
  multi-edge operator races are model-level or future work.
- The Android tablet directory is a scaffold; Section V uses Python/tablet stubs
  and service APIs.
- The Docker evaluation is single-host emulation with `tc-netem`, not a physical
  mesh or measured WireGuard/mTLS deployment.

## Troubleshooting

- If Docker names or networks collide, run `./scripts/dev-down.sh` and retry.
- If `paper/scripts/generate_tables.py` reports a missing file, confirm the
  expected JSONL files exist in `paper/data/`.
- If netem results look stuck, remove the stack with `./scripts/dev-down.sh`;
  the netem harness cleans up on normal exit, but a killed run can leave qdiscs
  in a bad state.
- If the paper build reports changed references, rerun `latexmk` once more.

## License

This project is licensed under the Apache License 2.0. See `LICENSE`.
