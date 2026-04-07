# Rajant Mesh Commissioning

Configures Rajant Hawk and Sparrow radios for the inter-vehicle mesh, managed via BC|Commander.

## Steps

1. **Inventory** — record serial numbers, MAC addresses, and assigned mesh node IDs in BC|Commander.
2. **Apply baseline config** — load the regional `mesh-baseline.bcprofile` which sets:
   - Frequency plan (locale-specific)
   - Mesh PSK rotation policy
   - QoS classes (sync traffic prioritized over best-effort)
   - L3-only operation (no VLAN bridging — see [ADR-0002](../adr/0002-no-vlans-across-mesh.md))
3. **Provision per-vehicle Hawk** — assign vehicle-unique mesh address from `10.253.0.0/16`.
4. **Stationary Sparrow nodes** (optional) — for fixed operational hubs / tents.
5. **Verify** — BC|Commander topology view; ping test between vehicles; throughput test.

## TODO

- [ ] Document mesh PSK rotation procedure
- [ ] Document Sparrow placement guidance
