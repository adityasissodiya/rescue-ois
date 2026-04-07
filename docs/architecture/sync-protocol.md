# Sync Protocol

Rescue OIS supports six distinct synchronization flows. Each flow is described below in terms of **transport, mechanism, direction, and failure behavior**.

## Flow 1 — Core → Vehicle Baseline

Replicates master data (sites, plans, hazards, area geometries) and published map packages from the regional core to every vehicle K430.

- **Transport:** WireGuard overlay (`10.252.0.0/24`), HTTPS to `sync-api` and `packages` endpoints
- **Mechanism:** PostgreSQL logical replication (master tables, one-way) + HTTP polling for `manifest.json` and PMTiles/attachment downloads via HTTP range requests
- **Direction:** core → edge
- **Frequency:** continuous (logical replication) + scheduled package poll (every 15 min when online)
- **Failure behavior:** edge keeps last known good package; replication catches up automatically when WG link returns. The publisher's manifest + sha256sum allows partial-resume of attachment downloads.

## Flow 2 — Dispatch / Incident Bootstrap

When an incident is dispatched, the assigned command vehicle receives the incident-specific bundle and opens the incident journal locally.

- **Transport:** HTTPS to core `sync-api` over WG (preferred) or local creation if no link
- **Mechanism:** `GET /sync/bootstrap?incident_id=...` returns AOI, plan refs, hazard subset, attachment list. Command K430 marks itself as the writer of `incident.journal` and `incident.state`.
- **Direction:** core → command edge (initial); local thereafter
- **Failure behavior:** command vehicle can bootstrap from cached master data if core is unreachable; reconciles when link returns.

## Flow 3 — Tablet → Nearest Vehicle

Field tablets push and pull all incident data to/from the vehicle K430 they are physically connected to (OPS-TABLET VLAN over RUTX50).

- **Transport:** Local HTTPS over OPS-TABLET VLAN to `ops-api` on the K430
- **Mechanism:**
  - Read: `GET /api/bootstrap`, `GET /api/search`, `GET /tiles/*`, `GET /files/*`
  - Write: `POST /api/events` (field edit, atomic, idempotent via client-supplied UUID)
- **Direction:** bidirectional
- **Failure behavior:** tablet has a local Room outbox; retries `POST /api/events` until acknowledged. Tablet displays a sync status bar.

## Flow 4 — Responder → Command Vehicle

Non-command vehicles (responders) accept tablet edits, queue them in `device_outbox`, and forward to the command vehicle over the Rajant mesh.

- **Transport:** Rajant Hawk mesh (`10.253.0.0/16`), application-layer HTTPS between K430s
- **Mechanism:** `syncd` on responder pushes batches from `outbox.device_outbox` to the command K430's `syncd` accept endpoint. Command K430 sequences incoming events into `incident.journal` (single writer; see [ADR-0001](../adr/0001-single-incident-writer.md)).
- **Direction:** responder edge → command edge
- **Failure behavior:** outbox persists until ack received. If command vehicle fails, see Flow 6.

## Flow 5 — Command → Core

Command vehicle forwards the authoritative incident journal to the regional core for archival, regional dashboards, and audit.

- **Transport:** WireGuard overlay, HTTPS to core `sync-api`
- **Mechanism:** `syncd.forward` posts incremental journal slices keyed by `event_seq` to core. Core acks with the last accepted sequence number.
- **Direction:** command edge → core
- **Failure behavior:** command edge buffers locally; resumes from last acked sequence when WG returns.

## Flow 6 — Failure / Recovery

Covers failover when the command vehicle is lost or partitioned.

- **Detection:** responder K430s detect command-vehicle absence (heartbeat timeout over mesh).
- **Promotion:** operator runs `scripts/promote-responder.sh` on a designated responder; `EDGE_ROLE` flips from `responder` to `command`, `syncd` restarts in command mode.
- **Reconciliation:** new command pulls the most recent journal it has, accepts new events, and re-establishes forwarding to core. The old command's events (if any) are reconciled by `event_seq` ordering at core.
- **Audit:** every promotion is logged via `audit-forwarder` to core's `audit.events` with the operator identity.
