# Runbook: Device Revocation

Revoke a compromised, lost, or decommissioned device (tablet, K430, or maintenance laptop).

## Tablet

1. **Knox Manage** — issue remote wipe; revoke enrollment.
2. **CA** — revoke the tablet's mTLS client certificate via the organizational CA. Publish CRL / OCSP update.
3. **ops-api** — verify all K430s pick up the updated CRL on the next refresh window.
4. **Audit** — record revocation event.

## K430 (Vehicle Edge)

1. **WireGuard** — remove the K430's peer public key from the core WG configuration. Reload `wg-quick`.
2. **CA** — revoke any service certificates issued to that K430.
3. **Mesh** — remove the paired Hawk node from BC|Commander.
4. **Fleet inventory** — mark vehicle out of service in the fleet management system.
5. **Audit** — record revocation event with operator identity.

## Maintenance laptop

1. **CA** — revoke the device certificate.
2. **RUTX50 MAINT VLAN** — confirm the laptop's MAC is no longer present in any vehicle's MAINT zone DHCP lease list.
3. **Audit** — record revocation event.
