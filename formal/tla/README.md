# Rescue OIS - TLA+ Safety Verification

This directory contains the TLA+ specification of the Rescue OIS
synchronisation protocol's safety properties, and the TLC
configurations that drive the verification.

The model is single-journal: one incident journal whose write authority
is held by at most one vehicle at a time. Each vehicle keeps a local
cursor for the next `event_seq` to allocate. Strict promotion atomically
revokes the prior authority, allocates a fresh fence epoch, records the
journal prefix at that epoch, and refreshes the new authority's cursor.
Weak promotion does not allocate a fence epoch or revoke unreachable old
authorities, leaving two vehicles with cursors pointing at the same
journal position when the new command was promoted while partitioned from
the prior command.

The network is abstracted as a symmetric `partition` relation plus
`PartitionPair`/`HealPair` transitions. The model does not include an
in-flight message set; the checked properties are safety invariants over
global authority, epoch, and journal state rather than liveness properties
over message delivery.

## Files

- `RescueOIS.tla` - protocol specification.
- `RescueOIS_small.cfg` - strict smoke config.
- `RescueOIS_medium.cfg` - strict medium config used for the paper's main
  formal-evidence number.
- `RescueOIS_large.cfg` - strict best-effort large config under the
  30-minute per-config cap.
- `RescueOIS_strict.cfg` - alias of the small strict config for backward
  compatibility with earlier commands.
- `RescueOIS_weak.cfg` - weak protocol with all invariants enabled;
  surfaces the `SingleAuthority` counterexample.
- `RescueOIS_weak_epoch.cfg` - weak protocol with role-level authority
  invariants suppressed so TLC surfaces the `EpochAuthorityCoupling`
  counterexample directly.
- `RescueOIS_weak_journal.cfg` - weak variant with authority and
  epoch-coupling invariants suppressed so BFS continues to the
  `NoForkedJournal` counterexample: the canonical two-vehicles-commit-at-
  same-seq trace.
- `RUNS.md` - recorded TLC results for the strict and weak configs.
- `weak_counterexample.md` - prose summaries of the weak traces.

## Invariants

- `SingleAuthority` -- at most one vehicle holds write authority at any
  time.
- `EpochAuthorityCoupling` -- for every epoch, at most one vehicle holds
  authority at that epoch.
- `DurabilityAcrossPromotion` -- each journal snapshot recorded when an
  epoch is allocated remains a prefix of the current journal.
- `NoForkedJournal` -- distinct positions in the incident journal carry
  distinct `event_seq` values.
- `LocalIdempotency` -- no `cid` appears twice in the journal.
- `SingleCommand` -- at most one vehicle in the `command` role.

## Running

Requires Java and the TLA+ tools. Set `TLA_TOOLS_JAR` to the path of
`tla2tools.jar`.

```bash
java -jar "$TLA_TOOLS_JAR" -workers auto \
    -config RescueOIS_small.cfg RescueOIS.tla
java -jar "$TLA_TOOLS_JAR" -workers auto \
    -config RescueOIS_medium.cfg RescueOIS.tla
java -jar "$TLA_TOOLS_JAR" -workers auto \
    -config RescueOIS_large.cfg RescueOIS.tla
java -jar "$TLA_TOOLS_JAR" -workers auto \
    -config RescueOIS_weak.cfg RescueOIS.tla
java -jar "$TLA_TOOLS_JAR" -workers auto \
    -config RescueOIS_weak_epoch.cfg RescueOIS.tla
java -jar "$TLA_TOOLS_JAR" -workers auto \
    -config RescueOIS_weak_journal.cfg RescueOIS.tla
```

The strict runs exit 0 with all invariants verified. The weak runs exit
non-zero by design. We report weak counterexamples by trace length rather
than saying only "depth": `RescueOIS_weak.cfg` has a 3-state
`SingleAuthority` trace, `RescueOIS_weak_epoch.cfg` has a 3-state
`EpochAuthorityCoupling` trace, and `RescueOIS_weak_journal.cfg` has a
5-state `NoForkedJournal` trace showing two events at the same
`event_seq`.
