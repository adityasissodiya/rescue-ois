# NCA 2026 EDAS Submission Checklist

- [ ] Fresh `cd paper && latexmk -pdf -interaction=nonstopmode main.tex` build.
- [ ] No undefined citations or references in `paper/main.log`.
- [ ] `pdfinfo paper/main.pdf` shows no author-identifying metadata.
- [ ] Reviewer bundle exported from a working tree without `.git/`, local remotes, branch names, or commit history.
- [ ] `python3 paper/scripts/anonymize_data.py --in-place paper/data/*.jsonl baseline/data/*.jsonl` run after any harness rerun.
- [ ] Anonymisation grep clean for the manuscript and reviewer-facing bundle.
- [ ] Android/tablet package namespace remains neutral (`org.review.rescueois`).
- [ ] Page count <= 10 pages for regular paper with both paid extra pages.
- [ ] PDF eXpress validation passed if required by the final submission system.
- [ ] All `% verify` markers resolved in `paper/refs.bib`, or unused incomplete references removed.
- [ ] Submission-ready PDF saved as `paper/submission.pdf`.
- [ ] Track selected, if one is required: Network Architectures & Protocols.
- [ ] Secondary/topic tags, if allowed: Applications, Prototypes & Experiences; Distributed Systems & Platforms; Cloud, Edge, Computing Continuum.
- [ ] Mobile Ad-Hoc Networks selected only if the final manuscript keeps mesh/MANET claims explicitly scoped as target architecture, not physical evaluation.
- [ ] Author identities, affiliations, acknowledgements, and internal artifact metadata kept outside the double-blind submission PDF and reviewer-facing bundle.
- [ ] Submission completed >=48 hours before the regular-paper deadline.
