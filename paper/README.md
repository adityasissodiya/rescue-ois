# Ending command authority at disconnected devices (SRDS seed, working draft)

A working seed for an IEEE conference paper. SRDS 2027 is the candidate venue; no call
for papers was out on 24 November 2026, so the format follows the SRDS 2026 call: 10
pages excluding references, IEEE two-column, double-blind, and an optional, clearly
marked appendix that reviewers may read. `../research/positioning.md` records the venue
facts and the prior work.

**Status:** not a submission. Every lemma and proposition is a candidate, and no person
has reviewed the arguments. The text, the specification and the code were drafted with
an AI assistant (Claude). All times in the evidence are synthetic integers. The status
box on the first page says the same. Each claim carries an identifier (for example
`C-SEP`) that matches a row of `../research/claims.csv`.

On `main`, this directory holds the TCPS manuscript instead. Its sources are at commit
`3ebd585`.

## Layout

| Path | Contents |
| --- | --- |
| `main.tex` | Preamble (`IEEEtran`, conference) and the order of the sections. If `\seedanon` is defined, it makes the review build |
| `main-anon.tex` | The review build: defines `\seedanon` and inputs `main.tex` |
| `authors.tex`, `authors_meta.tex`, `acks.tex` | Names and affiliations, the PDF author field, and the acknowledgment. Only the author build reads them; the review export never contains them |
| `sections/` | Sections 00 to 09, and appendices A (candidate arguments in full) and B (reproduction) |
| `generated/` | Numbers, tables and Figure 1, written by `make seed` and `make tla`. Do not edit |
| `refs.bib` | The bibliography, shared with the TCPS manuscript; the seed cites a subset |
| `scripts/page_count.py` | Counts the main-text pages and checks the PDF metadata; `make paper` and `make paper-anon` run it |
| `STE.md`, `scripts/ste_check.py`, `ste/` | The advisory style check (below) |
| `history/2026-11-11-hostile-commander/` | The 11 November 2026 draft of this paper, unchanged, with a README that lists its known problems |
| `TCPS_PLAN.md`, `TRACEABILITY.md`, `data/`, `tables/`, `figures/`, `model/`, `build.ps1`, other `scripts/` | Files of the TCPS manuscript. The seed does not use them |

## Building

From the repository root, `make paper` writes `build/main.pdf` and `make paper-anon`
writes `build/main-anon.pdf`. Both print the number of main-text pages and fail if it is
more than 10. The label `end-of-main-text`, before the references, marks the end of the
main text. `make paper-anon` also fails if the PDF metadata names an author or carries
pdfTeX file information. [`BUILDING.md`](BUILDING.md) has the details.

## Numbers

No number from the experiments or the model check is typed by hand. `make seed` writes
`generated/seed_macros.tex`, `seed_table.tex`, `comparison_table.tex` and
`removal_figure.tex` from `../experiments/results/`. `make tla` writes
`generated/tla_macros.tex` from `../spec/tla/logs/`.

## Style check (advisory)

`python3 scripts/ste_check.py` checks the prose against the Simplified Technical English
rules in `STE.md`. The check is advisory: it does not stop the build, and the seed text
does not pass it in full. The ASD-STE100 dictionary file `ste/dict.local.json` is
copyrighted. It is excluded locally (`.git/info/exclude`) and must never be committed,
shared or put in an export.
