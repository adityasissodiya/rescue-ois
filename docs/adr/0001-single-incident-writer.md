# ADR-0001: Single Incident Writer (Command Vehicle)

## Status

Accepted

## Context

The Rescue OIS edge tier consists of multiple vehicle K430s that may be operating concurrently on the same incident, each with field tablets writing edits. PostgreSQL logical replication is one-way and does not provide automatic conflict resolution. Allowing every vehicle to write directly to `incident.journal` and `incident.state` would require multi-master conflict resolution — either via CRDTs, application-layer merges, or external coordination — all of which add operational complexity that is hard to reason about during a real incident.

## Decision

Only **one K430 per incident** writes to `incident.journal` and `incident.state`. That K430 is designated as the **command vehicle** at incident bootstrap. All other K430s operate in **responder** mode: they accept tablet edits into `outbox.device_outbox` and forward them to the command K430 over the Rajant mesh. The command K430 sequences incoming events with a monotonically increasing `event_seq` and forwards the resulting journal to the regional core.

## Consequences

**Positive:**

- The conflict model collapses to "single writer per incident" — easy to reason about and audit.
- Event ordering is unambiguous because `event_seq` is assigned by exactly one process.
- Forwarding to core is straightforward (last-acked sequence number resume).

**Negative:**

- The command vehicle is a single point of write availability for the incident. Recovery requires an explicit promotion procedure (`scripts/promote-responder.sh`) and a documented runbook (`docs/runbooks/command-failover.md`).
- Responder vehicles must persist outbox entries durably until acked.
- Promotion must be auditable to prevent split-brain.
