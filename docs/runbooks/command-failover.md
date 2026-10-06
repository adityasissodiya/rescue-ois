# Runbook: Command Vehicle Failover

How to promote a responder K430 to the command role when the command vehicle is lost or cut
off. This is the procedure the prototype implements: immediate promotion through the
regional core, with a lease on the old command (policy S1 in the paper). It needs core.
Promotion is not possible while the candidate cannot reach core.

## Trigger

- The command vehicle has gone silent: `syncd` posts to it fail, and the mesh topology view
  no longer shows it.
- An operator decision (vehicle relocating, rotating crew, and so on).

The prototype detects neither on its own. An operator decides.

## Preconditions

- The candidate can reach the regional core (`CORE_API_URL`). The script aborts otherwise and
  changes nothing.
- The operator is authorized to promote (audited) and has confirmed that the previous command
  vehicle is unreachable.

The script checks for itself that the candidate holds the complete journal prefix, so there
is no need to compare `event_seq` by hand.

## Steps

1. **Confirm the command vehicle is unreachable.** The `syncd` log shows repeated post
   failures, and the mesh topology view confirms it.
2. **Choose the successor.** Any responder that reaches core will do; the script fetches the
   journal prefix itself.
3. **Run the promotion script** for the incident:
   ```bash
   INCIDENT_ID=<incident> EDGE_COMPOSE_PROJECT=<candidate project> ./scripts/promote-responder.sh
   ```
   It asks for the previous command vehicle's id and for confirmation that it is unreachable
   (or set `PROMOTION_NON_INTERACTIVE=1` with `PREVIOUS_COMMAND_VEHICLE_ID` and
   `PREVIOUS_COMMAND_UNREACHABLE=yes`). Then, in order, it:
   1. bootstraps the incident-journal prefix from core into the candidate, and aborts without
      changing anything if the prefix is not contiguous;
   2. asks core for a new command epoch, and aborts if core cannot be reached. Core's insert is
      the serialization point, so two concurrent promotions cannot receive the same epoch;
   3. mirrors that epoch into the candidate's local `incident.command_epoch`, recreates the
      candidate's `syncd` with `EDGE_ROLE=command` (keeping its published port), and waits for
      it to report healthy;
   4. repoints every other responder edge it finds (or those listed in `RESPONDER_PROJECTS`) at
      the new command and recreates their `syncd`;
   5. appends a JSONL promotion record for the evaluation harness.
4. **Verify.** The new command logs `accept` activity, `incident.journal` accepts new events,
   and `forward` posts to core resume.
5. **Tell people, out of band.** The script repoints the responder edges it can reach in the
   Docker emulation. A responder it could not reach keeps pushing to the old command until it
   is repointed by hand: rewrite its `COMMAND_PEER_URL` and restart its `syncd`.
6. **Audit.** `audit-forwarder` records the promotion event. Add a free-text note.

## What happens to the old command vehicle

The script never contacts the old command vehicle and cannot tell whether it is still alive.
Two mechanisms fence it:

- **Lease.** Its lease renews only on a successful round trip to core. Cut off from core, it
  keeps accepting authority-bearing writes until the lease lapses (`lease_window_s`, 90 s by
  default), and then refuses them. Until then, two vehicles can accept decisions. An edge that
  never renewed a lease at all is not fenced by it.
- **Self-demotion.** When it reaches core again and core rejects a forwarded batch as stale
  (`stale_epoch`, `not_epoch_holder` or `forked_sequence`), it marks itself demoted, stops
  forwarding, and refuses further writes.

Its decisions that never reached core stay in its local journal. The new command continued
numbering from core's prefix, so those decisions collide on `event_seq`. Nothing reconciles
them: review them by hand. Set `EDGE_ROLE=responder` on the old vehicle before using it again.
