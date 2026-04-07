# infra/rutx50

Reference templates for the per-vehicle Teltonika RUTX50 router.

These files document the VLAN and firewall zone configuration that maps to
the five-VLAN model in [docs/architecture/network-topology.md](../../docs/architecture/network-topology.md).
They are **not** directly executable — they are loaded via the RUTX50 RCI /
UCI batch interface during provisioning.

`vehicle_id` is substituted at provisioning time to produce a unique
`172.31.<id>.0/24` block per vehicle.
