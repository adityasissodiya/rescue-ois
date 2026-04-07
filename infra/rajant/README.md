# infra/rajant

Notes on configuring Rajant Hawk and Sparrow nodes via BC|Commander.

## Profile

Rescue OIS uses a **transit-only** mesh profile. The mesh provides L3 transit
between vehicle K430s; user VLANs are **not** stretched across it (see
[ADR-0002](../../docs/adr/0002-no-vlans-across-mesh.md)).

## Required settings

- **Frequency plan:** locale-specific, configured by BC|Commander
- **PSK rotation:** scheduled per organizational policy
- **QoS:** sync traffic (TCP/443 between K430 mesh interfaces) prioritized over best-effort
- **L3 only:** no VLAN bridging across the mesh
- **Mesh address space:** `10.253.0.0/16`

## Commissioning

See [../../docs/deployment/mesh-commissioning.md](../../docs/deployment/mesh-commissioning.md).
