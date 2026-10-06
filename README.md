# AAS paper (working draft)

This branch holds the LaTeX source of the paper on Authority-Aligned Sequencing (AAS): how
an incident command organization's authority rules become the rules of an incident journal
shared over intermittent links, and which of those rules need consensus between devices.
The prototype it builds on is on the `main` branch of this repository.

**Status:** a working draft, not for submission. Text in orange brackets, written with
`\pending{}`, marks open points or planned work, not results.

## Layout

| Path | Contents |
| --- | --- |
| `main.tex` | Preamble and the order of the sections |
| `sections/` | The paper's sections |
| `figures/` | Figures; `figures/README.md` says which ones the paper includes |
| `tables/`, `data/`, `scripts/` | Generated tables, the evaluation datasets, and the scripts that generate tables and figures from them |
| `model/` | The scenario and system model document, built on its own |
| `TRACEABILITY.md` | Every number in the paper, traced to its dataset and generator |
| `refs.bib` | The bibliography |

## Building

`BUILDING.md` has the details. In PowerShell, with MiKTeX installed:

```powershell
.\build.ps1          # the paper: build\main.pdf
.\model\build.ps1    # the scenario and system model: model\build\scenario-and-model.pdf
```
