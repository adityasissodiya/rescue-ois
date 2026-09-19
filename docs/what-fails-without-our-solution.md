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
`NoForkedJournal` violation.

Durable `command_epoch` storage and stale-epoch rejection **are** implemented on
the single-edge service path. Migration `edge/db/migrations/005_command_epoch.sql`
creates `incident.command_epoch` and the `incident.current_epoch` view;
`edge/syncd/src/accept.py` caches the epoch (`init_epoch_cache`,
`refresh_epoch_cache`) and validates `X-Command-Epoch` in
`validate_request_epoch`, rejecting stale, future, and missing values with HTTP
409 before any journal write; each accepted row is stamped with its
`command_epoch`. Unit-covered by `edge/syncd/tests/test_accept_epoch.py` and
measured by `scripts/evaluate-fenced-promotion.py`.

What remains unimplemented is genuine **multi-edge** fenced promotion: an
isolated former command edge learning that its epoch is stale, and a newly
promoted edge obtaining the journal prefix from core (`edge/syncd/src/pull.py` is
a no-op stub and `core/sync-api` exposes no journal-row endpoint). Rejection
today happens at the current command's own acceptor, not at the stale writer.

## Test Gaps To Keep Visible

All of the tests below live in
`edge/syncd/tests/test_partition_and_boundary_visibility.py`. Four are now
implemented as opt-in integration tests (`RESCUE_OIS_INTEGRATION_TESTS=1`, which
starts or reuses the local Compose stack):

- `test_responder_partition_outbox_accumulates_then_replays`
- `test_crash_after_local_outbox_insert_before_forward_preserves_event`
  (drives `scripts/evaluate-outbox-crash-restart.py`)
- `test_stale_command_epoch_rejected_after_promotion`
- `test_promotion_record_required_before_new_command_accepts_events`

Three remain genuinely unimplemented and are kept visible as
`@pytest.mark.xfail(strict=True)`, so they fail the suite if they ever start
passing silently:

- `test_no_two_command_writers_for_same_incident_epoch` — cross-edge two-writer
  race; model-only, see the strict TLA+ `SingleCommand` property
- `test_crash_after_command_append_before_ack_does_not_duplicate_on_retry` —
  mid-flight ack-loss crash injection not automated
- `test_crash_before_forwarded_mark_retries_without_duplicate_journal_row` —
  mid-flight forwarded-mark crash injection not automated

The Raft baseline is only a quorum-progress illustration. It is not a
workflow-equivalent baseline for the Rescue OIS application.
