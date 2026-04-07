# CLAUDE.md

## Project Overview

Rescue OIS is a three-tier system (regional core → vehicle edge → field tablet) for Swedish rescue services. Core owns master data. Command vehicle owns live incident state. Responders and tablets queue and forward edits.

## Tech Stack

- Core services: Python 3.12+, FastAPI, PostgreSQL 16 + PostGIS 3.5, Martin, Nginx
- Edge services: Same stack as core, subset of services
- Tablet app: Kotlin, Jetpack Compose, MapLibre Native Android, Room (SQLite)
- Infra: Docker Compose (core/edge), Ansible (provisioning), WireGuard (overlay)

## Conventions

- Python: use `pyproject.toml` with ruff for linting, pytest for tests
- Kotlin: standard Android project layout, ktlint
- SQL migrations: numbered, forward-only, plain SQL
- All services expose health checks at `GET /health`
- Config via environment variables, never hardcoded

## Key Architectural Rules

1. Single incident writer: only the command vehicle K430 writes to incident_journal/incident_state
2. Responder K430s only write to device_outbox, then forward to command
3. Tablets never talk to the mesh or internet directly — only to their local K430 over HTTPS
4. No user VLANs are stretched across the Rajant mesh
5. PostgreSQL logical replication is one-way (core → edge) for master data only

## Running Locally

```
./scripts/dev-up.sh    # starts core stack via docker-compose
./scripts/run-migrations.sh
```

## Testing

```
cd core/feed-importer && pytest
cd core/sync-api && pytest
cd edge/ops-api && pytest
cd edge/syncd && pytest
```
