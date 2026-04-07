# edge/wireguard

WireGuard client templates for the vehicle K430. Each K430 holds a unique
keypair generated at enrollment; the public key is added as a peer entry on
the regional core.

`wg0-edge.conf.template` is rendered into `wg0-edge.conf` at provisioning time.
The rendered file is **never** committed.
