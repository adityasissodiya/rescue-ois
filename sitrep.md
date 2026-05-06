# Rescue OIS Submission Sitrep

Date: 2026-05-06
Branch: `nca2026-submission`

## Current Commit Stack

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
  30 runs. This should be made explicit in Section VI or the evaluator should
  emit 30 skipped rows for shape consistency.
- `partition_wan` audit rows are sparse and should not share the canonical
  metrics stream with the Python evaluator. Move partition audit output to a
  separate `partition_audit.jsonl`.
- The `command_throughput` low outlier is `run_index=0`:
  53.920090271790066 ev/s. The following runs immediately jump to the expected
  range around 168--173 ev/s, so Section VI can treat the first throughput run
  as warm-up and drop/warn on it.

## Paper State

The NCA paper is in IEEE skeleton form and now reads as a problem-driven
systems paper. The introduction states the research question, Section III
derives R1--R5 from operational requirements, Section IV maps protocol choices
to R1--R3, and Section VII argues explicitly why CRDT/local-first logic does
not satisfy R3.

Do not write measured numbers into Section VI until the canonical metrics file
has been committed under `paper/data/` and any plot/table generation is pointed
at that file.

## Next Submission Work

Immediate work before Phase 3:

1. Move `eval_metrics.jsonl` to `paper/data/eval_metrics.jsonl` and commit it
   as the ADR-0006 source of truth.
2. Apply the small evaluator/partition quality-of-life fixes:
   promotion run count consistency, separate partition audit output, and
   throughput warm-up marking.
3. Stop before Phase 3 until `safetyPlan.md` exists.

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
