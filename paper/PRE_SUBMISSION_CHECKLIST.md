# Pre-Submission Checklist (NCA 2026)

Branch: `nca2026-submission`. Submission deadline: **2026-06-19 AoE**.

Verify every item before uploading the PDF to EDAS. Re-run the
verification commands and confirm each box.

## Anonymity

- [x] **`\author{Anonymous Author(s)}` set in `paper/main.tex`.**

  ```bash
  grep -n "author" paper/main.tex | head
  ```
  Expected: `\IEEEauthorblockN{Anonymous Author(s)}` and
  `\IEEEauthorblockA{Anonymous Affiliation \\ Submitted to NCA 2026
  (double-blind review)}`.

- [x] **PDF metadata clean: Author / Creator / Producer empty;
  CreationDate / ModDate suppressed.**

  ```bash
  pdfinfo paper/main.pdf
  ```
  Expected: `Author:` empty; `Creator:` empty; `Producer:` empty; no
  `CreationDate:` or `ModDate:` lines. `Title:` is the paper title;
  `Subject:` is `NCA 2026 Submission`; `Keywords:` is empty.

- [x] **No identity strings in the PDF text or binary.**

  ```bash
  pdftotext paper/main.pdf - | grep -iE "(sissodiya|chiquito|bodin|kristiansson|luleå|lulea|\bltu\b|aditya|thinkpad)"
  strings paper/main.pdf | grep -iE "(/home|/media|aditya|thinkpad|hostname)"
  ```
  Both must return nothing.

- [x] **No acknowledgements section in the source.**

  ```bash
  grep -niE "\\\\section\{acknow|acknowledgement" paper/sections/ paper/main.tex
  ```
  Only matches should be the protocol verb "acknowledges/acknowledged"
  inside §III prose, not a section heading.

- [x] **No self-citations.** This paper has no prior published work
  by the authors that needs to be cited; verified by grep for
  "in our prior work", "we previously", etc.

  ```bash
  grep -iE "(in our (prior|previous)|in earlier work by us|we previously)" paper/sections/*.tex
  ```
  Must return nothing.

- [ ] **GitHub repository visibility (manual step).** If
  `github.com/<account>/rescue-ois` is currently public, flip it to
  private until camera-ready. The repository URL contains the
  author's username; history rewrite cannot fix this. Defer the
  history-rewrite-or-anonymized-mirror decision to after acceptance.

## Format

- [x] **IEEE conference template, two-column.**

  ```bash
  head -2 paper/main.tex
  ```
  Expected: `\documentclass[conference]{IEEEtran}`.

- [x] **Page count ≤ 10.**

  ```bash
  pdfinfo paper/main.pdf | grep Pages
  ```
  Must be `Pages: 10` or fewer. NCA 2026 hard cap is 10 pages (8
  base + 2 paid extra at €100 each = €200 in page fees).

- [x] **Bibliography references resolve.** No "undefined reference",
  "multiply defined", or "citation undefined" warnings on the final
  latexmk pass.

  ```bash
  cd paper && rm -f main.{pdf,aux,bbl,blg,fls,fdb_latexmk,log,out}
  latexmk -pdf -interaction=nonstopmode main.tex > /dev/null 2>&1
  grep -iE "(undefined|multiply.defined)" main.log
  ```
  Must return nothing.

## Submission bundle

- [x] **Bundle is `paper/main.pdf` only.** Documented in
  `paper/SUBMISSION_BUNDLE.md`. Do not upload JSONL data files,
  scripts, the supervisor research report, the whitepaper, or any
  internal planning documents alongside the PDF. The PDF carries
  all claims the paper makes; supplementary artefacts create
  additional anonymity surface and are not needed for review.

## EDAS administrative entries

- [ ] **EDAS author entries** (real names, affiliations, ORCIDs) are
  filled in only at camera-ready time. EDAS author records are
  administrative and not visible to reviewers, but use the
  pre-submission slot to verify only that the PDF upload succeeds
  and the page count is accepted.

## Final pre-upload command

Run from the repo root, immediately before uploading:

```bash
cd paper
latexmk -C
latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
pdfinfo main.pdf | grep -E "Pages|Author|Creator|Producer|CreationDate|ModDate"
pdftotext main.pdf - | grep -iE "(sissodiya|chiquito|bodin|kristiansson|luleå|lulea|\bltu\b|aditya|thinkpad)" || echo "anonymity OK"
strings main.pdf | grep -iE "(/home|/media|aditya|thinkpad|hostname)" || echo "strings OK"
```

If `Pages:` is `10` or fewer, the two greps echo `OK`, and no
`CreationDate` / `ModDate` / non-empty `Author` / non-empty `Creator`
/ non-empty `Producer` appears in `pdfinfo`, the PDF is ready to
upload.

## Roll-back if anything breaks

The pre-Phase-5 known-good state is on `nca2026-submission` after
the Phase 6.4 checklist commit (search `git log --grep "Phase 6.4"`
for the exact SHA). If Phase 5 introduces regressions and time runs
short, revert to that commit before submission.
