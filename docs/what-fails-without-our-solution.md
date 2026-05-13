# What Fails Without Authority-Aligned Linearization

Rescue OIS is not a general offline data store, generic mesh platform, or
substitute for Raft. The central boundary is operational authority:
non-authority data can be cached, queued, and forwarded, but authority-bearing
incident decisions must be linearized at the current command authority.

Without that boundary, a rescue-service incident system tends toward one of two
wrong failure modes:

- **Quorum/cloud-dependent authority.** Command work blocks when the regional
  core or enough vehicle replicas are unreachable, even if the designated
  command vehicle and its local storage are alive.
- **Uncontrolled local-first authority.** Disconnected actors make
  authority-bearing decisions locally, then reconcile conflicting assignments,
  status transitions, or hazards after the fact.

The proposed contract separates state classes:

- reference data and packages are cached locally;
- field observations are durably inserted into a responder outbox before local
  acknowledgement;
- retries are made safe with `client_event_id` idempotency;
- authority-bearing incident events receive `event_seq` only at the command
  writer;
- audit and core backhaul are forwarded later;
- command promotion is manual and must fence stale authority.

## Concrete Failure Modes

- Cloud-only or regional-core-first operation makes WAN recovery a prerequisite
  for field usefulness.
- Pure local-first or CRDT-style operation cannot generically merge
  non-commutative command decisions without changing their operational meaning.
- Vehicle-quorum consensus can block command progress under common responder
  partitions.
- Multi-primary disconnected writes make audit and ordering ambiguous for
  safety-relevant state.
- A non-durable responder outbox can acknowledge observations that later vanish.
- Missing `client_event_id` idempotency lets retries create duplicate journal
  rows or consume multiple `event_seq` values.
- Weak promotion without fencing can create two command authorities and fork the
  incident journal.
- Stretching tablet/user VLANs across the mesh makes routing, discovery, and
  security boundaries harder to reason about under churn.

## Evidence Boundary

The current Docker Compose evaluation supports the implemented service path, not
a production deployment. It covers responder outbox forwarding, command-side
idempotent sequencing, command-to-core backfill, duplicate replay, throughput,
WAN recovery, and a direct command `syncd` accept-path partition experiment.

The direct command accept-path partition artifact measures command-originated
writes submitted directly to the implemented command `syncd`
`/accept/event-batch` endpoint while a responder `syncd` process is isolated. It
does not prove end-to-end tablet operation, Android persistence, physical Rajant
mesh behavior, WireGuard/mTLS overhead, or responder outbox replay during the
partition.

Model-level evidence covers the central safety failure: weak promotion without
fencing produces a `SingleAuthority` counterexample and can produce a
`NoForkedJournal` violation. The running services do not yet implement durable
`command_epoch` storage or stale-epoch rejection.

## Test Gaps To Keep Visible

The repository should keep these missing validations visible until they are
implemented:

- `test_responder_partition_outbox_accumulates_then_replays`
- `test_crash_after_local_outbox_insert_before_forward_preserves_event`
- `test_crash_after_command_append_before_ack_does_not_duplicate_on_retry`
- `test_crash_before_forwarded_mark_retries_without_duplicate_journal_row`
- `test_stale_command_epoch_rejected_after_promotion`
- `test_promotion_record_required_before_new_command_accepts_events`
- `test_no_two_command_writers_for_same_incident_epoch`

The Raft baseline is only a quorum-progress illustration. It is not a
workflow-equivalent baseline for the Rescue OIS application.
