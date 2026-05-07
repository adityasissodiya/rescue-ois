# Rescue OIS Submission Sitrep

Date: 2026-05-07
Branch: `nca2026-submission`

## Current Commit Stack

- `3b2e9d1 paper: add Phase 2 evaluator metrics source`
- `895b5ce scripts: fixes from STEP 7 dry-run`
- `a69bdca prototype: minimum wiring for Phase 2 measurements`
- `551a6fb paper: genre shift to problem-driven systems contribution`
- `e0ea8a3 paper: migrate NCA submission draft to IEEE skeleton`
- `f7cf97b docs: record NCA 2026 submission decisions`
- `8d0e2d3 paper: integrity pass -- remove unverified eval numbers, expand bibliography, add ADRs 0004-0006`

## Phase 2 Measurement State

Phase 2 is complete. The evaluator ran end to end for run
`b9ce852f-fb15-420f-b2b7-a512eb0a8377` and produced 365 measured JSONL rows.
The measurement window in the file is `2026-05-06T07:15:39Z` through
`2026-05-06T08:25:23Z`, roughly 70 minutes wall time.

Scenario row counts:

- `bootstrap_latency`: 120 rows, run indices 0--29.
- `field_edit_propagation`: 90 rows, run indices 0--29.
- `wan_recovery`: 90 rows, run indices 0--29.
- `command_throughput`: 30 rows, run indices 0--29.
- `duplicate_replay`: 30 rows, run indices 0--29.
- `command_promotion`: 5 rows, run indices 0--4.

The canonical metrics file is now committed at
`paper/data/eval_metrics.jsonl` per ADR-0006. Future evaluator runs default to
that path through `scripts/evaluate-pilot.py`.

Inspection checks already run:

- No `harness_error` rows.
- No unexpected nulls outside scenarios that intentionally store the result in
  `scenario_params` or mark promotion as skipped.
- All throughput rows have `scenario_params.events_per_sec`.
- Idempotency held across all 30 duplicate-replay runs:
  `scenario_params.stored == scenario_params.unique_events`.
- WAN recovery distribution is monotonic by partition duration:
  1s partitions remain below 10s, and 10s remain below 60s.

## Open Observations From Phase 2

- `command_promotion` only has 5 skipped rows while the rest of the cells use
  30 runs in the committed data. The evaluator has been updated so future runs
  emit `RUNS_PER_CELL` skipped promotion rows for shape consistency.
- `partition_wan` audit rows were sparse and shared the canonical metrics
  stream. `inject-partition.sh` now writes audit rows to
  `partition_audit.jsonl` by default instead.
- The `command_throughput` low outlier is `run_index=0`:
  53.920090271790066 ev/s. The following runs immediately jump to the expected
  range around 168--173 ev/s. The evaluator now marks throughput run 0 with a
  warm-up note; Section VI should exclude it from throughput summaries.

## Paper State

The NCA paper is in IEEE skeleton form and now reads as a problem-driven
systems paper. The introduction states the research question, Section III
derives R1--R5 from operational requirements, Section IV maps protocol choices
to R1--R3, and Section VII argues explicitly why CRDT/local-first logic does
not satisfy R3.

Section VI should use only `paper/data/eval_metrics.jsonl` for measured claims.

## Phase 3 Safety Verification State

Phase 3 is implemented as a single-incident-journal model (option 3 from the
2026-05-07 modeling-correction discussion). The exclusion-style `NoTwoWriters`
in the original `safetyPlan.md` was inconsistent with retained per-vehicle
journals; option 3 replaces it with `SingleAuthority` and `NoForkedJournal`
over one shared incident journal whose write authority is held by at most one
vehicle at a time. Authority is separated from the `command` role so the
strict/weak distinction lands on authority transfer atomicity, where the bug
actually lives.

Artifacts (uncommitted at time of writing):

- `formal/tla/RescueOIS.tla` -- spec.
- `formal/tla/RescueOIS_strict.cfg` -- adopted protocol, all invariants.
- `formal/tla/RescueOIS_weak.cfg` -- broken protocol, all invariants.
- `formal/tla/RescueOIS_weak_journal.cfg` -- weak with role invariants
  suppressed so BFS surfaces the deeper journal-fork counterexample.
- `formal/python/protocol_simulator.py` -- mirror of the TLA+ model.
- `formal/python/tests/{test_no_two_writers,test_idempotency,test_seq_monotonicity,test_against_real}.py`.

TLC runs (Java 21 + tla2tools 2.19, `-workers auto`, 12 workers):

- Strict (`RescueOIS_strict.cfg`, symmetry on Vehicles): 2789 states
  generated, 386 distinct, search depth 10. All invariants verified, no
  errors.
- Weak (`RescueOIS_weak.cfg`, no symmetry): `SingleAuthority` violated at
  depth 3. Trace: Init -> Partition(v1,v2) -> WeakPromote(v2) -> authority
  becomes `{v1, v2}` because v2 cannot reach v1 to revoke its authority.
- Weak-journal (`RescueOIS_weak_journal.cfg`, role invariants suppressed):
  `NoForkedJournal` violated at depth 5. Trace: Init -> Partition(v1,v2) ->
  WeakPromote -> CommitEvent(v1, c1) -> CommitEvent(v2, c2). Both events
  land in the shared journal at `seq=1` because each authority's local
  cursor was refreshed against `Len(journal)+1` at promotion and neither
  has seen the other's commit. 922 distinct states explored before the
  shortest counterexample.

Hypothesis runs (uv-managed venv, pytest -q):

- `tests/test_no_two_writers.py::TestStrict` -- 2000 examples, 50 stateful
  steps each. `SingleAuthority`, `NoForkedJournal`, `LocalIdempotency`, and
  `SingleCommand` all preserved.
- `tests/test_no_two_writers.py::test_weak_variant_admits_counterexample` --
  hand-built counterexample matching the TLC weak-journal trace passes
  (i.e. the simulator reproduces the same forked-seq violation as TLC).
- `tests/test_idempotency.py` -- 200 examples, replayed cid never adds.
- `tests/test_seq_monotonicity.py` -- 500 examples, single-authority seqs
  are dense.
- `tests/test_against_real.py` -- skipped (real-stack opt-in).

Total: 4 passed, 2 skipped, 0 failed.

## Outstanding Phase 3 Decisions

- Whether to commit `formal/python/uv.lock` alongside `pyproject.toml`. Not
  part of the original `safetyPlan.md`; was generated by `uv run`.
- Section VI safety subsection has not been drafted; framing depends on the
  numbers above and waits on Aditya's review.
