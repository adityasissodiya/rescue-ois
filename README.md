# Rescue OIS

Rescue OIS is a research prototype for authority-aligned synchronization in
rescue-service incident response. It studies how authority-bearing incident
events can be linearized at the current command authority across
intermittently connected regional, vehicle, and tablet tiers, while
non-authority data remains locally useful and forwardable.

The core design rule is:

> Core owns master data. The command vehicle owns live incident state.
> Responders and tablets only queue and forward field edits.

This repository contains the prototype services, local Docker emulation,
formal safety models, evaluation harnesses, a Raft comparison baseline, Android
tablet scaffold, and the LaTeX paper sources.

This prototype evaluates authority-aligned synchronization for rescue-service
incident data. It is not a general-purpose offline database and not a
production mesh deployment. The implemented path covers responder outbox
forwarding, command-side idempotent sequencing, command-to-core backfill,
duplicate replay, selected partition behavior, and model-level promotion
safety. Physical mesh behavior, Android tablet persistence, mTLS/WireGuard
overhead, service-level durable command epochs, and full crash-boundary
validation remain outside the measured path.

## Status

This is a research and submission repository, not a production deployment. The
local emulation exercises the protocol and measurements used by the paper, but
the full operational stack still requires production hardening around mTLS,
device management, deployment automation, physical mesh testing, and
field-validation procedures.

For NCA-style double-blind submission work, do not assume the whole repository
is an anonymous artefact. Some planning and submission-side documents under the
root and `docs/` may contain author-side information. Re-run the anonymisation
grep for any bundle before sharing it with reviewers.

## Architecture

Rescue OIS uses three tiers:

- `Regional Core`: authoritative master-data platform, publication pipeline,
  tile/package serving, sync API, and audit receiver.
- `Vehicle Edge`: per-vehicle local services. One edge acts as command and
  sequences the incident journal; responders cache data and forward queued
  field edits.
- `Field Tablet`: Android leaf client that talks only to the local vehicle
  edge over HTTPS and keeps a local offline store.

The mesh is treated as transit only. User VLANs are not stretched across
vehicles, and live incident-state writes are sequenced by exactly one command
node at a time.

See [docs/architecture/README.md](docs/architecture/README.md) for the detailed
architecture overview, network model, security model, and protocol write-up.

## Repository Layout

| Path | Purpose |
| --- | --- |
| `core/` | Regional services: PostGIS, Martin, GeoServer, Nginx, `sync-api`, `audit-api`, `feed-importer`, and `publisher`. |
| `edge/` | Vehicle services: local PostGIS, `ops-api`, `syncd`, package cache, audit forwarder, Nginx, WireGuard and firewall templates. |
| `tablet/` | Kotlin / Jetpack Compose / MapLibre Android tablet scaffold. |
| `formal/` | TLA+ model and Python Hypothesis state-machine tests for the protocol safety properties. |
| `baseline-raft/` | Three-voter `hashicorp/raft` baseline used for the paper comparison. |
| `scripts/` | Local emulation, migration, partition injection, promotion, and evaluation scripts. |
| `paper/` | IEEE/NCA paper source, bibliography, generated tables, figures, and measurement data. |
| `docs/` | Architecture, deployment notes, runbooks, ADRs, and submission-side checklist. |
| `infra/` | Ansible, router, and mesh-device configuration templates. |
| `ui_kits/`, `preview/` | Conceptual design-system and tablet UI preview artefacts. |

## Prerequisites

The full repository spans several toolchains. Install only the pieces needed for
the task you are running.

- Docker Engine with Docker Compose v2
- Python 3.11+ for evaluation scripts; `httpx` is required for the harnesses
  and `matplotlib` for plot generation
- LaTeX with `latexmk`, `pdflatex`, and BibTeX for the paper
- Go 1.21+ for the Raft baseline
- Java plus `tla2tools.jar` for TLA+ model checking
- Android Studio or Gradle/JDK for the tablet app

## Local Emulation

Start one regional core, one command edge, and one responder edge:

```bash
./scripts/dev-up.sh
./scripts/run-migrations.sh
./scripts/run-migrations.sh edge
```

Start with more responder vehicles:

```bash
RESPONDERS=3 ./scripts/dev-up.sh
./scripts/run-migrations.sh
./scripts/run-migrations.sh edge
```

Default host ports used by the emulation include:

- Core `sync-api`: `http://127.0.0.1:18000`
- Command edge `ops-api`: `http://127.0.0.1:18080`
- Command edge `syncd`: `http://127.0.0.1:18081`
- First responder `ops-api`: `http://127.0.0.1:18101`
- First responder `syncd`: `http://127.0.0.1:18201`

Stop and remove the local emulation:

```bash
./scripts/dev-down.sh
```

## Evaluation Harness

The main prototype evaluation drives bootstrap latency, field-edit
propagation, WAN recovery, throughput, and idempotency scenarios against the
running Docker emulation.

The separate command-partition harness measures only command-originated writes
submitted directly to the implemented command `syncd` `/accept/event-batch`
path while responder `syncd` is isolated. It is not an end-to-end tablet or
physical mesh measurement.

```bash
./scripts/dev-up.sh
./scripts/run-migrations.sh
./scripts/run-migrations.sh edge
python3 scripts/evaluate-pilot.py
python3 scripts/evaluate-command-local-partition.py
python3 paper/scripts/generate_plots.py
python3 paper/scripts/generate_tables.py
```

The canonical output is `paper/data/eval_metrics.jsonl`. Generated paper
outputs include `paper/figures/fig_recovery.pdf` and
`paper/tables/tab_evaluation.tex`.

Do not hand-edit measured data files or generated tables. Rerun the harnesses
and generator scripts instead.

## Raft Baseline

The Raft baseline is a deliberately small comparison target for the paper. It
mirrors only the journal-commit path and omits the Rescue OIS outbox, audit,
promotion, mTLS, tile, package, and durable-storage machinery.

```bash
docker network inspect rescue-ois-net >/dev/null 2>&1 || docker network create rescue-ois-net
docker compose -p baseline-raft -f baseline-raft/docker-compose.yml up -d --build
(cd baseline-raft && go build ./...)
python3 scripts/evaluate-raft-baseline.py
python3 paper/scripts/generate_baseline_table.py
docker compose -p baseline-raft -f baseline-raft/docker-compose.yml down
```

Run the evaluator and table generator from the repository root. The baseline
HTTP APIs are exposed on `18001`, `18002`, and `18003`.

The canonical output is `paper/data/eval_metrics_raft.jsonl`, with the
comparison table generated at `paper/tables/tab_baseline.tex`.

## Formal Verification

The adopted promotion protocol is checked in TLA+ and mirrored by Python
property tests.

Python state-machine tests:

```bash
cd formal/python
pip install -e .
pytest
```

Optional real-stack property tests:

```bash
./scripts/dev-up.sh
cd formal/python
RESCUE_OIS_REAL_STACK=1 pytest tests/test_against_real.py
```

TLA+ model checking:

```bash
cd formal/tla
java -jar "$TLA_TOOLS_JAR" -workers auto -config RescueOIS_strict.cfg RescueOIS.tla
java -jar "$TLA_TOOLS_JAR" -workers auto -config RescueOIS_weak.cfg RescueOIS.tla
java -jar "$TLA_TOOLS_JAR" -workers auto -config RescueOIS_weak_journal.cfg RescueOIS.tla
```

The strict configuration is expected to verify the adopted safety invariants.
The weak configurations are expected to produce counterexamples that show why
manual, authority-preserving promotion is required.

## Paper Build

Build the paper:

```bash
cd paper
latexmk -pdf -interaction=nonstopmode main.tex
```

Useful pre-submission checks from the repository root:

```bash
grep -c "Citation .* undefined" paper/main.log
grep -c "Reference .* undefined" paper/main.log
grep -c "% verify" paper/refs.bib
pdfinfo paper/main.pdf
```

Before any double-blind submission, also run an anonymisation scan over the
submitted paper and artefact tree, then inspect the PDF manually.

## Tablet App

Build and test the Android tablet scaffold:

```bash
cd tablet
./gradlew assembleDebug
./gradlew test
```

The tablet app is intended to talk only to its local vehicle edge endpoint and
to render operational maps from local/offline tile data.

## Operational Documentation

- [docs/architecture/README.md](docs/architecture/README.md) - three-tier
  architecture overview
- [docs/architecture/sync-protocol.md](docs/architecture/sync-protocol.md) -
  protocol flows
- [docs/architecture/network-topology.md](docs/architecture/network-topology.md)
  - IP plan, VLANs, and firewall model
- [docs/architecture/security-model.md](docs/architecture/security-model.md) -
  security boundaries and identity model
- [docs/runbooks/](docs/runbooks/) - incident bootstrap, command failover, and
  device revocation procedures
- [docs/adr/](docs/adr/) - architecture decision records

## License

This project is licensed under the Apache License 2.0. See [LICENSE](LICENSE).
