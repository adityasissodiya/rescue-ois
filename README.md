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

### 🔬 Prototype Validation Harness
To run the structural validation harness used by the paper:
```bash
./scripts/dev-up.sh
python3 scripts/evaluate-pilot.py
python3 paper/scripts/generate_plots.py
```
The harness writes `eval_metrics.jsonl`. Plot generation only emits a figure when real non-null measurements exist; the current paper does not embed numerical performance results.

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

# Tiered Sync — Design System

## Overview

This design system covers two related artifacts derived from a research project on offline-first incident information management for Swedish rescue services:

1. **The ISCRAM Paper** — a two-column academic manuscript targeting ISCRAM 2027 (Information Systems for Crisis Response and Management). LaTeX-based, using `lmodern` (Latin Modern) fonts and a standard academic typographic register.

2. **The Tiered Sync System UI** — a conceptual design for the three-tier field system described in the paper: a regional core, vehicle edge nodes, and field tablets used by Swedish rescue services (räddningstjänst) at incident scenes. Since no production UI codebase was provided, this design system proposes a coherent visual language grounded in Swedish public safety conventions and field-use ergonomics.

## Sources

- **Codebase:** `paper/` (mounted via File System Access API) — LaTeX paper scaffold with full section stubs, bibliography seed, and figure/table placeholders
- **No Figma links provided**
- **No production app codebase provided** — UI kit is a conceptual proposal

---

## CONTENT FUNDAMENTALS

### Voice and Tone
The paper is written in **third-person academic register** — impersonal, precise, and direct. Sentences are declarative and often short. Hedging is present but not excessive; claims are scoped explicitly ("in this domain", "for this deployment scale"). There is no marketing language, no first person "I" or "we" outside of standard academic usage.

**Copy conventions:**
- Casing: Sentence case for headings and labels. Technical terms are not title-cased unless they are proper nouns (e.g. "WireGuard", "PostgreSQL/PostGIS").
- No emoji anywhere.
- Abbreviations spelled out on first use: WAN, CRDT, VLAN, LTE, MSB, RAKEL.
- Numbers: spelled out below ten; numeral form above.
- Swedish terms appear where operationally exact (e.g. "räddningstjänst"), always italicized on first use.

**UI copy conventions (tablet app):**
- Extremely terse — labels, not sentences. "Command vehicle", "Outbox (3)", "Sync pending".
- Status language is neutral and operational: "Partition detected", "Promoting to command", "Edit queued".
- No softening language. No "Oops!" or friendly error copy. Rescue workers need unambiguous states.
- All caps used only for status badges (OFFLINE, LIVE, QUEUED).

---

## VISUAL FOUNDATIONS

### Colors
Two palettes in play:

**Paper palette:** Monochrome academic. Near-black body text (#1a1a1a on white). Hyperlinks suppressed (hidelinks). Tables use booktabs rules — no vertical lines, light gray mid-rules. Figures are boxed placeholders.

**Tablet UI palette:** Dark-mode-first, high-contrast, field-readable.
- Background: deep charcoal `#0f1117`
- Surface: `#1c2030`
- Card/panel: `#252b3b`
- Border: `#2e3650`
- Primary accent: Swedish rescue orange `#f5681e` (maps to räddningstjänst red-orange livery)
- Alert/critical: `#e8302a`
- Info/authority: Swedish MSB blue `#0057a8`
- Success/safe: `#2db67d`
- Warning: `#f5b21e`
- Text primary: `#f0f2f7`
- Text secondary: `#8a94b0`
- Text muted: `#4a5168`

### Typography
- **Paper:** Latin Modern (lmodern, Computer Modern family). Closest Google Fonts substitute: **Source Serif 4** (used in preview cards). Monospace: Latin Modern Mono → **JetBrains Mono**.
- **Tablet UI:** **IBM Plex Sans** for all UI. Compact, authoritative, legible at small sizes and in bright outdoor light. Monospace data: **JetBrains Mono**.

### Spacing & Layout
- Paper: 1.65 cm margins, 0.7 cm column gutter, 10pt base type, tight list spacing (2pt item/top sep).
- Tablet: 8px base unit. Comfortable 44px minimum touch targets. Dense but not cramped — information is safety-critical.

### Backgrounds & Surfaces
- Paper: white page only.
- Tablet: layered dark surfaces. No gradients except for a subtle top-bar protection vignette. No decorative imagery. Maps are the primary "background" in operational views.

### Animation & Interaction
- Paper: N/A (static document).
- Tablet: minimal animation. Status transitions use 150ms opacity fades. Sync indicator pulses at 1s interval. No bouncy or playful easing. `ease-in-out` or `linear` only.

### Corner Radii
- Tablet: 4px for compact chips/badges, 8px for cards and panels, 12px for modals. No pill shapes except status badges.

### Shadows & Elevation
- Tablet: `0 1px 3px rgba(0,0,0,0.5)` for cards, `0 4px 16px rgba(0,0,0,0.6)` for modals and overlays. Elevation expressed through shadow darkness, not blur radius.

### Iconography
See ICONOGRAPHY section below.

### Cards
Cards have a `#252b3b` background, `1px solid #2e3650` border, 8px radius, and 12px/16px padding. No colored left-border accents. Critical state cards add a top border `2px solid #e8302a`.

### Hover / Press States
- Hover: background lightens by one surface step (e.g. `#252b3b` → `#2e3650`).
- Press: slight scale `0.98` + background darkens slightly. No color change for standard actions.
- Destructive actions: red tint on hover (`rgba(232,48,42,0.15)`).

### Color vibe of imagery
Maps (OSM/vector tile based) are the main imagery. Style: dark basemap, muted terrain, high-contrast road labels. Photos if any: desaturated, functional (site photos for pre-incident plans).

---

## ICONOGRAPHY

No icon font or sprite sheet is bundled with the paper codebase. The tablet UI design system uses **Lucide Icons** (CDN: `https://unpkg.com/lucide@latest`) — stroke-based, 1.5px weight, 24px grid. This is a **proposed substitution**; the real system would likely use a similar lightweight stroke icon set.

Key icons in use:
- `map-pin` — incident location
- `radio` — mesh/comms status
- `wifi-off` — partition / offline
- `shield` — command authority
- `truck` — vehicle node
- `tablet-smartphone` — field tablet
- `clock` — sync timestamp
- `send` — outbox submit
- `arrow-up-from-line` — forward-only replication
- `alert-triangle` — warning/critical state
- `check-circle-2` — confirmed/committed

No emoji used. No Unicode chars as icons.

---

## File Index

```
README.md                   This file
SKILL.md                    Agent skill definition
colors_and_type.css         CSS custom properties for all colors, type, spacing
assets/                     Logos and visual assets
preview/                    Design system card previews (registered in Design System tab)
  colors_base.html
  colors_semantic.html
  type_paper.html
  type_tablet.html
  spacing_tokens.html
  components_badges.html
  components_buttons.html
  components_cards.html
  components_status.html
  brand_overview.html
ui_kits/
  tablet/                   Field tablet UI kit (conceptual)
    index.html
    README.md
```
