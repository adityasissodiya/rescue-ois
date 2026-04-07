# Architecture Overview

Rescue OIS is a three-tier system designed for resilient, offline-first operation in Swedish rescue services.

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

Local copy of master data and the **live incident state**. One vehicle per incident is designated **command** (single writer). Other vehicles act as **responders** that queue field edits and forward them.

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

This rule eliminates multi-writer conflict resolution across PostgreSQL logical replication.

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

- [network-topology.md](network-topology.md) — IP plan, VLANs, firewall matrix
- [sync-protocol.md](sync-protocol.md) — six sync flows in detail
- [security-model.md](security-model.md) — VLAN isolation, WireGuard, Knox, audit
- [../adr/](../adr/) — Architecture Decision Records
