# Weak-Promotion Counterexamples

The weak model sets `StrictPromotion = FALSE`. In that variant, a responder can be promoted while partitioned from the old command; the old command is not revoked, and the weak promotion does not allocate a fence epoch. These traces are the negative control showing what the strict promotion rule prevents.

## SingleAuthority Trace

Config: `RescueOIS_weak.cfg`

- Violated invariant: `SingleAuthority`
- Trace length: 3 states (initial state plus 2 transitions)
- TLC graph-search depth at stop: 5

Trace summary suitable for the paper:

1. Initial state: one vehicle is command and holds the only authority.
2. The network partitions a responder from the command vehicle.
3. The partitioned responder is weak-promoted. Because the old command is unreachable, weak promotion does not revoke it. The model now has two vehicles in `authority`, violating `SingleAuthority`.

## EpochAuthorityCoupling Trace

Config: `RescueOIS_weak_epoch.cfg`

- Violated invariant: `EpochAuthorityCoupling`
- Trace length: 3 states (initial state plus 2 transitions)
- TLC graph-search depth at stop: 6

Trace summary suitable for the paper:

1. Initial state: one command vehicle holds authority at epoch 0.
2. A responder is partitioned from that command vehicle.
3. The responder is weak-promoted without allocating a new fence epoch. Both the old command and the new command hold authority at epoch 0, violating the invariant that at most one vehicle may hold authority for any epoch.

## NoForkedJournal Trace

Config: `RescueOIS_weak_journal.cfg`

- Violated invariant: `NoForkedJournal`
- Trace length: 5 states (initial state plus 4 transitions)
- TLC graph-search depth at stop: 7

Trace summary suitable for the paper:

1. Initial state: one vehicle is command and holds authority at epoch 0.
2. A responder is partitioned from the command vehicle.
3. The responder is weak-promoted, leaving both vehicles with authority at epoch 0 and local cursors at sequence 1.
4. The old command commits client id `c1` at `seq=1`, epoch 0.
5. The new command commits client id `c2` at `seq=1`, epoch 0. The journal now contains two distinct entries with the same `event_seq`, violating `NoForkedJournal`.
