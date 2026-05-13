# Architecture Overview

Rescue OIS is a three-tier research prototype for authority-aligned
synchronization in rescue-service incident response. Offline operation is a
supporting property; the central protocol boundary is command authority for
authority-bearing incident events.

## Tiers

### 1. Regional Core

Authoritative store for **master data** (sites, plans, hazards, area geometries) and the publication pipeline that produces offline packages for vehicles.

Components:

- PostgreSQL 16 + PostGIS 3.5 — master/staging/publication/audit schemas
- GeoServer — OGC services for desktop GIS clients
- Martin — vector tile server (PMTiles + PG sources)
- Nginx — TLS termination, reverse proxy, static publication serving
- WireGuard — encrypted overlay to vehicle edges
- `feed-importer` — pulls Lantmäteriet, SMHI, Trafikverket, Naturvårdsverket
- `publisher` — staging → master → build (PMTiles + attachments) → publish + manifest
- `sync-api` — `/sync/*`, `/tiles/*`, `/packages/*` for edges
- `audit-api` — receives audit events forwarded from edges

### 2. Vehicle Edge (per-vehicle K430 + RUTX50 + Rajant Hawk)

Local copy of master data and the **live incident state**. One vehicle per incident is designated **command** and assigns `event_seq` for authority-bearing incident events. Other vehicles act as **responders** that queue field edits and forward them.

Components:

- PostgreSQL 16 + PostGIS 3.5 — cache + outbox + (command-only) incident journal
- Martin — serves PMTiles from local cache
- Nginx — TLS termination, reverse proxy
- `ops-api` — `/api/bootstrap`, `/api/search`, `/api/events`, `/tiles/*`, `/files/*`
- `syncd` — pull (baseline), push (responder→command), accept & sequence (command), forward (command→core)
- `package-cache` — local PMTiles/attachment cache management
- `audit-forwarder` — batches and forwards audit entries to core

### 3. Field Tablet

Ruggedized Android tablet talking only to the local vehicle K430 over HTTPS. No internet, no mesh access.

Components:

- Kotlin / Jetpack Compose UI
- MapLibre Native Android (offline tile rendering from local cache)
- Room (SQLite) local database
- Retrofit / OkHttp client to ops-api

## Single Design Rule

> **Core owns master data. Command vehicle owns live incident state. Responders and tablets only queue and forward field edits.**

This rule avoids multi-writer conflict resolution for authority-bearing incident events. It does not make the system a generic offline database or a replacement for consensus.

## Evidence Boundary

The current repository evaluates the implemented Docker/Python service path:
responder outbox forwarding, command-side idempotent sequencing,
command-to-core backfill, duplicate replay, selected partition behavior, and
model-level promotion safety. It does not validate Rajant radio behavior,
Android tablet persistence, WireGuard or mTLS overhead, production
promotion/fencing, service-level durable `command_epoch` rejection, or exhaustive
crash-boundary safety.

The direct command accept-path partition artifact is intentionally narrow. It
isolates a responder `syncd` process and submits command-originated writes
directly to the command `syncd` `/accept/event-batch` endpoint while command
PostgreSQL remains available. It does not exercise the full tablet -> responder
`ops-api` -> responder outbox -> command accept path during the partition.

## Data Flow (text diagram)

```
+----------------------+        WireGuard         +-------------------------+
|     Regional Core    |  <----------------->     |   Vehicle Edge (K430)   |
|                      |                          |                         |
|  PostGIS (master)    |  baseline replication    |  PostGIS (cache,        |
|  Martin (PMTiles)    |  -------------------->   |  incident journal*,     |
|  publisher           |                          |  outbox)                |
|  sync-api            |  audit forwarding        |  ops-api                |
|  audit-api           |  <---------------------- |  syncd  (* = command)   |
|  GeoServer           |                          |  package-cache          |
+----------------------+                          +-----------+-------------+
                                                              |
                                              local HTTPS via RUTX50 VLAN
                                                              |
                                                  +-----------+-------------+
                                                  |     Field Tablets       |
                                                  |  Kotlin / MapLibre      |
                                                  |  Room (offline)         |
                                                  +-------------------------+

           Rajant Hawk mesh sits between vehicles as transit-only
           (no user VLANs stretched across the mesh).
```

## Further Reading

- [../what-fails-without-our-solution.md](../what-fails-without-our-solution.md) — failure modes and claim discipline
- [network-topology.md](network-topology.md) — IP plan, VLANs, firewall matrix
- [sync-protocol.md](sync-protocol.md) — six sync flows in detail
- [security-model.md](security-model.md) — VLAN isolation, WireGuard, Knox, audit
- [../adr/](../adr/) — Architecture Decision Records
