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
   The script inserts a new row into `incident.command_epoch` on this edge's local Postgres (monotonically advancing `epoch_id` — this is the fencing act), then flips `EDGE_ROLE` from `responder` to `command` and restarts `syncd` so `accept.init_epoch_cache()` picks up the new epoch. It appends a JSONL promotion record for the evaluation harness. Note the epoch is **local to this edge**; no other edge is consulted or informed.
4. **Verify** — new command K430 logs `accept` activity; `incident.journal` accepts new events; `forward` posts to core resume.
5. **Notify peers** — out-of-band, and **manual**. There is no peer discovery: each responder's `COMMAND_PEER_URL` is a static environment variable set once when the stack is brought up (`edge/syncd/src/config.py`, `scripts/dev-up.sh`). To repoint responders you must rewrite `COMMAND_PEER_URL` for each one and restart its `syncd`; until you do, responders keep pushing to the old command and their outboxes accumulate.
6. **Audit** — promotion event is automatically recorded by `audit-forwarder`. Operator should add a free-text note.

## Post-failover

If the original command vehicle reappears, it must be **demoted** before reconnecting (`EDGE_ROLE=responder`) to prevent split-brain. This demotion is entirely manual and operator-enforced: `scripts/promote-responder.sh` inspects only its **own** `EDGE_ROLE` and never contacts any other edge, so it cannot detect another live command. Its only safeguard is the interactive prompt requiring the operator to type `yes` to "Has the previous command vehicle been confirmed unreachable?" (bypassable with `PROMOTION_NON_INTERACTIVE=1`). As the script's own header warns, running it while the previous command is reachable and still accepting writes will fork `incident.journal`.
