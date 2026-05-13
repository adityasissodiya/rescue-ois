# NCA 2026 Paper Sources

This directory contains the IEEEtran manuscript sources for an NCA 2026 regular
paper submission.

Target topic framing:

- Primary: Network Architectures & Protocols
- Secondary: Applications, Prototypes & Experiences

The manuscript frames Rescue OIS as an authority-aligned synchronization
architecture/protocol for rescue-service incident response over intermittent
edge networks. It must not claim field deployment, a validated Android path,
production readiness, full implementation proof, or physical mesh measurements.

## Build

```bash
cd paper
latexmk -pdf -interaction=nonstopmode main.tex
```

## Data And Generated Artifacts

- `data/` contains measured JSONL artifacts and must not be hand-edited.
- `tables/` contains generated table snippets. Regenerate them with
  `scripts/generate_tables.py` and `scripts/generate_baseline_table.py` when
  measurement inputs change.
- `figures/` contains paper figures and generated plots.

## Double-Blind Checks

Before submission, run the repository submission checks and inspect the PDF
manually. The paper must not include author names, affiliations, GitHub URLs,
self-identifying artifact metadata, or institution-identifying prose. Keep
venue logistics and author-side planning out of the submitted manuscript.
