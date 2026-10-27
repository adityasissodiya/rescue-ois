# Documentation

These documents are about the prototype: its design, the decisions behind it, how to
run it, and how the target deployment would be set up. The succession testbed documents
itself in [`../testbed/README.md`](../testbed/README.md), and the manuscript is on branch
`tcps`.

Many documents describe the deployment the prototype was designed for, on vehicle
hardware, more than the code that exists. Each one below is labelled:

- **Current**: describes the code on this branch.
- **Target design**: describes the intended deployment. None of it has been deployed or
  measured; the prototype runs as a Docker Compose emulation on one host.
- **Historical**: kept for the record.

## Start With

| Document | Status | Contents |
| --- | --- | --- |
| [prototype.md](prototype.md) | Current | Running the prototype, re-running its evaluation and baselines, formal checks, what it does not do, troubleshooting |
| [architecture/README.md](architecture/README.md) | Current; the hardware is target design | The three tiers, the single design rule, the evidence boundary |
| [what-fails-without-our-solution.md](what-fails-without-our-solution.md) | Current | Why the prototype has a single command writer, what its evidence covers, which tests are missing |

## Architecture

| Document | Status | Contents |
| --- | --- | --- |
| [architecture/sync-protocol.md](architecture/sync-protocol.md) | Current, except flow 1 (not implemented) and the tablet side of flow 3 (a scaffold) | The six synchronization flows |
| [architecture/security-model.md](architecture/security-model.md) | Target design; its threat model also applies to the prototype | Network, transport, device and identity controls; residual risks |
| [architecture/network-topology.md](architecture/network-topology.md) | Target design | IP plan, VLANs, firewall matrix |

## Decisions

| Record | Status |
| --- | --- |
| [ADR-0001: single incident writer](adr/0001-single-incident-writer.md) | Accepted; implemented |
| [ADR-0002: no user VLANs across the mesh](adr/0002-no-vlans-across-mesh.md) | Accepted; target design |
| [ADR-0003: PMTiles over MBTiles](adr/0003-pmtiles-over-mbtiles.md) | Accepted; target design (no edge code serves PMTiles yet) |
| [ADR-0004: promotion authority model](adr/0004-promotion-authority-model.md) | Partially implemented: command epochs yes, the signed promotion token no |
| [ADR-0005: revocation under partition](adr/0005-revocation-under-partition.md) | Proposed; not implemented |
| [ADR-0006: one source of evaluation data](adr/0006-evaluation-harness-data-source.md) | Accepted; implemented |

New records start from [adr/template.md](adr/template.md).

## Runbooks

| Document | Status | Contents |
| --- | --- | --- |
| [runbooks/command-failover.md](runbooks/command-failover.md) | Current | Promoting a responder to command with `scripts/promote-responder.sh`, and what happens to the old command |
| [runbooks/incident-bootstrap.md](runbooks/incident-bootstrap.md) | Target design (core serves `/sync/bootstrap`; no edge code fetches it) | Opening an incident and designating its command vehicle |
| [runbooks/device-revocation.md](runbooks/device-revocation.md) | Target design | Revoking a tablet, a vehicle node or a maintenance laptop |

## Deployment

All target design, for the hardware in [architecture/README.md](architecture/README.md);
the templates they use are in [`../infra/`](../infra/).

| Document | Contents |
| --- | --- |
| [deployment/core-setup.md](deployment/core-setup.md) | The regional core, as a pair of hosts |
| [deployment/vehicle-edge-setup.md](deployment/vehicle-edge-setup.md) | One vehicle edge: K430, RUTX50, Rajant Hawk |
| [deployment/mesh-commissioning.md](deployment/mesh-commissioning.md) | The Rajant mesh (Hawk and Sparrow radios) |
| [deployment/tablet-enrollment.md](deployment/tablet-enrollment.md) | Field tablets: Knox Manage, app, client certificate |

## Historical

| Document | Contents |
| --- | --- |
| [submission-checklist.md](submission-checklist.md) | Checklist for the anonymized archive of a double-blind submission. Reuse it only if a venue asks for an anonymized artifact again. |
