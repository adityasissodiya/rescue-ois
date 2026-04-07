# Core Setup: cop-core-a / cop-core-b

This runbook provisions the regional core HA pair.

## Prerequisites

- Two physical or virtual hosts (`cop-core-a`, `cop-core-b`) on the core management VLAN
- Ansible control node with SSH access to both
- Existing organizational CA for service certificates
- WireGuard server keypair generated and stored in vault

## Steps

1. **Bootstrap OS** — Debian 12 minimal install, SSH key auth only, time sync (chrony) pointed at organizational NTP.
2. **Run Ansible playbook** — `infra/ansible/playbooks/core-provision.yml` against the `[core]` group.
3. **Initialize PostgreSQL** — apply `core/db/migrations/*.sql` in order via `scripts/run-migrations.sh`.
4. **Deploy Docker Compose stack** — `core/docker-compose.yml`. Verify `/health` endpoints for sync-api, audit-api, feed-importer, publisher.
5. **Configure WireGuard** — render `core/wireguard/wg0-core.conf.template` with the server keys and the per-vehicle peer list.
6. **Configure Nginx** — install organizational CA bundle, deploy `core/nginx/nginx.conf`.
7. **Smoke test** — pull `sync-api` from a test vehicle peer, verify TLS, verify `manifest.json` retrieval.

## TODO

- [ ] PostgreSQL streaming replication between cop-core-a and cop-core-b
- [ ] Backup procedure for PostGIS volume
- [ ] Failover runbook between A and B
