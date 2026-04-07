# core/wireguard

Templates for the regional core's WireGuard overlay (`10.252.0.0/24`).

`wg0-core.conf.template` is rendered into `wg0-core.conf` at provisioning time
by the Ansible `wireguard` role. The rendered file is **never** committed.

Per-vehicle peer entries are added when a new K430 is enrolled (see
`docs/deployment/vehicle-edge-setup.md`).
