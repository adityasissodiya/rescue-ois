# Security Model

Rescue OIS layers defense across the network, transport, host, application, and device-management planes. It does **not** introduce a new identity stack — it integrates with the existing IdP / CA used by the Swedish rescue service organization.

## Per-Vehicle VLAN Isolation (RUTX50)

Each vehicle's RUTX50 enforces zone-based firewalling between the five VLANs (MGMT, EDGE-SVC, OPS-TABLET, SENSOR, MAINT). The OPS-TABLET zone allows only HTTPS egress to the K430's ops-api endpoint — no DNS, no internet, no inter-tablet traffic. See [network-topology.md](network-topology.md) for the full firewall matrix.

## Encrypted Overlay (WireGuard)

All vehicle ↔ core communication runs over a WireGuard overlay (`10.252.0.0/24`). Each vehicle K430 holds a per-device WG private key provisioned during enrollment. Core peer keys are pinned in the K430 configuration. Compromise of a single device requires only revocation of its peer entry on the core (see `docs/runbooks/device-revocation.md`).

## Host-Level Firewall (nftables on K430)

The K430 enforces a default-deny nftables policy. Only the following are permitted:

- Inbound HTTPS on EDGE-SVC from OPS-TABLET (ops-api)
- Inbound HTTPS on the mesh interface from peer K430s (syncd accept)
- Outbound WireGuard UDP to the core peer
- Loopback freely

`edge/nftables/nftables.conf.template` is the canonical policy.

## Tablet Network Policy

Tablets are managed by **Knox Manage** and locked into a single network profile:

- No internet access
- No mesh access
- Outbound traffic limited to the local K430's ops-api over HTTPS with the K430's pinned certificate
- App allowlist enforced; sideloading disabled in field mode

## Mutual Authentication

- **Tablet ↔ ops-api:** mTLS, tablet client cert issued by the existing organizational CA, validated by ops-api via the authority chain.
- **K430 ↔ K430 (mesh):** mTLS over the mesh interface, peer certificates pinned per incident.
- **K430 ↔ core:** WireGuard authentication + TLS to sync-api.

## Audit Trail

Every authoritative state change is recorded:

- `ops-api`, `syncd`, `sync-api`, `audit-api` write structured audit events.
- Edge audit entries are batched by `audit-forwarder` and pushed to core `audit-api`, where they land in `audit.events`.
- Core retains audit events according to organizational retention policy.

## Identity & CA

Rescue OIS does not issue identities. It consumes:

- Existing organizational IdP for operator identity (SAML / OIDC, depending on the integration)
- Existing organizational CA for device, service, and operator certificates

This avoids a parallel identity universe and keeps revocation in one place.
