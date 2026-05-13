# NCA 2026 EDAS Submission Checklist

- [ ] Fresh `cd paper && latexmk -pdf -interaction=nonstopmode main.tex` build.
- [ ] No undefined citations or references in `paper/main.log`.
- [ ] `pdfinfo paper/main.pdf` shows no author-identifying metadata.
- [ ] Anonymisation grep clean for the manuscript and reviewer-facing bundle.
- [ ] Page count <= 10 pages for regular paper with both paid extra pages.
- [ ] PDF eXpress validation passed if required by the final submission system.
- [ ] All `% verify` markers resolved in `paper/refs.bib`, or unused incomplete references removed.
- [ ] Submission-ready PDF saved as `paper/submission.pdf`.
- [ ] Track selected, if one is required: Network Architectures & Protocols.
- [ ] Secondary/topic tags, if allowed: Applications, Prototypes & Experiences; Distributed Systems & Platforms; Cloud, Edge, Computing Continuum.
- [ ] Mobile Ad-Hoc Networks selected only if the final manuscript keeps mesh/MANET claims explicitly scoped as target architecture, not physical evaluation.
- [ ] Author identities, affiliations, acknowledgements, and internal artifact metadata kept outside the double-blind submission PDF and reviewer-facing bundle.
- [ ] Submission completed >=48 hours before the regular-paper deadline.
