# ADR-0006: Single Source of Truth for Evaluation Data

## Status

Accepted

## Context

`scripts/evaluate-pilot.py` previously emitted hardcoded latency numbers to `eval_metrics.log`, while plotting code used a separate set of mock arrays embedded in its own source. The two sources did not agree, and the values were treated downstream as if they were measurements. The evaluation pipeline now keeps measured JSONL output as the single reproducible source for numerical claims.

## Decision

There is exactly one source of evaluation data for the AAL harness: `artifacts/data/eval_metrics.jsonl` by default, or the path supplied in `RESCUE_OIS_METRICS_PATH`. The file format is JSON Lines, one record per measured event, with fields: `run_id`, `scenario`, `metric_name`, `value_ms`, `timestamp_iso`, `notes`.

- `scripts/evaluate-pilot.py` writes to that file. It does not embed default or fallback values.
- Downstream analysis reads measured JSONL outputs. It must not contain inline data arrays. If the file is missing or empty, downstream analysis should exit with a non-zero status and a clear error message.
- Any plot, table, or reported number must be traceable to a row in the relevant JSONL file.

## Consequences

**Positive:**

- One data source. No drift between scripts.
- Reviewer and re-runner can inspect measurements from a single artifact.
- Future addition of numerical claims is straightforward: rerun the harness and regenerate downstream analysis from JSONL.

**Negative:**

- Removes the convenience of "just regenerate plots without a fresh run."
- Requires CI discipline to keep the file fresh.
