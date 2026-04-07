# Vehicle Edge Setup: K430 + RUTX50 + Rajant Hawk

This runbook provisions a single vehicle edge (one K430 server, one RUTX50 router, one Rajant Hawk radio).

## Hardware checklist

- Klas Telecom Voyager K430 (compute)
- Teltonika RUTX50 (router with cellular fallback)
- Rajant Hawk (mesh radio)
- Ruggedized Ethernet harness, vehicle DC supply

## Steps

1. **Rack & cable** — connect K430 to RUTX50 EDGE-SVC port; tablets to RUTX50 OPS-TABLET ports; Hawk to RUTX50 mesh-uplink port.
2. **RUTX50 base config** — flash latest firmware, apply `infra/rutx50/vlan-config.rci.template` and `infra/rutx50/firewall-zones.rci.template` (substituting `vehicle_id`).
3. **Hawk config** — apply mesh PSK and routing role from BC|Commander; see [mesh-commissioning.md](mesh-commissioning.md).
4. **K430 base OS** — Debian 12 minimal, SSH key auth, chrony.
5. **Ansible** — run `infra/ansible/playbooks/edge-provision.yml` against the host in `[edge_responder]` (or `[edge_command]` if this vehicle is the designated command for the upcoming incident).
6. **Migrations** — apply `edge/db/migrations/*.sql`.
7. **Docker Compose** — start `edge/docker-compose.yml` with `EDGE_ROLE=responder` (default) or `EDGE_ROLE=command`.
8. **WireGuard enrollment** — render `edge/wireguard/wg0-edge.conf.template` with the device keypair, get the peer entry added on the core.
9. **Smoke test** — verify `/health` for ops-api, syncd, package-cache, audit-forwarder; pull a baseline package via syncd.

## TODO

- [ ] Knox Manage enrollment of paired tablets for this vehicle
- [ ] mTLS client cert distribution to tablets
- [ ] Promotion drill (responder → command)
