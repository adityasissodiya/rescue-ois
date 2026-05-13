# NCA 2026 Submission Bundle

## What gets uploaded to EDAS

**One file: `paper/main.pdf`.**

That is the entire submission bundle. Nothing else is uploaded, attached, or
linked from the PDF.

## What is NOT in the bundle

Do not ship, link to, or otherwise reference any of:

- `paper/data/*.jsonl` (raw or anonymized) — evaluation artefacts. Numbers
  appear inside the PDF; the JSONL files do not need to ship.
- `paper/data/*.anon.jsonl` — same reason. The anonymized files exist for the
  case where the repo is later opened (camera-ready / artifact track), not for
  the initial submission.
- `paper/scripts/*` — generator scripts (`generate_tables.py`,
  `generate_baseline_table.py`, `generate_plots.py`, `anonymize_data.py`).
- `paper/figures/*` source files — final figures are embedded in `main.pdf`;
  the source files do not ship separately.
- `paper/SUBMISSION_ANONYMITY_AUDIT.md`, `paper/SUBMISSION_BUNDLE.md`,
  `paper/PRE_SUBMISSION_CHECKLIST.md` — internal-only artefacts.
- `paper/diagram-notes/*` — internal planning notes.
- `README.md` (repo root) — project README.
- `Rescue OIS Whitepaper.html` (repo root) — pre-anonymization document.
- `Rescue OIS Supervisor-Review Research Report.md` (repo root) — names the
  author and supervisors.
- `CLAUDE_CODE_PLAN.md` (repo root) — names the author.
- `infra/rajant/`, `infra/rutx50/` — physical mesh notes; out of scope.
- `tablet/` Kotlin / Android scaffold — out of scope per Discussion non-claims.
- `formal/` — TLA+ and Hypothesis models. Evidence summaries appear in the
  PDF; the model sources do not ship.
- Any `.aux`, `.bbl`, `.blg`, `.fls`, `.fdb_latexmk`, `.log`, `.out`,
  `.synctex.gz` — these embed the build host's absolute paths and must never
  ship.

## Why PDF-only

1. **NCA 2026 reviews the PDF.** Supplementary artefacts are optional and
   create additional anonymity surfaces to audit.
2. **The headline claims in the paper are supported in the PDF itself.** The
   protocol description, the model-level evidence summary, and the
   service-path measurements are all in §IV–§V.
3. **Anonymizing JSONL files for upload is harder than skipping them.** Even
   after stripping `host_uname` and absolute paths, the `git_commit` value
   pins the data to a specific commit on a repository that, if it ever becomes
   public, names the author.

## If you want a public artifact link for camera-ready

Do not link from the submission PDF. After acceptance, mirror the evaluation
inputs (`paper/data/*.anon.jsonl`, the evaluation scripts, and the migration
files) under an anonymized-then-deanonymized account, and include the URL in
the camera-ready preamble only.

## Build the bundle

```
cd paper
latexmk -C
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
# Upload only ./main.pdf to EDAS.
```

The pre-upload check is `paper/PRE_SUBMISSION_CHECKLIST.md` (Task 6.4).
