# Rescue OIS

Resilient Operational Information System for Swedish rescue services — a map-centric, offline-first digital platform replacing paper-based incident planning.

The system is a three-tier architecture: a regional **core** (master data and publication), **vehicle edge** nodes (per-vehicle K430 + RUTX50 + Rajant Hawk providing local services and the live incident journal), and ruggedized **field tablets** that talk only to their local vehicle edge.

See [docs/architecture/README.md](docs/architecture/README.md) for the architecture overview, network topology, sync protocol, and security model.

## Quickstart (local development)

```bash
./scripts/dev-up.sh          # start core stack via docker-compose
./scripts/run-migrations.sh  # apply SQL migrations
./scripts/dev-down.sh        # tear down
```

## Repository layout

- `core/` — regional services (PostGIS, Martin, GeoServer, Nginx, sync-api, audit-api, feed-importer, publisher)
- `edge/` — vehicle K430 services (PostGIS, Martin, ops-api, syncd, package-cache, audit-forwarder)
- `tablet/` — Kotlin / Jetpack Compose / MapLibre Native Android app
- `infra/` — Ansible playbooks, RUTX50 templates, Rajant notes
- `docs/` — architecture, deployment, runbooks, ADRs
- `scripts/` — developer convenience scripts

## License

Apache License 2.0 — see [LICENSE](LICENSE).

## Contributing

Open a pull request following the template in `.github/pull_request_template.md`.
