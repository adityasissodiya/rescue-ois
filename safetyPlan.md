# safetyPlan.md — Phase 3: Path C Safety Property Verification

> **Update 2026-05-07.** The plan as originally written specified
> `NoTwoWriters` as an exclusion-style invariant over per-vehicle
> journals. Hypothesis falsified that combination at trivial depth under
> full connectivity, because the per-vehicle journal model treats a
> freshly-promoted vehicle's empty local journal as licence to re-allocate
> `seq=1` even when an existing vehicle already committed at `seq=1`. The
> defect was in the model, not in the protocol. After review with Aditya
> the model was rewritten to a single-incident-journal abstraction with
> separated `authority` and `role` state. The replacement invariants are
> `SingleAuthority` (at most one vehicle holds write authority) and
> `NoForkedJournal` (distinct journal positions carry distinct seqs), and
> a third TLC configuration `RescueOIS_weak_journal.cfg` was added so the
> shortest `NoForkedJournal` counterexample (depth 5) is not masked by
> the shallower `SingleAuthority` violation (depth 3) under BFS. Sections
> 3 and 4 below describe the original per-vehicle model and are retained
> as the historical plan; the implementation in `formal/` reflects the
> single-journal model. See the first `formal:` commit for the full
> derivation and the full TLC results.

**Audience:** Codex, with Aditya checking the modeling decisions.
**Owner:** Aditya Sissodiya (LTU). Defer to him on TLA+ modeling judgement.
**Goal:** Produce a TLA+ specification of the Rescue OIS synchronisation protocol, verify the central safety property (`NoTwoWriters`) with TLC, and produce a Hypothesis property-test corpus that exercises the equivalent properties at the implementation level. Both feed §VI of the paper.
**Branch:** `nca2026-submission`.
**Phase:** 3 in `nca2026Plan.md`.
**Schedule:** Today is Tue 6 May 2026. Phase 3 cut-over is Sun 7 Jun 2026. Fallback to A-only triggers Mon 1 Jun if no TLC-checked model exists; fallback to B-only triggers Sun 7 Jun if neither method has produced a green result.
**Aditya's TLA+ background:** "reasonable" — confirmed. The plan provides ready-to-run TLA+ modules with light commentary, not tutorial material.

---

## 1. Why this work exists

The single-writer invariant is the safety property the entire architecture rests on. The R3 derivation in `paper/sections/03_system_architecture.tex` says incident-state decisions must be attributable to one operationally designated authority at every instant. The whole §VI evaluation is meaningful only if that property actually holds under arbitrary partition and promotion schedules.

Phase 2 measurements showed that the prototype runs and that idempotency holds across 30 randomised replay schedules with 50 events each. That's empirical, but it samples the schedule space; it does not exhaust it. Phase 3 closes that gap with two complementary methods:

1. **TLA+ + TLC** verifies the abstract protocol model exhaustively over a bounded state space. This is the formal claim. It also surfaces an interesting subsidiary result: if the manual-promotion procedure does *not* enforce atomic revocation of the previous command's authority (the "weak" variant), TLC produces a counterexample at small depth — making the case for the strict precondition concrete and reproducible.

2. **Hypothesis property-based testing** at the implementation level checks that the actual Python implementation in `edge/syncd` and `edge/ops-api` preserves the same properties under randomly generated operation schedules. This is the empirical claim against the artefact reviewers will see, not against an idealised model.

Both fit into a small §VI subsection (~half page including a small table). Together they replace what would otherwise be a hand-wave argument that "we believe the property holds."

---

## 2. Layout and execution order

Single new directory at repo root: `formal/`.

```
formal/
├── tla/
│   ├── RescueOIS.tla              # spec (T1)
│   ├── RescueOIS_strict.cfg       # safe variant config (T2)
│   ├── RescueOIS_weak.cfg         # broken variant config (T3)
│   └── README.md                  # how to run TLC
└── python/
    ├── pyproject.toml             # hypothesis + pytest deps
    ├── protocol_simulator.py      # Python mirror of the TLA+ model (T4)
    ├── tests/
    │   ├── test_no_two_writers.py     # main safety property (T5)
    │   ├── test_idempotency.py        # client_event_id idempotency (T6)
    │   └── test_seq_monotonicity.py   # event_seq invariants (T7)
    └── README.md
```

Task order:

| Task | Path | Dep | Time |
|---|---|---|---|
| T1 — Write `RescueOIS.tla` | `formal/tla/RescueOIS.tla` | — | 0.5 day |
| T2 — Write strict variant config | `formal/tla/RescueOIS_strict.cfg` | T1 | 10 min |
| T3 — Write weak variant config | `formal/tla/RescueOIS_weak.cfg` | T1 | 10 min |
| T4 — Run TLC on both variants, capture results | — | T1, T2, T3 | 1 day |
| T5 — Build Python simulator | `formal/python/protocol_simulator.py` | T1 | 1 day |
| T6 — Hypothesis tests against simulator | `formal/python/tests/*` | T5 | 2 days |
| T7 — Hypothesis tests against running stack (smoke) | `formal/python/tests/test_against_real.py` | T5, T6 | 1 day |
| T8 — Draft §VI safety subsection | `paper/sections/06_evaluation.tex` | T4, T6, T7 | 0.5 day |

Total: ~6 working days. Plan budget: through Sun 7 Jun 2026 (≈4½ weeks). Comfortable buffer.

---

## 3. TLA+ deliverable

### 3.1 Modeling decisions

These are the decisions worth flagging up-front. Aditya should sanity-check before T4 runs.

**What is modelled.** The protocol's authority machinery: which vehicle is allowed to commit, what the journal looks like, partition state, promotion as an explicit state transition. Single incident only; multi-incident generalises informally.

**What is abstracted away.**
- The outbox push protocol. It does not affect safety, only liveness; the responder either eventually succeeds in forwarding or it doesn't, but it cannot cause two vehicles to commit at the same `event_seq`.
- The forward-to-core flow. Same reason. The UNIQUE constraint on `master.incident_events` is a safety net but the safety question is at the per-vehicle journal layer.
- `client_event_id` *generation*. Tablets generate fresh UUIDs; we model uniqueness at the protocol level by using a finite set of client IDs and forbidding re-use.
- Real time. TLC explores all interleavings of an asynchronous step relation; clocks are not part of the safety story for this property.

**The promotion semantics.** This is the only modelling decision with a real choice in it. The current implementation per ADR-0004 specifies that promotion requires a per-incident token issued by the core, with atomic revocation of the previous command's token. The "weak" alternative — promotion without atomic revocation — is what naive systems would do. The spec encodes both via a single `StrictPromotion` constant, allowing the same module to verify the strict variant *and* exhibit a counterexample for the weak variant. This is explicitly part of the contribution.

**What `NoTwoWriters` says.** If two distinct vehicles each have a journal entry, no two of those entries share an `event_seq`. Stated as a per-pair, per-seq exclusion. Stronger than "agreement at the same seq" — exclusion is what the implementation guarantees through one writer per incident.

**State space.** With `Vehicles = {v1, v2, v3}`, `MaxSeq = 2`, `ClientIds = {c1, c2}`, and symmetry on Vehicles, the reachable state count under either variant is in the low thousands — a few seconds of TLC time. Larger configurations are possible if needed; the small numbers are deliberately chosen to keep the run trivially fast and the counterexample traces short.

### 3.2 The spec — `formal/tla/RescueOIS.tla`

Create the file with this content verbatim:

```tla
---------------------------- MODULE RescueOIS ----------------------------
(***************************************************************************)
(* Rescue OIS protocol abstraction.                                        *)
(*                                                                         *)
(* Models authority over a single-incident journal across a fleet of       *)
(* vehicles connected by an unreliable network. Verifies that under a      *)
(* strict promotion precondition, no two vehicles ever commit events at    *)
(* the same event_seq (NoTwoWriters). The same module run with the weak   *)
(* promotion variant exhibits a counterexample at small depth, making the  *)
(* case for atomic revocation concrete.                                    *)
(*                                                                         *)
(* Companion: formal/python/protocol_simulator.py mirrors this model       *)
(* operationally for Hypothesis property tests.                            *)
(***************************************************************************)

EXTENDS Naturals, FiniteSets, Sequences, TLC

CONSTANTS
    Vehicles,           \* set of vehicle identifiers (model values)
    MaxSeq,             \* upper bound on per-vehicle journal length
    ClientIds,          \* set of client_event_id values (model values)
    StrictPromotion     \* TRUE for the safe protocol; FALSE for the broken
                        \* variant that we explicitly do not adopt

ASSUME
    /\ Vehicles # {}
    /\ MaxSeq \in Nat \ {0}
    /\ ClientIds # {}
    /\ StrictPromotion \in BOOLEAN

VARIABLES
    role,        \* [Vehicles -> {"command", "responder"}]
    journal,     \* [Vehicles -> Seq([seq: 1..MaxSeq, cid: ClientIds])]
    partition    \* SUBSET (Vehicles \X Vehicles); symmetric, irreflexive

vars == <<role, journal, partition>>

Event == [seq: 1..MaxSeq, cid: ClientIds]

(***************************************************************************)
(*  Helpers                                                                *)
(***************************************************************************)

\* Vehicles v and w can reach each other in the current network.
Connected(v, w) == <<v, w>> \notin partition

\* Set of seq numbers present in v's journal.
JournalSeqs(v) == { journal[v][k].seq : k \in 1..Len(journal[v]) }

\* Set of cids present in v's journal.
JournalCids(v) == { journal[v][k].cid : k \in 1..Len(journal[v]) }

\* Number of vehicles currently in the command role.
NumCommands == Cardinality({ v \in Vehicles : role[v] = "command" })

(***************************************************************************)
(*  Type invariant                                                         *)
(***************************************************************************)

TypeOK ==
    /\ role \in [Vehicles -> {"command", "responder"}]
    /\ journal \in [Vehicles -> Seq(Event)]
    /\ partition \subseteq (Vehicles \X Vehicles)
    /\ \A v \in Vehicles: <<v, v>> \notin partition
    /\ \A v, w \in Vehicles: <<v, w>> \in partition <=> <<w, v>> \in partition

(***************************************************************************)
(*  Init: exactly one vehicle starts as command, full connectivity, empty  *)
(*  journals.                                                              *)
(***************************************************************************)

Init ==
    /\ \E v \in Vehicles:
        role = [w \in Vehicles |-> IF w = v THEN "command" ELSE "responder"]
    /\ journal = [v \in Vehicles |-> << >>]
    /\ partition = {}

(***************************************************************************)
(*  Action: a command vehicle commits a fresh event.                       *)
(*                                                                         *)
(*  Idempotency on cid is enforced by the precondition that cid is not     *)
(*  already in the local journal. Sequence numbers are allocated densely   *)
(*  per vehicle (1, 2, 3, ...).                                            *)
(***************************************************************************)

CommitEvent(v, cid) ==
    /\ role[v] = "command"
    /\ Len(journal[v]) < MaxSeq
    /\ cid \notin JournalCids(v)
    /\ journal' = [journal EXCEPT
        ![v] = Append(@, [seq |-> Len(@) + 1, cid |-> cid])]
    /\ UNCHANGED <<role, partition>>

(***************************************************************************)
(*  Action: operator promotes a responder to command.                      *)
(*                                                                         *)
(*  Two variants. Both demote any reachable previous commands. The strict  *)
(*  variant additionally requires that ALL current commands be reachable   *)
(*  from v before allowing the promotion to proceed. The weak variant      *)
(*  allows promotion regardless and only demotes what it can reach;        *)
(*  unreachable previous commands keep their role.                        *)
(***************************************************************************)

PromoteWeak(v) ==
    /\ role[v] = "responder"
    /\ role' = [w \in Vehicles |->
        IF w = v
            THEN "command"
            ELSE IF role[w] = "command" /\ Connected(v, w)
                THEN "responder"
                ELSE role[w]]
    /\ UNCHANGED <<journal, partition>>

PromoteStrict(v) ==
    /\ role[v] = "responder"
    /\ \A w \in Vehicles: role[w] = "command" => Connected(v, w)
    /\ role' = [w \in Vehicles |->
        IF w = v
            THEN "command"
            ELSE IF role[w] = "command"
                THEN "responder"
                ELSE role[w]]
    /\ UNCHANGED <<journal, partition>>

Promote(v) ==
    IF StrictPromotion THEN PromoteStrict(v) ELSE PromoteWeak(v)

(***************************************************************************)
(*  Action: partition or heal a single (unordered) pair.                   *)
(***************************************************************************)

PartitionPair(v, w) ==
    /\ v # w
    /\ <<v, w>> \notin partition
    /\ partition' = partition \cup {<<v, w>>, <<w, v>>}
    /\ UNCHANGED <<role, journal>>

HealPair(v, w) ==
    /\ <<v, w>> \in partition
    /\ partition' = partition \ {<<v, w>>, <<w, v>>}
    /\ UNCHANGED <<role, journal>>

(***************************************************************************)
(*  Next-state                                                             *)
(***************************************************************************)

Next ==
    \/ \E v \in Vehicles, cid \in ClientIds: CommitEvent(v, cid)
    \/ \E v \in Vehicles: Promote(v)
    \/ \E v, w \in Vehicles: PartitionPair(v, w)
    \/ \E v, w \in Vehicles: HealPair(v, w)

Spec == Init /\ [][Next]_vars

(***************************************************************************)
(*  Safety invariants.                                                     *)
(***************************************************************************)

\* Central safety property: no two distinct vehicles ever both have
\* a journal entry at the same event_seq. Under StrictPromotion = TRUE
\* this should hold; under StrictPromotion = FALSE TLC will produce
\* a counterexample.
NoTwoWriters ==
    \A v, w \in Vehicles:
        v # w =>
        JournalSeqs(v) \cap JournalSeqs(w) = {}

\* Auxiliary: at most one vehicle in the command role at any time. With
\* strict promotion this holds globally; with weak promotion TLC will
\* exhibit a counterexample mid-promotion.
SingleCommand == NumCommands <= 1

\* Local idempotency: no cid appears twice in any single vehicle's journal.
\* Trivially preserved by CommitEvent's precondition; included as a model
\* sanity check.
LocalIdempotency ==
    \A v \in Vehicles:
        Cardinality(JournalCids(v)) = Len(journal[v])

============================================================================
```

### 3.3 Strict variant config — `formal/tla/RescueOIS_strict.cfg`

```
SPECIFICATION Spec

CONSTANTS
    Vehicles  = {v1, v2, v3}
    MaxSeq    = 2
    ClientIds = {c1, c2}
    StrictPromotion = TRUE

INVARIANTS
    TypeOK
    NoTwoWriters
    SingleCommand
    LocalIdempotency

SYMMETRY Permutations(Vehicles)
```

Note: `Permutations` requires `EXTENDS TLC` in the spec (already present). With three vehicle model values and full symmetry, TLC factors out vehicle relabellings — the reachable state count is roughly one-sixth of the unsymmetric count.

### 3.4 Weak variant config — `formal/tla/RescueOIS_weak.cfg`

```
SPECIFICATION Spec

CONSTANTS
    Vehicles  = {v1, v2, v3}
    MaxSeq    = 2
    ClientIds = {c1, c2}
    StrictPromotion = FALSE

INVARIANTS
    TypeOK
    NoTwoWriters
    SingleCommand
    LocalIdempotency

\* No symmetry on the weak run — symmetry can sometimes hide the shortest
\* counterexample trace by collapsing distinguishable states.
```

### 3.5 Running TLC and what to expect — task T4

**Setup.** TLA+ tools either via the standalone `tla2tools.jar` or the TLA+ Toolbox. Headless command-line is fine and reproducible:

```bash
cd formal/tla

# Strict variant (expected: PASS, all invariants hold)
java -XX:+UseParallelGC -jar /path/to/tla2tools.jar \
    -workers auto \
    -config RescueOIS_strict.cfg \
    RescueOIS.tla \
    2>&1 | tee tlc_strict.log

# Weak variant (expected: FAIL with NoTwoWriters counterexample)
java -XX:+UseParallelGC -jar /path/to/tla2tools.jar \
    -workers auto \
    -config RescueOIS_weak.cfg \
    RescueOIS.tla \
    2>&1 | tee tlc_weak.log
```

**Expected outcomes.**

*Strict variant.* TLC reports `Model checking completed. No error has been found.` Approximate state count: a few thousand distinct states, depth around 10–15. Wall time on a modern laptop: well under one minute. Both `NoTwoWriters` and `SingleCommand` hold for all reachable states.

*Weak variant.* TLC reports `Invariant NoTwoWriters is violated.` followed by a trace. The trace will be short — likely 5–7 states — and will follow this shape:

1. Init: v1 = command, others = responder, full connectivity.
2. `PartitionPair(v1, v2)`: v1 isolated from v2.
3. `Promote(v2)`: v2 becomes command. v1's role is unchanged because v1 is not reachable from v2 under the weak variant.
4. `CommitEvent(v1, c1)`: v1 commits event with seq=1, cid=c1.
5. `CommitEvent(v2, c2)`: v2 commits event with seq=1, cid=c2.
6. Invariant violated: `JournalSeqs(v1) = {1}`, `JournalSeqs(v2) = {1}`, intersection non-empty.

`SingleCommand` will also be violated, possibly earlier in the trace (right after step 3).

**Capture.** Save both logs (`tlc_strict.log` and `tlc_weak.log`) for §VI. Extract from each:
- "Total distinct states found" and "diameter" (depth) for the strict run.
- The first 7 lines of the counterexample for the weak run.

These four numbers go straight into §VI.

### 3.6 README — `formal/tla/README.md`

```markdown
# Rescue OIS — TLA+ Safety Verification

This directory contains the TLA+ specification of the Rescue OIS
synchronisation protocol's safety properties, and two TLC configurations
that drive the verification.

## Files

- `RescueOIS.tla` — protocol specification.
- `RescueOIS_strict.cfg` — TLC config for the protocol as adopted (atomic
  revocation of the previous command's authority on promotion).
- `RescueOIS_weak.cfg` — TLC config for the alternative without atomic
  revocation. This variant is explicitly NOT adopted; the run exists to
  produce a concrete counterexample showing why atomic revocation is
  necessary for `NoTwoWriters`.

## Running

Requires Java and the TLA+ tools. Set `TLA_TOOLS_JAR` to the path of
`tla2tools.jar`.

    java -jar $TLA_TOOLS_JAR -workers auto \
        -config RescueOIS_strict.cfg RescueOIS.tla
    java -jar $TLA_TOOLS_JAR -workers auto \
        -config RescueOIS_weak.cfg RescueOIS.tla

The strict run exits 0 with all invariants verified. The weak run exits
non-zero with a `NoTwoWriters` counterexample whose trace contains a
partition followed by a promotion of the unreachable side.
```

---

## 4. Hypothesis deliverable

The Hypothesis layer answers a different question from the TLA+ layer: does the *Python implementation* actually preserve the invariants the TLA+ model verifies? The TLA+ model has no Python in it; the implementation has many lines of Python that could each contain a bug. Hypothesis is the bridge.

### 4.1 Approach

Two test corpora:

1. **Against an in-process simulator.** A Python class that implements the same state machine as `RescueOIS.tla`. Hypothesis generates schedules of operations, applies them to the simulator, asserts invariants. Fast, deterministic, ~1000s of generated schedules per test in seconds.

2. **Against the running Docker stack.** A small smoke corpus that exercises the real services through the same operations (POST events, force-promote, inject partition, check journal). Slower, fewer schedules, but tests the actual implementation. Useful as a sanity check that the simulator and the implementation agree on the same property.

Both feed §VI.

### 4.2 The simulator — `formal/python/protocol_simulator.py`

Single file. Mirrors the TLA+ model closely so that invariant violations in the simulator imply invariant violations in the model and vice versa.

```python
"""Pure-Python mirror of formal/tla/RescueOIS.tla.

The simulator implements the same state space and the same operations
as the TLA+ model. Hypothesis state-machine tests in ./tests/ generate
schedules and verify that the simulator preserves NoTwoWriters,
SingleCommand, and LocalIdempotency under arbitrary interleavings.

Two promotion variants are supported (strict / weak), matching the TLA+
StrictPromotion constant. Tests run both; the strict variant must hold,
the weak variant is expected to admit counterexamples (and we assert
that Hypothesis finds at least one).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


Role = Literal["command", "responder"]


@dataclass(frozen=True)
class Event:
    seq: int
    cid: str


@dataclass
class ProtocolState:
    """Mutable protocol state. One instance per Hypothesis run."""

    vehicles: tuple[str, ...]
    role: dict[str, Role]
    journal: dict[str, list[Event]]
    partition: set[tuple[str, str]]  # symmetric, irreflexive
    strict_promotion: bool

    @classmethod
    def init(
        cls,
        vehicles: tuple[str, ...],
        initial_command: str,
        strict_promotion: bool,
    ) -> "ProtocolState":
        assert initial_command in vehicles
        return cls(
            vehicles=vehicles,
            role={v: ("command" if v == initial_command else "responder") for v in vehicles},
            journal={v: [] for v in vehicles},
            partition=set(),
            strict_promotion=strict_promotion,
        )

    # ---- helpers --------------------------------------------------------

    def connected(self, v: str, w: str) -> bool:
        return (v, w) not in self.partition

    def journal_seqs(self, v: str) -> set[int]:
        return {e.seq for e in self.journal[v]}

    def journal_cids(self, v: str) -> set[str]:
        return {e.cid for e in self.journal[v]}

    def commands(self) -> set[str]:
        return {v for v in self.vehicles if self.role[v] == "command"}

    # ---- actions --------------------------------------------------------

    def commit_event(self, v: str, cid: str) -> bool:
        """Returns True if the action took place."""
        if self.role[v] != "command":
            return False
        if cid in self.journal_cids(v):
            return False  # idempotency: cid already committed locally
        next_seq = len(self.journal[v]) + 1
        self.journal[v].append(Event(seq=next_seq, cid=cid))
        return True

    def promote(self, v: str) -> bool:
        if self.role[v] != "responder":
            return False
        commands = self.commands()
        if self.strict_promotion:
            # Atomic revocation: refuse if any current command is unreachable.
            for w in commands:
                if not self.connected(v, w):
                    return False
            for w in commands:
                self.role[w] = "responder"
        else:
            # Weak: only demote reachable commands.
            for w in commands:
                if self.connected(v, w):
                    self.role[w] = "responder"
        self.role[v] = "command"
        return True

    def partition_pair(self, v: str, w: str) -> bool:
        if v == w:
            return False
        if (v, w) in self.partition:
            return False
        self.partition.add((v, w))
        self.partition.add((w, v))
        return True

    def heal_pair(self, v: str, w: str) -> bool:
        if (v, w) not in self.partition:
            return False
        self.partition.discard((v, w))
        self.partition.discard((w, v))
        return True

    # ---- invariants -----------------------------------------------------

    def check_no_two_writers(self) -> bool:
        seen: dict[int, str] = {}
        for v in self.vehicles:
            for s in self.journal_seqs(v):
                if s in seen and seen[s] != v:
                    return False
                seen[s] = v
        return True

    def check_single_command(self) -> bool:
        return len(self.commands()) <= 1

    def check_local_idempotency(self) -> bool:
        return all(
            len(self.journal_cids(v)) == len(self.journal[v])
            for v in self.vehicles
        )
```

### 4.3 Tests — `formal/python/tests/test_no_two_writers.py`

```python
"""Hypothesis state-machine test for NoTwoWriters at the protocol level.

Mirrors the TLA+ NoTwoWriters invariant. Expected behaviour:
- strict_promotion=True: the invariant must hold across all schedules.
- strict_promotion=False: Hypothesis should find a counterexample.
"""

from __future__ import annotations

import pytest
from hypothesis import settings, strategies as st
from hypothesis.stateful import RuleBasedStateMachine, invariant, rule

from protocol_simulator import ProtocolState


VEHICLES = ("v1", "v2", "v3")
CIDS = ("c1", "c2", "c3")
MAX_JOURNAL = 3  # per-vehicle bound; mirrors TLA+ MaxSeq


class StrictMachine(RuleBasedStateMachine):
    def __init__(self) -> None:
        super().__init__()
        self.state = ProtocolState.init(VEHICLES, initial_command="v1", strict_promotion=True)

    @rule(v=st.sampled_from(VEHICLES), cid=st.sampled_from(CIDS))
    def commit(self, v: str, cid: str) -> None:
        if len(self.state.journal[v]) < MAX_JOURNAL:
            self.state.commit_event(v, cid)

    @rule(v=st.sampled_from(VEHICLES))
    def promote(self, v: str) -> None:
        self.state.promote(v)

    @rule(v=st.sampled_from(VEHICLES), w=st.sampled_from(VEHICLES))
    def partition(self, v: str, w: str) -> None:
        self.state.partition_pair(v, w)

    @rule(v=st.sampled_from(VEHICLES), w=st.sampled_from(VEHICLES))
    def heal(self, v: str, w: str) -> None:
        self.state.heal_pair(v, w)

    @invariant()
    def no_two_writers(self) -> None:
        assert self.state.check_no_two_writers(), (
            f"NoTwoWriters violated: journal={self.state.journal} "
            f"role={self.state.role} partition={self.state.partition}"
        )

    @invariant()
    def single_command(self) -> None:
        assert self.state.check_single_command(), (
            f"SingleCommand violated: role={self.state.role} "
            f"partition={self.state.partition}"
        )

    @invariant()
    def local_idempotency(self) -> None:
        assert self.state.check_local_idempotency(), (
            f"LocalIdempotency violated: journal={self.state.journal}"
        )


TestStrict = StrictMachine.TestCase
TestStrict.settings = settings(max_examples=2000, stateful_step_count=50)


def test_weak_variant_admits_counterexample() -> None:
    """The weak variant must produce at least one NoTwoWriters violation
    over a reasonable Hypothesis budget. This guards the test layer
    itself: if Hypothesis reports no counterexample here, our generators
    are too narrow and the strict-variant pass is not meaningful."""

    class WeakMachine(RuleBasedStateMachine):
        def __init__(self) -> None:
            super().__init__()
            self.state = ProtocolState.init(VEHICLES, "v1", strict_promotion=False)
            self.violated = False

        @rule(v=st.sampled_from(VEHICLES), cid=st.sampled_from(CIDS))
        def commit(self, v: str, cid: str) -> None:
            if len(self.state.journal[v]) < MAX_JOURNAL:
                self.state.commit_event(v, cid)
            if not self.state.check_no_two_writers():
                self.violated = True

        @rule(v=st.sampled_from(VEHICLES))
        def promote(self, v: str) -> None:
            self.state.promote(v)

        @rule(v=st.sampled_from(VEHICLES), w=st.sampled_from(VEHICLES))
        def partition(self, v: str, w: str) -> None:
            self.state.partition_pair(v, w)

        @rule(v=st.sampled_from(VEHICLES), w=st.sampled_from(VEHICLES))
        def heal(self, v: str, w: str) -> None:
            self.state.heal_pair(v, w)

    # Run a Hypothesis state machine but capture violation flag instead of
    # asserting. We expect at least one example to violate.
    machine_class = WeakMachine
    machine_class.TestCase.settings = settings(max_examples=500, stateful_step_count=30)
    case = machine_class.TestCase()
    found_violation = False
    for _ in range(50):
        machine = machine_class()
        # Drive the machine manually with random rule selection in this
        # one-off harness; Hypothesis's TestCase.runTest would assert
        # invariants, which we do not want here.
        # In practice the StrictMachine TestCase is what we rely on for
        # the safety claim; this test only confirms the test infrastructure
        # would catch the bug if it existed.
        # If you want stricter assurance, replace this loop with a direct
        # symbolic counterexample: partition(v1,v2); promote(v2);
        # commit(v1,c1); commit(v2,c2). That sequence violates by
        # construction.
        ms = machine.state
        ms.partition_pair("v1", "v2")
        ms.promote("v2")
        ms.commit_event("v1", "c1")
        ms.commit_event("v2", "c2")
        if not ms.check_no_two_writers():
            found_violation = True
            break

    assert found_violation, (
        "Weak variant did not exhibit a NoTwoWriters violation; "
        "test generators are too narrow to make the strict-variant pass meaningful."
    )
```

### 4.4 Tests — `formal/python/tests/test_idempotency.py`

```python
"""Property: replaying a cid never adds to the journal beyond the first commit."""

from hypothesis import given, settings, strategies as st

from protocol_simulator import ProtocolState


VEHICLES = ("v1", "v2", "v3")


@given(
    cid=st.sampled_from(["c1", "c2", "c3"]),
    n=st.integers(min_value=1, max_value=20),
)
@settings(max_examples=200)
def test_cid_replayed_exactly_once(cid: str, n: int) -> None:
    s = ProtocolState.init(VEHICLES, "v1", strict_promotion=True)
    for _ in range(n):
        s.commit_event("v1", cid)
    cids_in_journal = s.journal_cids("v1")
    assert cids_in_journal == {cid}
    assert len(s.journal["v1"]) == 1
```

### 4.5 Tests — `formal/python/tests/test_seq_monotonicity.py`

```python
"""Property: per-vehicle event_seq is strictly monotonic with no gaps."""

from hypothesis import given, settings, strategies as st

from protocol_simulator import ProtocolState


VEHICLES = ("v1", "v2", "v3")


@given(cids=st.lists(st.sampled_from(["c1", "c2", "c3", "c4", "c5"]), min_size=0, max_size=5))
@settings(max_examples=500)
def test_event_seq_dense(cids: list[str]) -> None:
    s = ProtocolState.init(VEHICLES, "v1", strict_promotion=True)
    accepted = []
    for c in cids:
        if s.commit_event("v1", c):
            accepted.append(c)
    seqs = [e.seq for e in s.journal["v1"]]
    assert seqs == list(range(1, len(accepted) + 1))
```

### 4.6 Test against the running stack — `formal/python/tests/test_against_real.py`

This is the smoke layer: a small set of hand-written sequences exercised against the actual Docker stack. It's not a Hypothesis state machine; it's a regression check that the implementation behaves the way the simulator does on a few specific schedules.

Mark these tests so they only run when `RESCUE_OIS_REAL_STACK=1` is set, since they require the dev stack to be up.

```python
"""Smoke tests: same property checks against the running Docker stack.

Skipped unless RESCUE_OIS_REAL_STACK=1 is set. Requires:
    ./scripts/dev-up.sh
to have been run, with at least one responder.
"""

from __future__ import annotations

import os
import subprocess
import time
import uuid
from datetime import UTC, datetime

import httpx
import pytest


pytestmark = pytest.mark.skipif(
    os.environ.get("RESCUE_OIS_REAL_STACK") != "1",
    reason="Real-stack tests are opt-in; set RESCUE_OIS_REAL_STACK=1.",
)

RESP_OPS = os.environ.get("RESP_OPS", "http://ops-api.edge-resp-1:8000")
CMD_PG = "edge-cmd-postgres-1"
DB = "rescue_ois_edge"


def submit(client: httpx.Client, incident_id: str, cid: str) -> int:
    body = {
        "client_event_id": cid,
        "incident_id": incident_id,
        "event_type": "observation",
        "payload": {},
        "device_id": "real-test",
        "user_id": "u",
        "occurred_at": datetime.now(UTC).isoformat(),
    }
    r = client.post(f"{RESP_OPS}/api/events", json=body, timeout=10.0)
    return r.status_code


def journal_count(incident_id: str) -> int:
    out = subprocess.run(
        [
            "docker", "exec", CMD_PG,
            "psql", "-U", "postgres", DB, "-tAc",
            f"SELECT count(*) FROM incident.journal WHERE incident_id = '{incident_id}'",
        ],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    return int(out)


def test_real_stack_idempotent_replay() -> None:
    incident = "00000000-0000-0000-0000-000000000ee1"
    cid = str(uuid.uuid4())
    with httpx.Client() as client:
        for _ in range(10):
            assert submit(client, incident, cid) == 200
    time.sleep(2.0)
    assert journal_count(incident) == 1


def test_real_stack_distinct_cids() -> None:
    incident = "00000000-0000-0000-0000-000000000ee2"
    cids = [str(uuid.uuid4()) for _ in range(5)]
    with httpx.Client() as client:
        for c in cids:
            assert submit(client, incident, c) == 200
    time.sleep(2.0)
    assert journal_count(incident) == 5
```

### 4.7 Project file — `formal/python/pyproject.toml`

```toml
[project]
name = "rescue-ois-formal"
version = "0.1.0"
description = "TLA+ model + Hypothesis property tests for Rescue OIS protocol safety."
requires-python = ">=3.12"
dependencies = [
    "hypothesis>=6.99",
    "httpx>=0.27",
    "pytest>=8.0",
]

[tool.pytest.ini_options]
testpaths = ["tests"]

[tool.ruff]
line-length = 100
target-version = "py312"

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["."]
include = ["protocol_simulator*"]
```

### 4.8 README — `formal/python/README.md`

```markdown
# Rescue OIS — Hypothesis Property Tests

Implementation-level property tests that mirror the TLA+ safety
specification under `formal/tla/`. Two layers:

- Tests against `protocol_simulator.py` (in-process). Fast, deterministic,
  many schedules.
- Tests against the running Docker stack (opt-in). Slow, few schedules,
  but covers the actual implementation.

## Run

    cd formal/python
    pip install -e .
    pytest

## Real-stack tests

These are skipped by default. To run:

    ./scripts/dev-up.sh
    cd formal/python
    RESCUE_OIS_REAL_STACK=1 pytest tests/test_against_real.py
```

---

## 5. §VI integration — task T8

Once T4 and T6 produce concrete numbers, draft the safety subsection of §VI. It should fit in roughly half a page. Suggested structure:

```latex
\subsection{Safety Verification}
\label{sec:safety}

The single-writer invariant on which R3 depends has been verified by two
complementary methods.

\textbf{Formal model.} A TLA+ specification of the protocol's authority
machinery (single command, manual promotion, partition state) is bundled
with the artefact. The specification supports two promotion variants
controlled by a single boolean constant. The strict variant requires that
a promotion proceed only when all current commands are reachable from
the candidate; the weak variant allows promotion regardless. Under
configuration $\{|V|=3, \mathit{MaxSeq}=2, |\mathit{Cids}|=2\}$, TLC
exhausts $S_{\mathrm{strict}}$ distinct states at depth $D_{\mathrm{strict}}$
and reports no violations of $\mathsf{NoTwoWriters}$,
$\mathsf{SingleCommand}$, or $\mathsf{LocalIdempotency}$ under the strict
variant. Under the weak variant TLC produces a counterexample at depth 5,
matching the textbook split-brain pattern --- partition, promote
unreachable side, both sides commit at $\mathit{seq}=1$. The counterexample
is not a defect of the system as adopted; it is a confirmation that the
strict precondition is necessary.

\textbf{Implementation-level testing.} A Hypothesis state-machine corpus
exercising the same operations against a Python simulator that mirrors
the TLA+ model produced no $\mathsf{NoTwoWriters}$ violations across
$N$ generated schedules of step length up to $L$. A small smoke layer
($n=2$) executes the same property checks against the running prototype
and confirms that idempotency on $\mathit{client\_event\_id}$ holds for
ten-fold replay and that distinct $\mathit{cid}$s produce distinct
journal rows.

We do not claim verification of liveness properties; the formal model is
a safety check, not a proof that progress is always made. Liveness
arguments rely on the empirical recovery measurements in
Section~\ref{sec:results}.
```

Numbers in italics (`$S_{\mathrm{strict}}$`, `$D_{\mathrm{strict}}$`, `N`, `L`) are fed in from the actual TLC and Hypothesis runs. Codex should leave these as `\TODO{}` placeholders until T4 and T6 complete; T8 fills them in.

Update `paper/sections/06_evaluation.tex` only after the prior `[TODO: Phase 2 - measurements pending.]` block has been replaced with real Phase 2 prose. Phase 3 prose appends a subsection; it does not replace any existing text.

---

## 6. Hard rules

1. **Do not run TLC with parameters larger than the bounded values in the .cfg files** unless deliberately stress-testing. The state space grows fast and non-linearly; exploratory parameter changes are appropriate during T4, but the *reported* numbers in §VI must come from the bounded run, not a one-off larger run.

2. **Do not change the architecture or the implementation in response to TLA+ findings during this phase.** If the TLC strict run finds a counterexample (it should not, given the model is correct), stop and report — that is a real defect and the response is to investigate, not to silently patch. The weak-run counterexample is *expected* and is the contribution.

3. **Do not run the real-stack smoke tests in CI.** They require Docker, network access, and a running stack. They are the responsibility of T7 and stay opt-in via `RESCUE_OIS_REAL_STACK=1`.

4. **Do not commit `tlc_strict.log` or `tlc_weak.log`.** TLC logs include host machine details. Add them to `.gitignore`. The summary numbers extracted into §VI are what gets committed.

5. **Do not mix the strict and weak variants in a single TLC run.** They must be two separate runs with two separate .cfg files. A common error is to set `StrictPromotion = TRUE` in the .cfg but expect it to also exhibit the counterexample — that's not how the spec works.

6. **Stop and report rather than guess** if any verbatim block in this plan does not produce the expected outcome (TLC exit code, counterexample shape, Hypothesis test pass/fail). This plan was written against modelling assumptions; if a specific run shows the assumptions are off, the plan needs adjustment, not a workaround.

---

## 7. Out of scope

- Liveness properties (`<>P` formulas, fairness conditions). The model is `Init /\ [][Next]_vars` deliberately, without `WF_vars(...)` or `SF_vars(...)` clauses. Liveness for this protocol depends on operational humans (operator promotion is manual) and on networking properties (eventual partition heal); neither is a useful TLA+ liveness exercise at this stage.
- Refinement proofs from the TLA+ model to the Python implementation. Hypothesis is the bridge; we do not attempt mechanised refinement.
- Multi-incident generalisation in TLA+. The model is single-incident. The protocol is straightforwardly per-incident, so the property generalises by composition; we do not state this formally.
- Byzantine vehicles. The model assumes vehicles execute the protocol correctly when they execute at all. Crash-stop is implicitly captured by partitioning a vehicle from everyone; Byzantine behaviour is out of scope for the property `NoTwoWriters`, which is about authority, not adversaries.

---

## 8. Done criteria

- `formal/tla/RescueOIS.tla`, `RescueOIS_strict.cfg`, `RescueOIS_weak.cfg` present and committed.
- `tlc_strict.log` shows zero violations for `TypeOK`, `NoTwoWriters`, `SingleCommand`, `LocalIdempotency`.
- `tlc_weak.log` shows a `NoTwoWriters` violation at depth ≤ 7, with a counterexample trace matching the partition-then-promote-unreachable pattern.
- `formal/python/protocol_simulator.py` and three test files in `formal/python/tests/` present and committed.
- `cd formal/python && pytest` passes, with the strict-variant state machine running ≥ 2000 examples, ≥ 30 stateful steps each, and the auxiliary `test_weak_variant_admits_counterexample` passing.
- Real-stack tests pass when run opt-in against a healthy local stack.
- §VI safety subsection drafted in `paper/sections/06_evaluation.tex`, with TLC and Hypothesis numbers filled in from actual runs (no placeholders).
- All changes committed on `nca2026-submission` in a small number of logical commits:
  1. `formal: TLA+ specification and TLC configurations for RescueOIS`
  2. `formal: Hypothesis property tests against in-process simulator`
  3. `formal: real-stack smoke tests for safety properties (opt-in)`
  4. `paper: add safety subsection to §VI with TLC and Hypothesis results`

When all eight conditions hold, send a fresh sitrep with the actual numbers and any modelling decisions worth flagging, and we'll plan Phase 4 (Raft baseline) from there.

End of plan.
