# Runbook: Incident Bootstrap

How to open a new incident and designate a command vehicle.

## Preconditions

- Core is reachable from the dispatching workstation
- The chosen command vehicle K430 is online (over WG to core, or at least reachable via the mesh from a vehicle that is)

## Steps

1. **Create incident in core** — operator submits incident metadata (name, AOI polygon, initial responder roster).
2. **Assign command vehicle** — set `command_edge_id = <vehicle K430 ID>` on the incident record.
3. **Wait for bootstrap** — command K430's `syncd` polls `GET /sync/bootstrap?incident_id=...` and pulls the incident bundle (AOI, plan refs, hazard subset, attachments).
4. **Verify** — on the command K430, `incident.journal` exists and is empty, `incident.state` reflects the bootstrap.
5. **Promote `EDGE_ROLE`** — should already be `command` on this vehicle; verify with `docker compose exec syncd env | grep EDGE_ROLE`.
6. **Notify responders** — over the mesh, responder syncd processes detect the new command peer and begin posting outbox batches.

## Failure modes

- **Core unreachable:** command vehicle bootstraps from cached master data; reconciles when WG returns. Audit notes the offline bootstrap.
- **Command vehicle unreachable from core:** dispatch via mesh from a peer vehicle that has WG; same flow.
