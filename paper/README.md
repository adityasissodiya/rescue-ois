# ISCRAM Paper Scaffold

This directory contains a compileable LaTeX scaffold for the paper outlined in [`../ISCRAM_PAPER_OUTLINE.md`](../ISCRAM_PAPER_OUTLINE.md).

The manuscript currently uses a generic `article`-based two-column layout so writing can start immediately. Replace the class file and margin settings with the official ISCRAM 2027 template once the call for papers is published.

## Build

```bash
cd paper
latexmk -pdf main.tex
```

## Contents

- `main.tex`: top-level manuscript file
- `sections/`: section stubs aligned to the outline
- `refs.bib`: seed bibliography assembled from Consensus results and a small number of recent ISCRAM proceedings entries
- `figures/`: planned figure placeholders
- `tables/`: planned table placeholders

## Notes

- The bibliography is intentionally focused on the core framing: crisis-response information systems, local-first/offline-first systems, and public-safety networking.
- Swedish authority reports and project-specific sources still need to be added before submission, especially for MSB, RAKEL, and any local pilot context.
- Some BibTeX entries are minimal seed entries rather than camera-ready metadata. Enrich them with DOI, page ranges, and publisher details before submission.

