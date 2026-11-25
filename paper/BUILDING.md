# Building the seed paper

The seed uses IEEE's `IEEEtran` class in conference mode, BibTeX with `IEEEtran.bst`, and
TikZ. We built it with TeX Live 2023 (Debian, pdfTeX 1.40.25) and `latexmk`; other
distributions are untested. On Debian or Ubuntu, `texlive-publishers`,
`texlive-latex-extra`, `texlive-pictures`, `texlive-science` and `latexmk` should be
enough.

## Commands

From the repository root:

```bash
make paper        # build/main.pdf: names, affiliations and acknowledgment
make paper-anon   # build/main-anon.pdf: the anonymous review build
```

Or by hand, from this directory:

```bash
latexmk -pdf -interaction=nonstopmode -halt-on-error -outdir=build main.tex
latexmk -pdf -interaction=nonstopmode -halt-on-error -outdir=build -jobname=main-anon main-anon.tex
python3 scripts/page_count.py build/main
```

The build reads `generated/`. If it is missing, run `make seed` (and `make tla` for the
model-check numbers) first.

## The review build

`main-anon.tex` defines `\seedanon` and inputs `main.tex`. With it:

* the title block says "Anonymous authors" and "Affiliation withheld for review";
* `authors.tex`, `authors_meta.tex` and `acks.tex` are not read;
* the PDF author field is empty, and pdfTeX writes no creation date, source file name
  or banner.

`make paper-anon` checks the metadata. `make export` builds the review PDF again, copies
an allowlist of files to `../artifact/out/review/`, and fails if the PDF text or any
exported file contains a name, an affiliation, a funding identifier or a local path.

## The TCPS manuscript

The TCPS manuscript (`acmart`) is not built from this branch. To build it, check out
commit `3ebd585` in a separate worktree (`git worktree add ../tcps 3ebd585`) and follow
its `paper/BUILDING.md`.
