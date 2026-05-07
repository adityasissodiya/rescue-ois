# Rescue OIS - TLA+ Safety Verification

This directory contains the TLA+ specification of the Rescue OIS
synchronisation protocol's safety properties, and three TLC
configurations that drive the verification.

The model is single-journal: one incident journal whose write authority
is held by at most one vehicle at a time. Each vehicle keeps a local
cursor for the next `event_seq` to allocate. Strict promotion atomically
revokes the prior authority and refreshes the new authority's cursor;
weak promotion does not, leaving two vehicles with cursors pointing at
the same journal position when the new command was promoted while
partitioned from the prior command.

## Files

- `RescueOIS.tla` - protocol specification.
- `RescueOIS_strict.cfg` - TLC config for the protocol as adopted (atomic
  revocation of the previous command's authority on promotion). All
  invariants must hold.
- `RescueOIS_weak.cfg` - same protocol with `StrictPromotion = FALSE`.
  Surfaces `SingleAuthority` violation at depth 3.
- `RescueOIS_weak_journal.cfg` - weak variant with the role-level
  `SingleAuthority` and `SingleCommand` invariants suppressed so that
  BFS continues past the depth-3 split-brain state and surfaces the
  deeper `NoForkedJournal` counterexample at depth 5 -- the canonical
  two-vehicles-commit-at-same-seq trace.

## Invariants

- `SingleAuthority` -- at most one vehicle holds write authority at any
  time. Strict: holds. Weak: violated at depth 3.
- `NoForkedJournal` -- distinct positions in the incident journal carry
  distinct `event_seq` values. Strict: holds (single cursor in use).
  Weak: violated at depth 5 (two cursors each commit at `seq=1` against
  the same journal).
- `LocalIdempotency` -- no `cid` appears twice in the journal.
- `SingleCommand` -- at most one vehicle in the `command` role.

## Running

Requires Java and the TLA+ tools. Set `TLA_TOOLS_JAR` to the path of
`tla2tools.jar`.

```bash
java -jar "$TLA_TOOLS_JAR" -workers auto \
    -config RescueOIS_strict.cfg RescueOIS.tla
java -jar "$TLA_TOOLS_JAR" -workers auto \
    -config RescueOIS_weak.cfg RescueOIS.tla
java -jar "$TLA_TOOLS_JAR" -workers auto \
    -config RescueOIS_weak_journal.cfg RescueOIS.tla
```

The strict run exits 0 with all invariants verified. The weak run exits
non-zero with a `SingleAuthority` counterexample at depth 3. The
weak-journal run exits non-zero with a `NoForkedJournal` counterexample
at depth 5 showing two events at the same `event_seq`.
