# 🚁 Rescue OIS

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Build Status](https://github.com/aditya-sissodiya/rescue-ois/actions/workflows/ci.yml/badge.svg)](https://github.com/aditya-sissodiya/rescue-ois/actions)

> **Resilient Operational Information System** for Swedish rescue services — a map-centric, offline-first digital platform replacing paper-based incident planning.

---

## 🏗️ Architecture Overview
The system utilizes a robust three-tier architecture specifically designed for unstable network conditions:
- 🏢 **Regional Core**: Source of truth handling master data and map publication.
- 🚒 **Vehicle Edge Nodes**: Installed per-vehicle (`K430` + `RUTX50` + `Rajant Hawk`). These provide local services and host the live incident journal for offline operations.
- 📱 **Field Tablets**: Ruggedized operator tablets that communicate exclusively with their local vehicle edge node.

📖 *See [docs/architecture/README.md](docs/architecture/README.md) for the architecture overview, network topology, sync protocol, and security model.*

---

## 🚀 Quickstarts 

### 🖥️ Local Development Emulation
To quickly boot up a full environment locally (containing 1 Core, 1 Edge Command, and 1 Edge Responder):

```bash
./scripts/dev-up.sh          # Start core & edges via docker-compose
./scripts/run-migrations.sh  # Apply SQL migrations
./scripts/dev-down.sh        # Tear down
```

### 🔬 Academic Evaluation Pilot
To reproduce the timing metrics and figures presented in our academic paper:
```bash
./scripts/dev-up.sh
python3 scripts/evaluate-pilot.py
python3 paper/scripts/generate_plots.py
```
> The generated SVGs/PDFs will be pushed to the `paper/figures` directory!

---

## 📁 Repository Layout

| Directory   | Description |
| ----------- | ----------- |
| `core/`     | Regional services *(PostGIS, Martin, GeoServer, Nginx, sync-api, audit-api, feed-importer, publisher)* |
| `edge/`     | Vehicle K430 services *(PostGIS, Martin, ops-api, syncd, package-cache, audit-forwarder)* |
| `tablet/`   | Kotlin / Jetpack Compose / MapLibre Native Android application |
| `infra/`    | Ansible playbooks, RUTX50 templates, Rajant notes |
| `docs/`     | Architecture, deployment, runbooks, and ADR tracking |
| `paper/`    | LaTeX files, research scripts, and generated figures |
| `scripts/`  | Developer convenience & test runner scripts |

---

## 🤝 Contributing & License

Open a pull request following the template in `.github/pull_request_template.md`.

This software is released under the **Apache License 2.0** — see [LICENSE](LICENSE).
