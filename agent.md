# Agent Directives: Rescue OIS Project

## Purpose
This file (`agent.md`) contains the critical context, architectural rules, and technical conventions necessary for an AI coding agent to effectively analyze, implement, and debug the **Resilient Operational Information System (OIS)** for Swedish rescue services. 

If you are an agent joining this workspace, parse this document fully before attempting to modify the code.

## Project Overview
Rescue OIS is a digital platform designed to replace paper-based incident planning. It uses an offline-first **three-tier architecture** heavily designed for resilience over intermittent and disconnected mesh networks.

### The Three Tiers
1. **Regional Core (`core/`)**: The source of truth. Handles global master data (map tiles, basic static data) and publishes it.
2. **Vehicle Edge Nodes (`edge/`)**: Emulated via Docker, but physically a combination of K430 routers, RUTX50, and Rajant Hawk hardware installed per-vehicle.
   - **Command Vehicle**: The single incident writer. Only this node owns the live `incident.journal`.
   - **Responder Vehicles**: These write to a local `device_outbox` and queue edits to forward to the Command node.
3. **Field Tablets (`tablet/`)**: Off-grid ruggedized tablets running an Android application. **Rule:** Tablets never talk to the mesh network or internet—they *only* communicate with the localized vehicle Edge node over HTTPS.

## Directory Structure
- `core/` - Python FastAPI microservices (PostgreSQL/PostGIS, Martin, GeoServer, Nginx, WireGuard).
- `edge/` - Subset of core microservices modified for Edge (PostGIS, Martin, ops-api, syncd, audit-forwarder).
- `tablet/` - Kotlin, Jetpack Compose, and MapLibre Native implementation.
- `infra/` - Ansible provisioning and RUTX50 VLAN network templates.
- `docs/` - Architectural documentation and ADRs (Architecture Decision Records).
- `paper/` - LaTeX manuscripts and Python evaluation plotting scripts (`generate_plots.py`) for benchmarking.
- `scripts/` - Developer scripts for simulation, dev orchestration, and chaos testing.

## Tech Stack & Conventions
- **Backend (Core/Edge)**: Python 3.12+, `FastAPI`, `asyncpg`, `sqlalchemy`, `pydantic`. 
  - Linting: `ruff`. 
  - Testing: `pytest`.
- **Database**: PostgreSQL 16 + PostGIS 3.5.
- **Frontend (Tablet)**: Android Kotlin, `Jetpack Compose`, `Room` (SQLite), `MapLibre Native`.
- **Formatting**: `ktlint` for Android. `ruff` for Python.
- **Microservices Rules**: 
  - Never hardcode configurations; strictly use environment variables via `pydantic-settings`.
  - All Python services MUST expose a `GET /health` endpoint returning `{"status": "ok", "service": "<name>"}`.
  - SQL migrations are plain SQL mapped sequentially (forward-only logic).

## Key Architectural Invariants ⚠️
When writing or refactoring code across the repository, the following core rules must **not** be violated:
1. **Single Incident Writer**: ONLY the assigned command vehicle node (`EDGE_ROLE=command`) can write to `incident_journal` and `incident_state`.
2. **Responder Outboxing**: Responder edge nodes (`EDGE_ROLE=responder`) strictly push to `device_outbox` and HTTP POST those edits over the mesh.
3. **VLAN Mesh Isolation**: User VLANs and networks are natively partitioned locally per vehicle and never stretch across the Rajant Mesh. The mesh is exclusively transit for K430 nodes. 
4. **Tile Formats**: PMTiles are prioritized over MBTiles to allow Native HTTP Range-Requests directly from Martin tileserver.
5. **No Two-Way Core Replication**: Core-to-Edge PostgreSQL logical replication flows one direction for master data only.

## Simulation & Evaluation Scripts
Because this framework requires physical vehicle node emulation, we utilize Docker Compose orchestration to mimic multiple networks locally:

### 1. Booting up Emulation
```bash
./scripts/dev-up.sh
```
*Note: This script has been modified to spin up 1 Core element alongside both a Command edge and Responder edge containers with dynamic ephemeral ports to avoid Host OS `:80` and `:443` collisions.*

### 2. Experimental Academic Verification
If modifying the synchronization mechanisms (`syncd`), always ensure you execute the evaluation pilot test to check your changes against the baseline latency goals:
```bash
python3 scripts/evaluate-pilot.py
```
This runs a simulated test injecting a WAN networking partition (`scripts/inject-partition.sh`), effectively recording propagation timings across the cluster.

### 3. Generate Plot Overviews
```bash
python3 paper/scripts/generate_plots.py
```
*Extracts the JSON from `eval_metrics.log` and translates it into `fig_evaluation.pdf` to visually verify synchronization benchmark regressions.*
