# Rescue OIS Submission Sitrep

Date: 2026-05-06
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

## Next Submission Work

Immediate work before Phase 3:

1. Stop before Phase 3 until `safetyPlan.md` exists.
2. Once `safetyPlan.md` exists, implement Path C: TLA+ primary, Hypothesis
   secondary.
3. After the safety-property result is green, update Section VI around
   measurements and safety verification without overclaiming production
   readiness.

Phase 3 is Path C per `docs/decisions.md`: TLA+ primary, Hypothesis secondary.
The TLA+ deliverable should model vehicles, roles, the journal, promotion
tokens, partitions, and the operations `CommitEvent`, `PromoteResponder`,
`AcknowledgePromotion`, and `HealPartition`. The primary invariants are
`NoTwoWriters` and `SingleCommandPerIncident`.

## TLA+ Background

No repository file records whether any of the four authors have prior TLA+
exposure. That answer still needs to come from Aditya before `safetyPlan.md`
is written, because it determines whether the plan should teach the model
construction or provide a ready-to-run TLC model.
