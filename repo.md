# Repository Tree

Annotated tree of the current repository. This focuses on tracked source, documentation, infrastructure, and research assets. Omitted: `.git/`, `.claude/`, and `tablet/.gradle/`.

```text
rescue-ois/
├── .github/                                      # GitHub automation and contribution templates
│   ├── CODEOWNERS                                # Review ownership rules
│   ├── ISSUE_TEMPLATE/                           # Bug report and feature request forms
│   │   ├── bug_report.md                         # Bug template
│   │   └── feature_request.md                    # Feature template
│   ├── pull_request_template.md                  # Pull request checklist/template
│   └── workflows/                                # CI and release pipelines
│       ├── ci.yml                                # Continuous integration workflow
│       └── release.yml                           # Release workflow
├── CLAUDE.md                                     # Short agent-facing project briefing
├── LICENSE                                       # Apache 2.0 license
├── PROJECT_SCAFFOLD.md                           # Original repository scaffold/specification
├── README.md                                     # Project overview, quickstart, and architecture summary
├── Rescue OIS Whitepaper.html                    # Static HTML whitepaper/design artifact
├── SKILL.md                                      # Skill manifest for the design-system workflow
├── agent.md                                      # Detailed AI agent directives and architecture rules
├── mismatch.md                                   # Notes on gaps between the paper and the current scaffold
├── core/                                         # Regional core services and core-side infrastructure
│   ├── docker-compose.yml                        # Local compose stack for core services
│   ├── audit-api/                                # Core API that receives and stores audit events
│   │   ├── Dockerfile                            # Container image for audit-api
│   │   ├── README.md                             # Service purpose, endpoints, and env vars
│   │   ├── pyproject.toml                        # Python package/dependency config
│   │   ├── src/                                  # FastAPI implementation
│   │   │   ├── __init__.py
│   │   │   ├── main.py                           # App entrypoint
│   │   │   ├── models.py                         # Audit request/response models
│   │   │   └── routes.py                         # Audit endpoints
│   │   └── tests/                                # Service tests
│   │       ├── __init__.py
│   │       └── test_audit.py
│   ├── db/                                       # Core database schema definitions
│   │   └── migrations/                           # Forward-only PostgreSQL migrations
│   │       ├── 001_init_schema.sql               # Initial schema setup
│   │       ├── 002_master_tables.sql             # Master-data tables
│   │       ├── 003_incident_tables.sql           # Incident-related tables
│   │       ├── 004_audit_tables.sql              # Audit tables
│   │       └── README.md                         # Migration usage notes
│   ├── feed-importer/                            # Imports external geospatial feeds into staging
│   │   ├── Dockerfile                            # Container image for feed-importer
│   │   ├── README.md                             # Supported feeds and runtime config
│   │   ├── pyproject.toml                        # Python package/dependency config
│   │   ├── src/
│   │   │   ├── __init__.py
│   │   │   ├── main.py                           # App entrypoint
│   │   │   ├── common/                           # Shared database and geometry helpers
│   │   │   │   ├── __init__.py
│   │   │   │   ├── db.py                         # Database helper utilities
│   │   │   │   └── geo.py                        # Geospatial helper utilities
│   │   │   └── importers/                        # Source-specific importers
│   │   │       ├── __init__.py
│   │   │       ├── lantmateriet.py               # Lantmateriet importer
│   │   │       ├── naturvardsverket.py           # Naturvardsverket importer
│   │   │       ├── smhi.py                       # SMHI importer
│   │   │       └── trafikverket.py               # Trafikverket importer
│   │   └── tests/
│   │       ├── __init__.py
│   │       └── test_importers.py                 # Importer tests
│   ├── nginx/
│   │   └── nginx.conf                            # Core reverse proxy/TLS config
│   ├── publisher/                                # Builds and publishes packages for edge nodes
│   │   ├── Dockerfile                            # Container image for publisher
│   │   ├── README.md                             # Publish pipeline overview
│   │   ├── pyproject.toml                        # Python package/dependency config
│   │   ├── src/
│   │   │   ├── __init__.py
│   │   │   ├── attachments.py                    # Attachment bundling logic
│   │   │   ├── main.py                           # App entrypoint
│   │   │   ├── manifest.py                       # Package manifest generation/signing
│   │   │   ├── pipeline.py                       # Staging -> master -> build -> publish flow
│   │   │   └── pmtiles_builder.py                # PMTiles package builder
│   │   └── tests/
│   │       ├── __init__.py
│   │       └── test_pipeline.py                  # Pipeline tests
│   ├── sync-api/                                 # Core sync/package/tile API for edge nodes
│   │   ├── Dockerfile                            # Container image for sync-api
│   │   ├── README.md                             # Endpoints and runtime config
│   │   ├── pyproject.toml                        # Python package/dependency config
│   │   ├── src/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py                           # Sync API auth helpers
│   │   │   ├── main.py                           # App entrypoint
│   │   │   ├── models.py                         # Sync/package models
│   │   │   └── routes/
│   │   │       ├── __init__.py
│   │   │       ├── packages.py                   # /packages/* routes
│   │   │       ├── sync.py                       # /sync/* routes
│   │   │       └── tiles.py                      # /tiles/* routes
│   │   └── tests/
│   │       ├── __init__.py
│   │       └── test_sync.py                      # Sync API tests
│   └── wireguard/
│       ├── README.md                             # Core WireGuard overlay notes
│       └── wg0-core.conf.template                # Core WireGuard config template
├── docs/                                         # Architecture, deployment, operations, and ADRs
│   ├── adr/                                      # Architecture Decision Records
│   │   ├── 0001-single-incident-writer.md        # Command vehicle is the only incident writer
│   │   ├── 0002-no-vlans-across-mesh.md          # Do not stretch VLANs over the mesh
│   │   ├── 0003-pmtiles-over-mbtiles.md          # PMTiles chosen over MBTiles
│   │   └── template.md                           # ADR authoring template
│   ├── architecture/                             # High-level system design docs
│   │   ├── README.md                             # Three-tier architecture overview
│   │   ├── network-topology.md                   # IP plan, VLANs, and firewall model
│   │   ├── security-model.md                     # Security and isolation model
│   │   └── sync-protocol.md                      # Detailed sync flows
│   ├── deployment/                               # Provisioning/setup guides
│   │   ├── core-setup.md                         # Core environment setup guide
│   │   ├── mesh-commissioning.md                 # Rajant mesh commissioning guide
│   │   ├── tablet-enrollment.md                  # Tablet enrollment/setup guide
│   │   └── vehicle-edge-setup.md                 # Vehicle edge setup guide
│   └── runbooks/                                 # Operational procedures
│       ├── command-failover.md                   # Command-role failover procedure
│       ├── device-revocation.md                  # Device revocation process
│       └── incident-bootstrap.md                 # Incident bootstrap procedure
├── edge/                                         # Vehicle-edge services and edge-side infrastructure
│   ├── audit-forwarder/                          # Sends edge audit batches to the core
│   │   ├── Dockerfile                            # Container image for audit-forwarder
│   │   ├── README.md                             # Forwarder overview and env vars
│   │   ├── pyproject.toml                        # Python package/dependency config
│   │   ├── src/
│   │   │   ├── __init__.py
│   │   │   ├── forwarder.py                      # Audit batching/forwarding logic
│   │   │   └── main.py                           # App entrypoint
│   │   └── tests/
│   │       ├── __init__.py
│   │       └── test_health.py                    # Health endpoint test
│   ├── db/                                       # Edge database schema definitions
│   │   └── migrations/                           # Forward-only PostgreSQL migrations for edges
│   │       ├── 001_edge_schema.sql               # Base edge schema
│   │       ├── 002_outbox.sql                    # Device outbox tables
│   │       ├── 003_incident_journal.sql          # Command-role incident journal tables
│   │       └── README.md                         # Migration usage notes
│   ├── docker-compose.yml                        # Local compose stack for edge services
│   ├── nftables/
│   │   ├── README.md                             # Edge firewall policy notes
│   │   └── nftables.conf.template                # Edge nftables template
│   ├── nginx/
│   │   └── nginx.conf                            # Edge reverse proxy/TLS config
│   ├── ops-api/                                  # Tablet-facing edge API
│   │   ├── Dockerfile                            # Container image for ops-api
│   │   ├── README.md                             # Endpoints and runtime config
│   │   ├── pyproject.toml                        # Python package/dependency config
│   │   ├── src/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py                           # Tablet/edge auth helpers
│   │   │   ├── incident.py                       # Incident journal/state logic
│   │   │   ├── main.py                           # App entrypoint
│   │   │   ├── models.py                         # Request/response models
│   │   │   └── routes/
│   │   │       ├── __init__.py
│   │   │       ├── api.py                        # /api/bootstrap, /api/search, /api/events
│   │   │       ├── files.py                      # /files/* routes
│   │   │       └── tiles.py                      # /tiles/* routes
│   │   └── tests/
│   │       ├── __init__.py
│   │       ├── test_api.py                       # Tablet API tests
│   │       └── test_incident.py                  # Incident logic tests
│   ├── package-cache/                            # Local PMTiles and attachment cache management
│   │   ├── Dockerfile                            # Container image for package-cache
│   │   ├── README.md                             # Cache behavior and env vars
│   │   ├── pyproject.toml                        # Python package/dependency config
│   │   ├── src/
│   │   │   ├── __init__.py
│   │   │   ├── cache.py                          # Cache swap/inspection logic
│   │   │   └── main.py                           # App entrypoint
│   │   └── tests/
│   │       ├── __init__.py
│   │       └── test_health.py                    # Health endpoint test
│   ├── syncd/                                    # Edge sync daemon for pull/push/accept/forward flows
│   │   ├── Dockerfile                            # Container image for syncd
│   │   ├── README.md                             # Role-dependent sync behavior
│   │   ├── pyproject.toml                        # Python package/dependency config
│   │   ├── src/
│   │   │   ├── __init__.py
│   │   │   ├── accept.py                         # Command-side accept/sequencing flow
│   │   │   ├── config.py                         # Role/config handling
│   │   │   ├── forward.py                        # Command-to-core forward flow
│   │   │   ├── main.py                           # App entrypoint
│   │   │   ├── outbox.py                         # Device outbox helpers
│   │   │   ├── pull.py                           # Core-to-edge baseline sync
│   │   │   └── push.py                           # Responder-to-command push flow
│   │   └── tests/
│   │       ├── __init__.py
│   │       ├── test_accept.py                    # Accept flow tests
│   │       ├── test_pull.py                      # Pull flow tests
│   │       └── test_push.py                      # Push flow tests
│   └── wireguard/
│       ├── README.md                             # Edge WireGuard enrollment notes
│       └── wg0-edge.conf.template                # Edge WireGuard config template
├── infra/                                        # Provisioning and network device configuration
│   ├── ansible/                                  # Automation for core/edge provisioning
│   │   ├── inventory/                            # Inventory and group variables
│   │   │   ├── group_vars/
│   │   │   │   ├── all.yml                       # Shared Ansible variables
│   │   │   │   ├── core.yml                      # Core-specific variables
│   │   │   │   └── edge.yml                      # Edge-specific variables
│   │   │   └── hosts.yml.template                # Inventory template
│   │   ├── playbooks/                            # Provisioning entrypoints
│   │   │   ├── core-provision.yml                # Core provisioning playbook
│   │   │   ├── edge-provision.yml                # Edge provisioning playbook
│   │   │   └── wireguard-setup.yml               # WireGuard setup playbook
│   │   └── roles/                                # Ansible roles by subsystem
│   │       ├── martin/tasks/main.yml             # Martin role tasks
│   │       ├── nginx/tasks/main.yml              # Nginx role tasks
│   │       ├── postgres/tasks/main.yml           # PostgreSQL role tasks
│   │       └── wireguard/tasks/main.yml          # WireGuard role tasks
│   ├── rajant/
│   │   └── README.md                             # Rajant mesh configuration notes
│   └── rutx50/
│       ├── README.md                             # Teltonika RUTX50 provisioning notes
│       ├── firewall-zones.rci.template           # Router firewall zone template
│       └── vlan-config.rci.template              # Router VLAN config template
├── paper/                                        # ISCRAM paper source, figures, and evaluation scripts
│   ├── README.md                                 # Paper build/use notes
│   ├── figures/
│   │   └── README.md                             # Figure placeholder notes
│   ├── main.tex                                  # Top-level LaTeX manuscript
│   ├── refs.bib                                  # Bibliography seed file
│   ├── scripts/
│   │   └── generate_plots.py                     # Generates evaluation plots for the paper
│   ├── sections/                                 # Paper sections split by topic
│   │   ├── 00_abstract.tex
│   │   ├── 01_introduction.tex
│   │   ├── 02_related_work.tex
│   │   ├── 03_system_architecture.tex
│   │   ├── 04_synchronization_protocol.tex
│   │   ├── 05_implementation.tex
│   │   ├── 06_evaluation.tex
│   │   ├── 07_discussion.tex
│   │   └── 08_conclusion.tex
│   └── tables/
│       └── README.md                             # Table placeholder notes
├── preview/                                      # HTML previews for the design system
│   ├── brand_overview.html                       # Brand summary preview
│   ├── colors_base.html                          # Base color tokens preview
│   ├── colors_semantic.html                      # Semantic color usage preview
│   ├── components_badges.html                    # Badge component preview
│   ├── components_buttons.html                   # Button component preview
│   ├── components_cards.html                     # Card component preview
│   ├── components_status.html                    # Status component preview
│   ├── spacing_tokens.html                       # Spacing scale preview
│   ├── type_paper.html                           # Paper typography preview
│   └── type_tablet.html                          # Tablet typography preview
├── scripts/                                      # Developer scripts for local emulation and evaluation
│   ├── build-pmtiles.sh                          # Builds PMTiles artifacts
│   ├── dev-down.sh                               # Tears down local dev environment
│   ├── dev-up.sh                                 # Starts local core/edge emulation
│   ├── evaluate-pilot.py                         # Simulated evaluation/pilot runner
│   ├── inject-partition.sh                       # Simulates a network partition during evaluation
│   ├── promote-responder.sh                      # Helper for responder-to-command promotion
│   └── run-migrations.sh                         # Applies database migrations
├── tablet/                                       # Android tablet application
│   ├── README.md                                 # Tablet app overview and network policy
│   ├── build.gradle.kts                          # Top-level Android build config
│   ├── gradle.properties                         # Gradle settings/properties
│   ├── settings.gradle.kts                       # Gradle module settings
│   └── app/
│       ├── build.gradle.kts                      # App module build config
│       └── src/
│           ├── main/
│           │   ├── AndroidManifest.xml           # Android app manifest
│           │   ├── kotlin/se/ltu/rescueois/
│           │   │   ├── RescueOisApp.kt           # Application bootstrap
│           │   │   ├── data/
│           │   │   │   ├── local/
│           │   │   │   │   ├── AppDatabase.kt    # Room database definition
│           │   │   │   │   ├── IncidentDao.kt    # Incident DAO interface
│           │   │   │   │   ├── SiteDao.kt        # Site DAO interface
│           │   │   │   │   └── TileCache.kt      # Local tile cache helper
│           │   │   │   └── remote/
│           │   │   │       ├── EdgeApiClient.kt  # Edge API client
│           │   │   │       └── SyncManager.kt    # Tablet sync coordination
│           │   │   ├── domain/
│           │   │   │   ├── HazardInfo.kt         # Hazard domain model
│           │   │   │   ├── Incident.kt           # Incident domain model
│           │   │   │   ├── Site.kt               # Site domain model
│           │   │   │   └── SyncState.kt          # Sync state model
│           │   │   ├── map/
│           │   │   │   ├── LayerManager.kt       # Map layer management
│           │   │   │   ├── MapLibreWrapper.kt    # MapLibre integration wrapper
│           │   │   │   └── OfflineTileProvider.kt # Offline tile source/provider
│           │   │   └── ui/
│           │   │       ├── IncidentScreen.kt     # Incident-focused screen
│           │   │       ├── MainActivity.kt       # Main Android activity
│           │   │       ├── MapScreen.kt          # Map-centric screen
│           │   │       ├── SiteDetailScreen.kt   # Site details screen
│           │   │       └── SyncStatusBar.kt      # Sync status UI component
│           │   └── res/values/
│           │       └── strings.xml               # App string resources
│           └── test/
│               └── kotlin/se/ltu/rescueois/
│                   ├── SyncManagerTest.kt        # Sync manager tests
│                   └── TileCacheTest.kt          # Tile cache tests
└── ui_kits/                                      # Conceptual UI kits and prototypes
    └── tablet/
        ├── README.md                             # Tablet UI kit overview
        ├── FleetView.jsx                         # Fleet screen prototype
        ├── IncidentView.jsx                      # Incident overview prototype
        ├── OutboxView.jsx                        # Outbox screen prototype
        ├── PromoteModal.jsx                      # Command-promotion modal prototype
        ├── SitePlanView.jsx                      # Site plan screen prototype
        ├── TopBar.jsx                            # Shared top bar/status component
        └── index.html                            # Interactive UI kit entrypoint
```

## Summary

- `core/`, `edge/`, and `tablet/` contain the system implementation scaffold for the three operational tiers.
- `docs/`, `infra/`, and `scripts/` support architecture, provisioning, and local emulation.
- `paper/`, `preview/`, and `ui_kits/` hold the research paper, design-system previews, and conceptual UI artifacts.
