# Building the paper

The project is configured for MiKTeX and VS Code with LaTeX Workshop.

## Command line

From this directory, run:

```powershell
.\build.ps1
```

The PDF and intermediate files are written to `build/`; the paper source is left uncluttered.

## VS Code

Open this directory in VS Code, open `main.tex`, and run **LaTeX Workshop: Build LaTeX project**. The workspace recipe runs `pdflatex`, BibTeX, and the two final `pdflatex` passes needed to resolve citations and cross-references. The PDF opens in a VS Code tab.

MiKTeX is configured to install a missing LaTeX package automatically when the project first needs it.
