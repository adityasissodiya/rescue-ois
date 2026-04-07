# edge/nftables

Host-level firewall for the vehicle K430. Default-deny inbound; only the
following ingress paths are allowed:

- HTTPS from the EDGE-SVC VLAN (tablets via RUTX50 → Nginx → ops-api)
- HTTPS from the mesh interface (peer K430 syncd traffic)
- WireGuard UDP from the core peer

`nftables.conf.template` is rendered at provisioning time by Ansible. The
rendered file lives at `/etc/nftables.conf` on the K430.
