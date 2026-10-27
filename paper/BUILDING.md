# Building the manuscript

The manuscript uses ACM's `acmart` class (`acmsmall`) and BibTeX with
`ACM-Reference-Format`. Both ship with MiKTeX and TeX Live.

## Windows, MiKTeX

From this directory:

```powershell
.\build.ps1
```

The PDF and intermediate files are written to `build/`. MiKTeX installs missing packages
the first time the project needs them.

## Linux or macOS, TeX Live

```bash
latexmk -pdf -interaction=nonstopmode -outdir=build main.tex
```

On Debian or Ubuntu, `texlive-publishers`, `texlive-fonts-extra`, `texlive-latex-extra`,
`texlive-science`, `texlive-pictures`, `texlive-plain-generic` and `latexmk` are enough.

## Testbed numbers

`data/testbed_macros.tex` and the rows in `tables/tab_policy_costs.tex` and
`tables/tab_faults.tex` are generated from the testbed's committed results. To refresh
them, from the rescue-ois checkout that has `testbed/`:

```bash
cd testbed
python -m aas_testbed latex --out <this directory>/data
mv <this directory>/data/tab_*.tex <this directory>/tables/
```
