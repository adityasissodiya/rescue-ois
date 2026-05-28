# TLC Runs for RescueOIS.tla

All runs used `tla2tools.jar` downloaded from the official TLA+ release for this revision.

- TLC version: 2.19 of 08 August 2024 (rev: 5a47802)
- Command shape: `timeout 1800 /usr/bin/time -p java -jar /tmp/tla2tools.jar -workers auto -config <cfg> RescueOIS.tla`
- Host worker count selected by TLC: 12 workers
- Per-config cap: 30 minutes
- Network abstraction: the model uses a global symmetric `partition` relation and `PartitionPair`/`HealPair` transitions. It does not model in-flight messages; the checked properties are safety invariants over authority, epoch, and journal state, not liveness properties over message delivery.

## Strict Configurations

| Config | Constants | Symmetry | Result | Generated | Distinct | Queue Left | Graph-Search Depth | Wall Clock | Invariants |
|---|---|---:|---|---:|---:|---:|---:|---:|---|
| `RescueOIS_small.cfg` | `Vehicles={v1,v2,v3}`, `MaxJournal=2`, `ClientIds={c1,c2}`, `MaxPromotions=1`, `StrictPromotion=TRUE` | yes | pass | 745 | 108 | 0 | 7 | 0.80 s | `TypeOK`, `SingleAuthority`, `EpochAuthorityCoupling`, `DurabilityAcrossPromotion`, `NoForkedJournal`, `LocalIdempotency`, `SingleCommand` |
| `RescueOIS_medium.cfg` | `Vehicles={v1,v2,v3}`, `MaxJournal=6`, `ClientIds={c1,c2,c3,c4,c5,c6}`, `MaxPromotions=2`, `StrictPromotion=TRUE` | yes | pass | 4,681,527 | 681,092 | 0 | 12 | 13.82 s | same |
| `RescueOIS_large.cfg` | `Vehicles={v1,v2,v3}`, `MaxJournal=7`, `ClientIds={c1,c2,c3,c4,c5,c6,c7}`, `MaxPromotions=3`, `StrictPromotion=TRUE` | yes | pass | 263,736,831 | 38,561,328 | 0 | 14 | 781.22 s | same |

The proposed `MaxJournal=5`, `ClientIds={c1,c2,c3}`, `MaxPromotions=2` medium shape reached only 1,760 distinct states because idempotency limits effective journal length to `min(MaxJournal, Cardinality(ClientIds))`. The final medium config therefore keeps `Vehicles=3` and increases `ClientIds` to match the journal bound, preserving the approved scaling order without adding message state or a fourth vehicle.

## Weak Configurations

TLC stops at the first violated invariant. For weak runs, "trace length" below means the number of states in the counterexample behavior printed by TLC, including the initial state. TLC's reported graph-search depth is listed separately.

| Config | Purpose | Violated Invariant | Trace Length | TLC Graph-Search Depth at Stop | Generated | Distinct | Queue Left | Wall Clock |
|---|---|---|---:|---:|---:|---:|---:|---:|
| `RescueOIS_weak.cfg` | unfenced promotion with all invariants enabled | `SingleAuthority` | 3 | 5 | 323 | 185 | 137 | 0.85 s |
| `RescueOIS_weak_epoch.cfg` | suppress role-level authority invariant to expose epoch coupling | `EpochAuthorityCoupling` | 3 | 6 | 294 | 144 | 101 | 0.77 s |
| `RescueOIS_weak_journal.cfg` | suppress authority and epoch-coupling invariants to expose journal fork | `NoForkedJournal` | 5 | 7 | 3,509 | 1,015 | 595 | 0.83 s |

## Log Files

- `runs/small.log`
- `runs/medium.log`
- `runs/large.log`
- `runs/weak.log`
- `runs/weak_epoch.log`
- `runs/weak_journal.log`
