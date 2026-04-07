# Network Topology

This document specifies the IP addressing plan, VLANs, and firewall matrix for Rescue OIS.

## Address Plan

### Regional Core Subnets

| Purpose                | CIDR             | Notes                              |
|------------------------|------------------|------------------------------------|
| Core management        | `10.10.100.0/24` | Out-of-band mgmt, iLO, switches    |
| Core services A        | `10.10.110.0/24` | cop-core-a stack                   |
| Core services B        | `10.10.120.0/24` | cop-core-b stack (HA pair)         |
| Core publication egress| `10.10.130.0/24` | Publication / static serving       |

### WireGuard Overlay

| Purpose         | CIDR              |
|-----------------|-------------------|
| WG transport    | `10.252.0.0/24`   |

Each vehicle K430 receives a unique `/32` from the overlay (e.g. `10.252.0.10`, `10.252.0.11`, ...).

### Rajant Mesh

| Purpose         | CIDR              |
|-----------------|-------------------|
| Mesh underlay   | `10.253.0.0/16`   |

The mesh is **transit-only**. No user VLANs are stretched across it. See [ADR-0002](../adr/0002-no-vlans-across-mesh.md).

### Per-Vehicle VLAN Template

Each vehicle uses `172.31.<vehicle_id>.0/24` carved into the following five VLANs. The `vehicle_id` octet is unique per vehicle.

| VLAN ID | Name        | CIDR (vehicle 5 example) | Purpose                                 |
|---------|-------------|---------------------------|-----------------------------------------|
| 10      | MGMT        | `172.31.5.0/27`           | Management plane (RUTX50, K430 mgmt)   |
| 20      | EDGE-SVC    | `172.31.5.32/27`          | K430 service plane (ops-api, syncd)    |
| 30      | OPS-TABLET  | `172.31.5.64/26`          | Field tablets (HTTPS to ops-api only)  |
| 40      | SENSOR      | `172.31.5.128/27`         | Sensors (drones, gas, telemetry)       |
| 50      | MAINT       | `172.31.5.160/27`         | Maintenance laptop (temporary)         |

## Firewall Matrix (RUTX50, per-vehicle)

| From \\ To  | MGMT | EDGE-SVC | OPS-TABLET | SENSOR | MAINT | WG Core | Mesh |
|------------|------|----------|------------|--------|-------|---------|------|
| MGMT       | —    | allow    | deny       | deny   | deny  | allow   | deny |
| EDGE-SVC   | deny | —        | reply only | reply  | deny  | allow   | allow|
| OPS-TABLET | deny | https    | —          | deny   | deny  | deny    | deny |
| SENSOR     | deny | tls/api  | deny       | —      | deny  | deny    | deny |
| MAINT      | ssh  | deny     | deny       | deny   | —     | deny    | deny |

Rules:

- Tablets only reach EDGE-SVC over HTTPS to the ops-api endpoint. Nothing else.
- Sensors push to a dedicated EDGE-SVC ingest port over TLS only.
- Only the K430 (EDGE-SVC) and the management host can reach the WireGuard overlay to core.
- The Rajant mesh is reachable only from EDGE-SVC and only carries inter-K430 application traffic.

See `infra/rutx50/firewall-zones.rci.template` for the executable zone configuration.
