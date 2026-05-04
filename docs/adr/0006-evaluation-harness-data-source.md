# ADR-0006: Single Source of Truth for Evaluation Data

## Status

Accepted

## Context

`scripts/evaluate-pilot.py` previously emitted hardcoded latency numbers to `eval_metrics.log`, while `paper/scripts/generate_plots.py` used a separate set of mock arrays embedded in its own source. The two sources did not agree, and the values were treated downstream as if they were measurements. The paper has been corrected; the evaluation pipeline now needs to be brought in line with that correction so that any future re-introduction of numerical claims is grounded in a single, reproducible source.

## Decision

There is exactly one source of evaluation data: `eval_metrics.jsonl` in the repository root (or under `paper/data/eval_metrics.jsonl` if a `paper/data/` directory is preferred). The file format is JSON Lines, one record per measured event, with fields: `run_id`, `scenario`, `metric_name`, `value_ms`, `timestamp_iso`, `notes`.

- `scripts/evaluate-pilot.py` writes to that file. It does not embed default or fallback values.
- `paper/scripts/generate_plots.py` reads only that file. It does not contain any inline data arrays. If the file is missing or empty, the script exits with a non-zero status and a clear error message.
- The publication pipeline (CI or local) regenerates plots only after `evaluate-pilot.py` has produced a fresh file.
- Any plot or table number must be traceable to a row in this file.

## Consequences

**Positive:**

- One data source. No drift between scripts.
- Reviewer and re-runner can reproduce paper figures from a single artifact.
- Future addition of numerical claims to the paper is trivial: rerun harness, regenerate plots.

**Negative:**

- Removes the convenience of "just regenerate plots without a fresh run."
- Requires CI discipline to keep the file fresh.
