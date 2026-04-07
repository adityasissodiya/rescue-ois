# Project Scaffold Plan: Rescue OIS

## Purpose

This document is a specification for Claude Code to scaffold a GitHub repository for the **Resilient Operational Information System (OIS) for Rescue Services** — a map-centric, offline-first digital platform replacing paper-based incident planning for Swedish rescue services.

Read this entire file before creating anything. Then execute the scaffold in the order specified.

---

## Repository Name

`rescue-ois`

---

## Top-Level Structure

```
rescue-ois/
├── .github/
│   ├── workflows/
│   │   ├── ci.yml
│   │   └── release.yml
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug_report.md
│   │   └── feature_request.md
│   ├── pull_request_template.md
│   └── CODEOWNERS
├── docs/
│   ├── architecture/
│   │   ├── README.md              # Architecture overview (three-tier model)
│   │   ├── network-topology.md    # IP plan, VLANs, firewall matrix
│   │   ├── sync-protocol.md       # All 6 sync flows
│   │   └── security-model.md      # VLAN isolation, WireGuard, Knox, audit
│   ├── deployment/
│   │   ├── core-setup.md          # cop-core-a/b provisioning
│   │   ├── vehicle-edge-setup.md  # K430 + RUTX50 + Hawk per vehicle
│   │   ├── tablet-enrollment.md   # Knox Manage + app sideload
│   │   └── mesh-commissioning.md  # Rajant Hawk/Sparrow + BC|Commander
│   ├── runbooks/
│   │   ├── incident-bootstrap.md
│   │   ├── command-failover.md
│   │   └── device-revocation.md
│   └── adr/
│       ├── 0001-single-incident-writer.md
│       ├── 0002-no-vlans-across-mesh.md
│       ├── 0003-pmtiles-over-mbtiles.md
│       └── template.md
├── core/
│   ├── docker-compose.yml
│   ├── nginx/
│   │   └── nginx.conf
│   ├── feed-importer/
│   │   ├── src/
│   │   │   ├── main.py
│   │   │   ├── importers/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── lantmateriet.py
│   │   │   │   ├── smhi.py
│   │   │   │   ├── trafikverket.py
│   │   │   │   └── naturvardsverket.py
│   │   │   └── common/
│   │   │       ├── __init__.py
│   │   │       ├── db.py
│   │   │       └── geo.py
│   │   ├── tests/
│   │   │   └── test_importers.py
│   │   ├── Dockerfile
│   │   ├── pyproject.toml
│   │   └── README.md
│   ├── publisher/
│   │   ├── src/
│   │   │   ├── main.py
│   │   │   ├── pipeline.py        # staging → master → build → publish
│   │   │   ├── pmtiles_builder.py
│   │   │   ├── manifest.py        # manifest.json + sha256sum.txt
│   │   │   └── attachments.py     # tar.zst bundler
│   │   ├── tests/
│   │   │   └── test_pipeline.py
│   │   ├── Dockerfile
│   │   ├── pyproject.toml
│   │   └── README.md
│   ├── sync-api/
│   │   ├── src/
│   │   │   ├── main.py
│   │   │   ├── routes/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── sync.py        # /sync/*
│   │   │   │   ├── tiles.py       # /tiles/*
│   │   │   │   └── packages.py    # /packages/*
│   │   │   ├── auth.py
│   │   │   └── models.py
│   │   ├── tests/
│   │   │   └── test_sync.py
│   │   ├── Dockerfile
│   │   ├── pyproject.toml
│   │   └── README.md
│   ├── audit-api/
│   │   ├── src/
│   │   │   ├── main.py
│   │   │   ├── routes.py
│   │   │   └── models.py
│   │   ├── tests/
│   │   │   └── test_audit.py
│   │   ├── Dockerfile
│   │   ├── pyproject.toml
│   │   └── README.md
│   ├── db/
│   │   └── migrations/
│   │       ├── 001_init_schema.sql
│   │       ├── 002_master_tables.sql
│   │       ├── 003_incident_tables.sql
│   │       ├── 004_audit_tables.sql
│   │       └── README.md
│   └── wireguard/
│       ├── wg0-core.conf.template
│       └── README.md
├── edge/
│   ├── docker-compose.yml
│   ├── nginx/
│   │   └── nginx.conf
│   ├── ops-api/
│   │   ├── src/
│   │   │   ├── main.py
│   │   │   ├── routes/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── api.py          # /api/bootstrap, /api/search
│   │   │   │   ├── tiles.py        # /tiles/*
│   │   │   │   └── files.py        # /files/*
│   │   │   ├── auth.py
│   │   │   ├── models.py
│   │   │   └── incident.py         # incident journal / state (command role)
│   │   ├── tests/
│   │   │   ├── test_api.py
│   │   │   └── test_incident.py
│   │   ├── Dockerfile
│   │   ├── pyproject.toml
│   │   └── README.md
│   ├── syncd/
│   │   ├── src/
│   │   │   ├── main.py
│   │   │   ├── pull.py             # pull from core (baseline sync)
│   │   │   ├── push.py             # push outbox to command (responder role)
│   │   │   ├── accept.py           # accept & sequence events (command role)
│   │   │   ├── forward.py          # forward journal to core (command role)
│   │   │   ├── outbox.py           # device_outbox management
│   │   │   └── config.py           # role flag: command | responder
│   │   ├── tests/
│   │   │   ├── test_pull.py
│   │   │   ├── test_push.py
│   │   │   └── test_accept.py
│   │   ├── Dockerfile
│   │   ├── pyproject.toml
│   │   └── README.md
│   ├── package-cache/
│   │   ├── src/
│   │   │   ├── main.py
│   │   │   └── cache.py            # local PMTiles/attachment cache
│   │   ├── Dockerfile
│   │   ├── pyproject.toml
│   │   └── README.md
│   ├── audit-forwarder/
│   │   ├── src/
│   │   │   ├── main.py
│   │   │   └── forwarder.py        # batch & forward audit entries to core
│   │   ├── Dockerfile
│   │   ├── pyproject.toml
│   │   └── README.md
│   ├── db/
│   │   └── migrations/
│   │       ├── 001_edge_schema.sql
│   │       ├── 002_outbox.sql
│   │       ├── 003_incident_journal.sql  # command role only
│   │       └── README.md
│   ├── wireguard/
│   │   ├── wg0-edge.conf.template
│   │   └── README.md
│   └── nftables/
│       ├── nftables.conf.template
│       └── README.md
├── tablet/
│   ├── app/
│   │   ├── build.gradle.kts
│   │   └── src/
│   │       ├── main/
│   │       │   ├── kotlin/
│   │       │   │   └── se/ltu/rescueois/
│   │       │   │       ├── RescueOisApp.kt
│   │       │   │       ├── ui/
│   │       │   │       │   ├── MapScreen.kt
│   │       │   │       │   ├── SiteDetailScreen.kt
│   │       │   │       │   ├── IncidentScreen.kt
│   │       │   │       │   └── SyncStatusBar.kt
│   │       │   │       ├── data/
│   │       │   │       │   ├── local/
│   │       │   │       │   │   ├── AppDatabase.kt
│   │       │   │       │   │   ├── SiteDao.kt
│   │       │   │       │   │   ├── IncidentDao.kt
│   │       │   │       │   │   └── TileCache.kt
│   │       │   │       │   └── remote/
│   │       │   │       │       ├── EdgeApiClient.kt
│   │       │   │       │       └── SyncManager.kt
│   │       │   │       ├── domain/
│   │       │   │       │   ├── Site.kt
│   │       │   │       │   ├── Incident.kt
│   │       │   │       │   ├── HazardInfo.kt
│   │       │   │       │   └── SyncState.kt
│   │       │   │       └── map/
│   │       │   │           ├── MapLibreWrapper.kt
│   │       │   │           ├── OfflineTileProvider.kt
│   │       │   │           └── LayerManager.kt
│   │       │   ├── res/
│   │       │   │   └── values/
│   │       │   │       └── strings.xml
│   │       │   └── AndroidManifest.xml
│   │       └── test/
│   │           └── kotlin/
│   │               └── se/ltu/rescueois/
│   │                   ├── SyncManagerTest.kt
│   │                   └── TileCacheTest.kt
│   ├── build.gradle.kts            # root project build
│   ├── settings.gradle.kts
│   ├── gradle.properties
│   └── README.md
├── infra/
│   ├── ansible/
│   │   ├── inventory/
│   │   │   ├── hosts.yml.template
│   │   │   └── group_vars/
│   │   │       ├── core.yml
│   │   │       ├── edge.yml
│   │   │       └── all.yml
│   │   ├── playbooks/
│   │   │   ├── core-provision.yml
│   │   │   ├── edge-provision.yml
│   │   │   └── wireguard-setup.yml
│   │   └── roles/
│   │       ├── postgres/
│   │       │   └── tasks/main.yml
│   │       ├── martin/
│   │       │   └── tasks/main.yml
│   │       ├── nginx/
│   │       │   └── tasks/main.yml
│   │       └── wireguard/
│   │           └── tasks/main.yml
│   ├── rutx50/
│   │   ├── vlan-config.rci.template
│   │   ├── firewall-zones.rci.template
│   │   └── README.md
│   └── rajant/
│       └── README.md               # BC|Commander config notes
├── scripts/
│   ├── dev-up.sh                   # spin up core docker-compose for local dev
│   ├── dev-down.sh
│   ├── run-migrations.sh
│   ├── build-pmtiles.sh            # manual PMTiles build trigger
│   └── promote-responder.sh        # promote a responder K430 to command role
├── .editorconfig
├── .gitignore
├── .pre-commit-config.yaml
├── LICENSE
├── README.md
└── CLAUDE.md
```

---

## File Content Specifications

### Root-level files

**README.md**: Project title, one-paragraph description, architecture diagram link, quickstart for local dev (`scripts/dev-up.sh`), link to `docs/architecture/README.md`, license, and contributing section pointing to PR template.

**CLAUDE.md**: Instructions for Claude Code working in this repo. Contents:

```markdown
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
```

**.gitignore**: Python (`__pycache__`, `.venv`, `*.egg-info`, `.pytest_cache`), Kotlin/Gradle (`.gradle`, `build/`, `*.apk`), Docker, IDE files, `.env`, `*.pem`, `*.key`, `wg0*.conf` (not templates).

**.editorconfig**: UTF-8, LF, 4-space indent for Python/Kotlin/SQL, 2-space for YAML/JSON, trim trailing whitespace.

**.pre-commit-config.yaml**: ruff (lint + format), trailing-whitespace, end-of-file-fixer, check-yaml, check-json.

**LICENSE**: Apache 2.0.

---

### `.github/`

**ci.yml**: On push/PR to main. Jobs: (1) Python lint+test for each service in `core/` and `edge/`, (2) Kotlin build for `tablet/`. Use matrix strategy for Python services. Pin Python 3.12, Java 17.

**release.yml**: On tag `v*`. Build and push Docker images for each service. Placeholder registry (ghcr.io).

**CODEOWNERS**: `* @aditya-sissodiya`

**pull_request_template.md**: Sections — Description, Type of change, How tested, Checklist (tests pass, docs updated, migrations forward-only).

**bug_report.md / feature_request.md**: Standard GitHub issue templates.

---

### `docs/architecture/README.md`

Write the three-tier architecture overview: core (PostgreSQL/PostGIS, GeoServer, Martin, Nginx, WireGuard), vehicle edge (K430 running local PostGIS + Martin + ops-api + syncd), tablets (Kotlin + MapLibre Native). State the single design rule: "Core owns master data. Command vehicle owns live incident state. Responders and tablets only queue and forward field edits." Include a text-based diagram of the data flow.

### `docs/architecture/network-topology.md`

Document the full IP addressing plan verbatim from the source spec: core subnets (`10.10.100–130.0/24`), WireGuard overlay (`10.252.0.0/24`), Rajant mesh (`10.253.0.0/16`), per-vehicle VLAN template (`172.31.<ID>.*`). Include the five VLANs (MGMT, EDGE-SVC, OPS-TABLET, SENSOR, MAINT) with their CIDR blocks.

### `docs/architecture/sync-protocol.md`

Document all six sync flows: (1) Core → Vehicle baseline, (2) Dispatch/incident bootstrap, (3) Tablet → nearest vehicle, (4) Responder → command vehicle, (5) Command → core, (6) Failure/recovery. For each flow, specify transport, mechanism, direction, and failure behavior.

### `docs/architecture/security-model.md`

Cover: per-vehicle VLAN isolation with zone firewall on RUTX50, WireGuard encrypted overlay, nftables on K430, tablet network policy (no internet, no mesh, local K430 only), Knox Manage fleet management, audit trail forwarding, existing IdP/CA integration (not a new identity stack).

### `docs/adr/template.md`

Standard ADR template: Title, Status, Context, Decision, Consequences.

### `docs/adr/0001-single-incident-writer.md`

Context: Multi-writer distributed incident tables cause conflict hell with PostgreSQL logical replication. Decision: Only the command vehicle K430 writes incident state; responders forward edits via outbox. Consequences: Simpler conflict model, but command vehicle is a single point that requires failover procedure.

### `docs/adr/0002-no-vlans-across-mesh.md`

Context: Stretching user VLANs across Rajant mesh creates broadcast storms and unmanageable routing. Decision: Mesh is transit-only between K430 edge nodes; all user/device VLANs terminate locally on each vehicle's RUTX50. Consequences: Clean separation, but requires application-layer routing for inter-vehicle data exchange.

### `docs/adr/0003-pmtiles-over-mbtiles.md`

Context: Need an offline tile format servable by Martin on edge nodes. Decision: PMTiles as default package format (single-file, HTTP-range-request friendly, no SQLite locking). Consequences: Martin serves PMTiles natively; slightly less tooling support than MBTiles in some GIS workflows.

---

### Python Services (core/* and edge/*)

For every Python service:

**pyproject.toml**: 
- `[project]` with name, version `0.1.0`, requires-python `>=3.12`
- Dependencies: `fastapi`, `uvicorn[standard]`, `sqlalchemy`, `asyncpg`, `pydantic`, `pydantic-settings`
- Service-specific deps where relevant (e.g., `httpx` for feed-importer, `python-multipart` for sync-api)
- `[tool.ruff]` with `line-length = 100`, `target-version = "py312"`
- `[tool.pytest.ini_options]` with `testpaths = ["tests"]`

**Dockerfile** (per service):
```dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir .
COPY src/ src/
EXPOSE 8000
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**src/main.py** (per service): FastAPI app with `/health` endpoint returning `{"status": "ok", "service": "<name>"}`. Import and include the service's router(s). Read config from environment via pydantic-settings `Settings` class.

**tests/**: At minimum one test file with a test that hits `/health` using `httpx.AsyncClient` + FastAPI `TestClient`.

Service-specific stub content:

- **feed-importer**: Each importer file (`lantmateriet.py`, `smhi.py`, etc.) should have a class with `async def fetch()` and `async def ingest(session)` methods, both raising `NotImplementedError` with a TODO comment describing what the importer should do.
- **publisher**: `pipeline.py` should define `async def run_pipeline(incident_id: str | None)` with stages as TODO comments (staging validate, promote, build PMTiles, build attachments, write manifest, publish).
- **sync-api**: Routes for `GET /sync/events`, `GET /sync/bootstrap`, `GET /tiles/{path}`, `GET /packages/{path}`. Stub handlers returning 501.
- **audit-api**: Routes for `POST /audit/events`, `GET /audit/events`. Stub handlers.
- **ops-api**: Routes for `GET /api/bootstrap`, `GET /api/search`, `GET /tiles/{path}`, `GET /files/{path}`, `POST /api/events` (accept field edits). Stub handlers.
- **syncd**: `config.py` should define `ROLE: Literal["command", "responder"]` read from env var `EDGE_ROLE`. Each module (`pull.py`, `push.py`, `accept.py`, `forward.py`) should have an `async def run()` coroutine with a TODO docstring explaining its sync flow responsibility.
- **package-cache**: Stub for local tile/attachment cache management.
- **audit-forwarder**: Stub for batching and forwarding audit entries to core.

---

### SQL Migrations

**core/db/migrations/001_init_schema.sql**: Enable PostGIS extension. Create schemas: `staging`, `master`, `publication`, `audit`.

**core/db/migrations/002_master_tables.sql**: Create tables in `master` schema:
- `sites` (id UUID PK, name TEXT, geom GEOMETRY(Point, 3006), metadata JSONB, created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ)
- `plans` (id UUID PK, site_id UUID FK, name TEXT, version INT, status TEXT, created_at, updated_at)
- `hazards` (id UUID PK, site_id UUID FK, substance TEXT, storage_info JSONB, geom GEOMETRY, created_at, updated_at)
- `area_geometries` (id UUID PK, plan_id UUID FK, label TEXT, geom GEOMETRY(Polygon, 3006), classification JSONB, created_at, updated_at)

Note: SRID 3006 = SWEREF 99 TM.

**core/db/migrations/003_incident_tables.sql**: Create tables:
- `incidents` (id UUID PK, name TEXT, status TEXT, aoi GEOMETRY(Polygon, 3006), opened_at TIMESTAMPTZ, closed_at TIMESTAMPTZ)
- `incident_events` (id UUID PK, incident_id UUID FK, event_seq BIGINT, event_type TEXT, payload JSONB, device_id TEXT, user_id TEXT, created_at TIMESTAMPTZ)

**core/db/migrations/004_audit_tables.sql**: Create `audit.events` (id UUID PK, timestamp TIMESTAMPTZ, service TEXT, action TEXT, actor TEXT, device_id TEXT, detail JSONB, source_edge TEXT).

**edge/db/migrations/001_edge_schema.sql**: Enable PostGIS. Create schemas: `cache`, `incident`, `outbox`.

**edge/db/migrations/002_outbox.sql**: Create `outbox.device_outbox` (id UUID PK, device_id TEXT, user_id TEXT, event_type TEXT, payload JSONB, created_at TIMESTAMPTZ, forwarded_at TIMESTAMPTZ NULL, ack_seq BIGINT NULL).

**edge/db/migrations/003_incident_journal.sql**: Create `incident.journal` and `incident.state` — same structure as core incident tables. Add comment: "Only populated on command-role K430."

---

### Tablet App (tablet/)

**settings.gradle.kts**: Root project name `rescue-ois-tablet`. Include `:app`.

**build.gradle.kts** (root): Kotlin 1.9.x, AGP 8.x, compose compiler plugin. Placeholder versions.

**app/build.gradle.kts**: 
- `applicationId = "se.ltu.rescueois"`
- `minSdk = 29`, `targetSdk = 35`
- Dependencies: Jetpack Compose BOM, MapLibre Native Android, Room, Retrofit/OkHttp, Kotlin Coroutines, kotlinx-serialization
- Enable compose

**RescueOisApp.kt**: Application class stub.

**MapScreen.kt**: Composable stub with TODO for MapLibre integration. Comment: "Primary screen. Full-bleed map with layer controls and site markers."

**SiteDetailScreen.kt**: Composable stub. Comment: "Detail view for selected site — plans, hazards, attachments."

**IncidentScreen.kt**: Composable stub. Comment: "Active incident view — event log, status updates, field edit submission."

**SyncStatusBar.kt**: Composable stub. Comment: "Persistent status bar showing sync state, last sync time, connectivity indicator."

**AppDatabase.kt**: Room database stub with `SiteDao` and `IncidentDao` entities.

**EdgeApiClient.kt**: Retrofit interface stub with endpoints matching ops-api routes.

**SyncManager.kt**: Stub class with `suspend fun syncBaseline()`, `suspend fun submitFieldEdit(edit: FieldEdit)`, `suspend fun pollEvents(afterSeq: Long)`. All throw `NotImplementedError`.

**MapLibreWrapper.kt**: Stub for MapLibre map initialization with offline tile source from local cache.

**OfflineTileProvider.kt**: Stub for serving tiles from local encrypted SQLite/PMTiles cache.

**AndroidManifest.xml**: Internet permission, `usesCleartextTraffic=false`, application entry.

---

### Docker Compose Files

**core/docker-compose.yml**: Services: `postgres` (postgis/postgis:16-3.5), `martin`, `nginx`, `geoserver` (kartoza/geoserver:2.28.x), `feed-importer`, `publisher`, `sync-api`, `audit-api`. Shared network `core-net`. Volumes for postgres data and published packages. Environment variables referencing `.env`.

**edge/docker-compose.yml**: Services: `postgres` (postgis/postgis:16-3.5), `martin`, `nginx`, `ops-api`, `syncd`, `package-cache`, `audit-forwarder`. Shared network `edge-net`. Environment variables including `EDGE_ROLE=command` (overridable).

---

### Nginx Configs

**core/nginx/nginx.conf**: Listen 443 (TLS placeholder with self-signed for dev). Upstream blocks for sync-api, audit-api, martin, geoserver. Location blocks: `/sync/*` → sync-api, `/tiles/*` → martin, `/packages/*` → static file serving from `/data/packages/`, `/geoserver/*` → geoserver. Access log with JSON format for auditability.

**edge/nginx/nginx.conf**: Listen 443 (TLS placeholder). Upstream blocks for ops-api, martin. Location blocks: `/api/*` → ops-api, `/sync/*` → syncd (command role only), `/tiles/*` → martin, `/files/*` → static from `/data/files/`. Client certificate validation placeholder (comment explaining mTLS with authority CA).

---

### Infra / Ansible

Stub playbooks and roles. Each `tasks/main.yml` should have task names with `# TODO` bodies describing what each task should do (install package, template config, enable service, etc.). The inventory template should show the expected host groups: `[core]`, `[edge_command]`, `[edge_responder]`.

**rutx50/**: `.rci.template` files with comments explaining the VLAN and firewall zone configuration that maps to the five-VLAN model. Not executable config — reference templates only.

---

### Scripts

**dev-up.sh**: `cd core && docker compose up -d`

**dev-down.sh**: `cd core && docker compose down`

**run-migrations.sh**: Apply all SQL files in order using `psql`. Accept `DATABASE_URL` env var.

**build-pmtiles.sh**: Placeholder calling the publisher pipeline manually.

**promote-responder.sh**: Change `EDGE_ROLE` env var from `responder` to `command` and restart syncd container. Include safety warning comment.

---

## Execution Instructions for Claude Code

1. Create the directory tree exactly as specified above.
2. Populate every file with the content described in this spec. Where full content is specified, use it verbatim. Where stubs are specified, create minimal but syntactically valid files with appropriate TODO comments.
3. Every Python `__init__.py` should be empty.
4. Every `README.md` in a service directory should contain: service name, one-line description, how to run locally, how to run tests, environment variables needed.
5. Ensure all Python files pass `ruff check` (no unused imports, no syntax errors).
6. Ensure all Kotlin files are syntactically valid.
7. Ensure all SQL files are syntactically valid PostgreSQL.
8. Ensure all YAML files are valid.
9. Do NOT create placeholder data, seed files, or mock fixtures. Keep it clean.
10. After creating everything, run `find . -name "*.py" | head -20` and `find . -name "*.kt" | head -20` to verify structure.
