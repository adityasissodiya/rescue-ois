# Submission Anonymity Audit (NCA 2026)

Run date: 2026-05-13. Branch: `nca2026-submission`.
Search command (executed from repo root):
```
grep -RIln -E "(Sissodiya|Chiquito|Bodin|Kristiansson|Luleå|Lulea|\bLTU\b|aditya|ThinkPad|/media/aditya)" \
  --exclude-dir=.git --exclude-dir=node_modules --exclude-dir=__pycache__ \
  --exclude-dir=.venv-eval --exclude-dir=.pytest_cache --exclude-dir=.hypothesis \
  --exclude-dir=preview \
  --exclude='*.pdf' --exclude='*.bbl' --exclude='*.aux' --exclude='*.fls' \
  --exclude='*.log' --exclude='*.fdb_latexmk' --exclude='*.blg' \
  --exclude='*.out' --exclude='*.synctex.gz'
```

Token `rescue-ois` is excluded from the strict grep above because it is the project's docker-network / package name and appears in dozens of build files without identifying the author. It is treated separately below (Bucket D).

The LaTeX source (`paper/sections/*.tex`, `paper/main.tex`, `paper/refs.bib`) is **clean** — `\author{Anonymous Author(s)}` is set in `main.tex:28` and grep for the identity tokens in `paper/sections/` and `paper/refs.bib` returns no matches.

## Bucket A — Identity leaks in files inside the build path

These files are read by paper scripts or referenced from the paper. They must be scrubbed before any artifact-bundle distribution.

| File | What leaks | Remediation |
|------|------------|-------------|
| `paper/data/eval_command_local_partition.jsonl` | 2 records contain `environment` block with `host_uname=Linux aditya-ThinkPad-T14-Gen-4 …`, `host_cpu_model=13th Gen Intel(R) Core(TM) i7-1355U`, `host_mem_total_kb=32520844`. The `summary` record also contains absolute paths `/media/aditya/File System 21/rescue-ois/paper/data/...` in `scenario_params.artifact_path` and `audit_artifact_path`. | Task 1.2: write `paper/scripts/anonymize_data.py`, emit `*.anon.jsonl`. |

The remaining files under `paper/data/` are clean:

- `paper/data/eval_command_local_partition.audit.jsonl` — 2 lines, no env block, no absolute paths.
- `paper/data/eval_metrics.jsonl` — 390 lines, no env block, no leak tokens.
- `paper/data/eval_metrics_raft.jsonl` — 160 lines, no env block, no leak tokens.

The repo-root `partition_audit.jsonl` is clean (no env block, no leak tokens). It is not referenced from the paper. Out of submission scope, but harmless.

## Bucket B — Build artifacts (regenerated each build, gitignored)

`paper/main.fls`, `paper/main.aux`, `paper/main.log`, `paper/main.fdb_latexmk`, `paper/main.bbl`, `paper/main.blg`, `paper/main.out`, `paper/main.synctex.gz`.

All match `paper/.gitignore`. They contain absolute build paths (e.g. `/media/aditya/...`). They are **never** part of the submission bundle (Task 1.5 fixes the bundle to PDF-only). Action: confirmed gitignored, no further action.

## Bucket C — Documentation / scaffolding files outside the submission bundle

These files were leak sources in earlier drafts. None of them are part of the submission bundle. All four are now in the repo-root `.gitignore` to keep them out of any future archive snapshot:

- `README.md` (repo root) — references the project name and contains contributor pointers. Not in submission bundle.
- `Rescue OIS Whitepaper.html` (repo root) — pre-anonymization marketing HTML. Gitignored.
- `Rescue OIS Supervisor-Review Research Report.md` (repo root) — gitignored, contains author name.
- `CLAUDE_CODE_PLAN.md` (repo root) — gitignored, contains author name.

## Bucket D — Project-name strings (`rescue-ois`)

`rescue-ois` appears in: `edge/docker-compose.yml`, `core/docker-compose.yml`, `baseline-raft/`, `scripts/`, `infra/`, `tablet/settings.gradle.kts`, `formal/python/pyproject.toml`, `formal/python/uv.lock`, `edge/syncd/pyproject.toml`, `edge/syncd/src/config.py`, etc.

This token is the docker-network and Python package name. It is **not author-identifying on its own**. None of these files are in the submission bundle (PDF-only, Task 1.5). The paper PDF itself never uses the slug `rescue-ois`; it uses the prose name "Rescue OIS" only.

**Risk:** if a reviewer searches Google for the string "Rescue OIS" they may find this repository (and a public GitHub mirror would expose the author). The paper does not link to any repository URL. Recommendation: do not include an artifact-availability URL in the submission PDF; if an artifact is published for camera-ready, mirror it under an anonymized account first.

## Bucket E — Files with identity outside the submission bundle but worth flagging

- `.github/CODEOWNERS` — contains `@aditya-sissodiya`. Not in submission bundle. Will be visible if the repo is ever made public; keep private until camera-ready, and rewrite before any public push.
- `.claude/settings.local.json` — contains `/media/aditya/...` paths in permission strings. Local-only, untracked, not in submission bundle.

## Per-file remediation status

| Bucket | File | Status |
|--------|------|--------|
| A | `paper/data/eval_command_local_partition.jsonl` | Pending — Task 1.2 |
| B | `paper/main.{fls,aux,log,fdb_latexmk,bbl,blg,out,synctex.gz}` | OK — gitignored |
| C | `Rescue OIS Whitepaper.html` | OK — gitignored |
| C | `Rescue OIS Supervisor-Review Research Report.md` | OK — gitignored |
| C | `CLAUDE_CODE_PLAN.md` | OK — gitignored |
| C | `README.md` | OK — not in bundle, no further action |
| D | `rescue-ois` slug across infra/build files | OK — not in bundle |
| E | `.github/CODEOWNERS` | OK — not in bundle; rewrite before public push |
| E | `.claude/settings.local.json` | OK — untracked, local-only |

## Final-PDF anonymity check (deferred to Task 6.2)

After all edits land, the binding test is:
```
cd paper && rm -f main.pdf main.aux main.bbl main.blg main.fls main.fdb_latexmk main.log main.out
latexmk -pdf -interaction=nonstopmode main.tex
pdfinfo main.pdf
pdftotext main.pdf - | grep -iE "(sissodiya|chiquito|bodin|kristiansson|luleå|lulea|\bltu\b|aditya|thinkpad)"
strings main.pdf | grep -iE "(/home|/media|aditya|thinkpad|hostname)"
```
All four greps must return nothing; `pdfinfo` Author must be empty.
