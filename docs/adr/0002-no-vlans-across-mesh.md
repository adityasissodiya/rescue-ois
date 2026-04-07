# ADR-0002: No User VLANs Across the Rajant Mesh

## Status

Accepted

## Context

The Rajant Hawk mesh provides inter-vehicle wireless transit. It is tempting to bridge user VLANs (OPS-TABLET, SENSOR) across the mesh so devices on one vehicle can talk to devices on another vehicle directly. In practice, stretching VLANs over a mobile multi-hop wireless mesh causes broadcast storms (ARP, mDNS, IPv6 ND), unmanageable routing as topology shifts, and difficult-to-debug failure modes when nodes partition and reconverge.

## Decision

The Rajant mesh is **transit-only**. Each vehicle's user VLANs (MGMT, EDGE-SVC, OPS-TABLET, SENSOR, MAINT) terminate on its own RUTX50. Inter-vehicle data exchange happens at the **application layer** between K430s — primarily `syncd` posting outbox batches to the command K430's accept endpoint over HTTPS, on top of the mesh's L3 transit (`10.253.0.0/16`).

## Consequences

**Positive:**

- Clean L2 boundaries per vehicle; no broadcast storms across the mesh.
- Each vehicle's tablet/sensor population is isolated and predictable.
- Failure modes are localized to the affected vehicle, not the whole mesh.

**Negative:**

- Inter-vehicle data exchange must always pass through application code (syncd / ops-api). There is no transparent "tablet on vehicle A talks to printer on vehicle B" path.
- Service discovery between vehicles is not via mDNS but via the configured peer list maintained by `syncd`.
