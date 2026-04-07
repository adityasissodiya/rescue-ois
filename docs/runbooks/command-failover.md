# Runbook: Command Vehicle Failover

How to promote a responder K430 to command role when the original command vehicle is lost or partitioned.

## Trigger

- Heartbeat timeout from command K430 over mesh (default: 90 s)
- Operator decision (vehicle relocating, rotating crew, etc.)

## Preconditions

- A responder K430 has the latest replicated incident journal slice (verify `event_seq`)
- Operator has authorization to perform promotion (audited)

## Steps

1. **Confirm command vehicle is unreachable** — `syncd` log shows repeated post failures; mesh topology view confirms.
2. **Choose successor** — pick the responder with the highest `event_seq` known.
3. **Run promotion script** — on the chosen K430:
   ```bash
   ./scripts/promote-responder.sh
   ```
   The script flips `EDGE_ROLE` from `responder` to `command` and restarts `syncd`.
4. **Verify** — new command K430 logs `accept` activity; `incident.journal` accepts new events; `forward` posts to core resume.
5. **Notify peers** — out-of-band: tell other vehicles to point at the new command. (`syncd` peer discovery handles this automatically once the role flip is observed.)
6. **Audit** — promotion event is automatically recorded by `audit-forwarder`. Operator should add a free-text note.

## Post-failover

If the original command vehicle reappears, it must be **demoted** before reconnecting (`EDGE_ROLE=responder`) to prevent split-brain. The promotion script refuses to run if it detects another live command on the same incident.
