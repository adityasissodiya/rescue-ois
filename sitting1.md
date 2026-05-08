# sitting1.md — Pre-Submission Cleanup Pass: Blockers

**Audience:** Codex, post-restart, with no prior project context.
**Owner:** Aditya Sissodiya (LTU).
**Goal:** Take the working tree from "all the recent work is uncommitted plus three blockers exist in the rendered PDF" to a state where the paper has no visible TODOs, the abstract and §I and §VIII match the actual content of §VI, the bibliography contains no printable "Verify..." text, and the embedded fonts in `fig_recovery.pdf` are TrueType (PDF eXpress compliant). End the sitting on a clean tree with all changes committed in a logical sequence.
**Branch:** `nca2026-submission` (already on it).
**Estimated time:** ~3 hours.
**This is one of three sittings. Sittings 2 and 3 follow.**

---

## 1. Project orientation (read this first if you have no context)

This is a research paper for IEEE NCA 2026 (deadline Wed 17 Jun 2026). Offline-first incident-information architecture for rescue services over intermittent mesh networks. Phase 1 (IEEE template + anonymisation), Phase 2 (real measurements, 365 rows), Phase 3 (TLA+ + Hypothesis safety verification), and Phase 4 (Raft baseline, 160 rows) are all complete in code/data — but Phase 4 plus the §VI rewrite plus the bibliography DOI cleanup are uncommitted on disk. The most recent committed work is Phase 3 (`b563dcd`).

**Read these first to orient yourself:**

- `docs/decisions.md` — submission decisions, four authors, fallback policy.
- `paper/main.tex` — IEEE conference template entry. **No TikZ packages currently loaded.**
- `paper/sections/01_introduction.tex` — research question, contributions list, R1–R5 derivation pointer.
- `paper/sections/03_system_architecture.tex` — line 57 has a TODO figure block (system topology). This is one of the three blockers.
- `paper/sections/04_synchronization_protocol.tex` — lines 29 and 45 have TODO figure blocks (sequence diagram, partition state diagram). The other two blockers.
- `paper/sections/06_evaluation.tex` — full §VI rewrite already done; uncommitted.
- `paper/sections/00_abstract.tex` — stale; still claims evaluation is "scheduled for the next submission phase."
- `paper/sections/08_conclusion.tex` — stale; still claims formal verification is future work.
- `paper/refs.bib` — partially cleaned but still has nine `note = {... [Vv]erify ...}` fields that print in the rendered bibliography.
- `paper/scripts/generate_plots.py` — produces `fig_recovery.pdf`. Currently uses matplotlib defaults which embed a Type 3 font (`DejaVuSans`); this fails IEEE PDF eXpress validation.

**Hard constraints throughout this sitting:**

- Do not push to origin yet. All commits stay local until end of Sitting 3.
- Do not introduce author identifying information. Anonymisation grep must remain clean.
- Page count must stay ≤ 10. Current is 8 with 2 pages of headroom; the topology figure and longer prose may add ~half a page.
- Do not modify `paper/data/eval_metrics.jsonl` or `paper/data/eval_metrics_raft.jsonl`. They are the canonical measurement sources per ADR-0006.

---

## 2. Task order and dependencies

```
T1  organise uncommitted work into 4 logical commits         (15 min)
T2  add TikZ packages to paper/main.tex preamble             (5 min)
T3  build system topology figure (TikZ verbatim)             (45 min)
T4  remove TODO sequence diagram in §IV.C                    (5 min)
T5  remove TODO partition state diagram in §IV.D             (5 min)
T6  rewrite abstract                                         (10 min)
T7  fix §I roadmap final paragraph                           (3 min)
T8  fix §VIII conclusion future-work first item              (5 min)
T9  clean printable "Verify..." notes from refs.bib          (15 min)
T10 fix matplotlib Type 3 font; regenerate fig_recovery.pdf  (10 min)
T11 build, anonymisation grep, page count check              (10 min)
T12 single cleanup commit                                    (5 min)
```

T1 must be first (commits the existing work cleanly so subsequent diffs are readable). T2 must precede T3 (TikZ needs the package). T11 must be last before the commit. The rest are independent.

---

## 3. T1 — Organise uncommitted work into logical commits

The working tree currently has substantial uncommitted Phase 4 + §VI rewrite + bib cleanup work. Commit in this exact order so each commit is buildable on its own.

### T1a — Phase 4 Raft baseline + tables infra

```bash
git add baseline-raft/
git add scripts/evaluate-raft-baseline.py
git add paper/scripts/generate_baseline_table.py
git add paper/scripts/generate_tables.py
git add paper/data/eval_metrics_raft.jsonl
git add paper/tables/tab_baseline.tex
git add paper/tables/tab_evaluation.tex
git add .gitignore
```

If `git status` shows `paper/tables/README.md` or `paper/figures/README.md` as modified, include them too — they are stub READMEs that may have been touched.

Commit:

```
git commit -m 'paper, baseline-raft: Phase 4 measured Raft baseline and table generation

Adds baseline-raft/ — a 3-voter hashicorp/raft cluster mirroring the
journal-commit path on the shared rescue-ois-net network — and the
evaluator scripts/evaluate-raft-baseline.py producing
paper/data/eval_metrics_raft.jsonl (160 rows: 90 propagation + 60
follower catch-up + 10 quorum-lost).

Adds paper/scripts/generate_tables.py and generate_baseline_table.py
which materialise paper/tables/tab_evaluation.tex and tab_baseline.tex
from the canonical .jsonl data files per ADR-0006.

.gitignore extended for baseline-raft Go build artefacts.'
```

### T1b — §VI rewrite

```bash
git add paper/sections/06_evaluation.tex
git add paper/scripts/generate_plots.py
git add README.md
```

Commit:

```
git commit -m 'paper: §VI rewrite integrating Phase 2, Phase 3, and Phase 4 results

Replaces the placeholder evaluation section with five subsections:
emulation environment; sync protocol latency and recovery; steady-state
throughput; idempotency and safety verification (TLA+ + Hypothesis);
comparison with consensus-based replication (Raft baseline);
limitations and threats to validity. All numerical claims trace to
paper/data/eval_metrics.jsonl (365 rows) or paper/data/eval_metrics_raft.jsonl
(160 rows).'
```

### T1c — Bibliography metadata cleanup with verified DOIs

```bash
git add paper/refs.bib
```

Commit:

```
git commit -m 'paper: bibliography metadata cleanup with verified DOIs

Resolves DOIs and missing fields for the load-bearing entries in §I and
§II via public sources: RSG operational guidance (rsg-rad201,
rsg-kommunalplan), karaman2024resilient (IEEE Comm. Surveys & Tutorials),
wisniewski2023continuity (IEEE Access), oecd2019resilience,
marshall2023telecommunications (J. Rural Studies), murphy2021digital
(Linköping Licentiate thesis), pilemalm2014enabling (IJES), and
westman2021mobilisation (Scand. J. Trauma).'
```

### T1d — Submission checklist

```bash
git add docs/submission-checklist.md
```

Commit:

```
git commit -m 'docs: NCA 2026 submission checklist'
```

### Verification

```bash
git status
# Expected: clean tree (no modified, no untracked work-bearing files).
# Untracked planning .md files (paperPlan*.md, prototypePlan.md,
# safetyPlan.md, sitting1.md, etc.) and the docs/*.zip files remain;
# leave them.

git log --oneline -8
# Expected: top of stack reads:
# <new>  docs: NCA 2026 submission checklist
# <new>  paper: bibliography metadata cleanup with verified DOIs
# <new>  paper: §VI rewrite integrating Phase 2, Phase 3, and Phase 4 results
# <new>  paper, baseline-raft: Phase 4 measured Raft baseline and table generation
# b563dcd formal: real-stack opt-in tests, .gitignore for TLC logs ...
# 0aa6a1f formal: option 3 — single-journal authority model ...
```

If any of T1a–T1d errors out, **stop and report**. Do not start the cleanup edits on a tree with mixed-state commits.

Build verification before moving on:

```bash
cd paper && latexmk -pdf -interaction=nonstopmode main.tex && cd ..
```

Should build cleanly. Confirm `paper/main.pdf` exists and is 8 pages (`pdfinfo paper/main.pdf | grep Pages`). If the build is broken at this point, the commit ordering interacted badly with `\input{tables/...}` references — investigate and report.

---

## 4. T2 — Add TikZ packages to paper/main.tex preamble

Open `paper/main.tex`. After the line `\usepackage[nameinlink,noabbrev]{cleveref}` (currently line 17), insert:

```latex
\usepackage{tikz}
\usetikzlibrary{positioning,arrows.meta,shapes.geometric,fit,backgrounds}
```

Acceptance:

```bash
grep -n 'usetikzlibrary' paper/main.tex
# Expected output: a line containing 'positioning,arrows.meta,...'

cd paper && latexmk -pdf -interaction=nonstopmode main.tex && cd ..
# Build still passes; no new warnings.
```

---

## 5. T3 — Build system topology figure

Replace the TODO block in `paper/sections/03_system_architecture.tex` (around line 56–60) with a TikZ figure. The block to replace is:

```latex
\begin{figure}[t]
  \centering
  \fbox{\parbox{0.95\columnwidth}{\centering TODO: system topology figure\\Core, command vehicle, responder vehicle, relay, tablets,\\plus mesh, WireGuard, and local VLAN annotations.}}
  \caption{Planned deployment topology figure for the three-tier architecture.}
  \label{fig:topology}
\end{figure}
```

Replace with this verbatim TikZ figure (a layered three-tier diagram, single-column width):

```latex
\begin{figure}[t]
\centering
\begin{tikzpicture}[
  node distance=4mm and 6mm,
  every node/.style={font=\footnotesize},
  tier/.style={draw, rounded corners=1pt, minimum height=7mm, align=center},
  core/.style={tier, fill=gray!10, minimum width=42mm},
  edge/.style={tier, minimum width=22mm},
  tablet/.style={tier, fill=white, minimum width=14mm, font=\scriptsize, minimum height=5mm},
  wan/.style={->, >=stealth, semithick},
  wandash/.style={->, >=stealth, semithick, dashed},
  mesh/.style={<->, >=stealth, thick, dashed},
  link/.style={-, semithick}
]

\node[core] (core) {Regional core\\\scriptsize (master DB, sync API, package publisher)};

\node[edge, below=12mm of core, xshift=-15mm] (cmd) {Command edge\\\scriptsize (journal, forward)};
\node[edge, below=12mm of core, xshift=15mm]  (resp) {Responder edge\\\scriptsize (cache, outbox)};

\draw[wan]     (cmd)  -- (core) node[midway, left, font=\scriptsize] {WireGuard};
\draw[wandash] (resp) -- (core) node[midway, right, font=\scriptsize] {(when WAN)};

\draw[mesh] (cmd) -- (resp) node[midway, above, font=\scriptsize] {Rajant mesh};

\node[tablet, below=8mm of cmd]  (t1) {Tablet};
\node[tablet, below=8mm of resp] (t2) {Tablet};

\draw[link] (t1) -- (cmd)  node[midway, right, font=\scriptsize] {HTTPS};
\draw[link] (t2) -- (resp) node[midway, right, font=\scriptsize] {HTTPS};

\end{tikzpicture}
\caption{Three-tier deployment topology. The regional core hosts master
data and the sync API; vehicle edges run a command or responder role;
tablets connect only to their local edge over HTTPS. Mesh transit
between edges is independent of WAN reachability to the core.}
\label{fig:topology}
\end{figure}
```

Acceptance:

```bash
cd paper && latexmk -pdf -interaction=nonstopmode main.tex && cd ..
grep -c 'TODO: system topology figure' paper/sections/03_system_architecture.tex
# Expected: 0
```

The PDF should now have a real topology diagram in §III. If the TikZ produces compile errors, **stop and report** with the LaTeX log line. Do not start tweaking the figure layout without sign-off.

---

## 6. T4 — Remove TODO sequence diagram in §IV.C

Open `paper/sections/04_synchronization_protocol.tex`. Find the figure block around lines 27–32:

```latex
\begin{figure}[t]
  \centering
  \fbox{\parbox{0.95\columnwidth}{\centering TODO: sequence diagram\\Tablet $\rightarrow$ responder outbox $\rightarrow$ command journal\\$\rightarrow$ responder/tablet fan-out $\rightarrow$ core backhaul}}
  \caption{Planned sequence diagram for the forward-only field edit flow.}
  \label{fig:sequence}
\end{figure}
```

**Delete the entire `\begin{figure}...\end{figure}` block.** No replacement.

The numbered list above it (steps 1–7 in §IV.C) is already a clear sequence specification; the figure was redundant.

Then update the prose reference to the figure. Find the line:

```latex
The steady-state field edit path proceeds as follows (\cref{fig:sequence}):
```

Replace with:

```latex
The steady-state field edit path proceeds as follows:
```

Acceptance:

```bash
grep -c 'TODO: sequence diagram' paper/sections/04_synchronization_protocol.tex
# Expected: 0
grep -c 'fig:sequence' paper/sections/04_synchronization_protocol.tex
# Expected: 0 (label gone, no dangling \cref)
cd paper && latexmk -pdf -interaction=nonstopmode main.tex && cd ..
# No undefined-reference warnings about fig:sequence.
```

---

## 7. T5 — Remove TODO partition state diagram in §IV.D

Same file. Find the figure block around lines 43–48:

```latex
\begin{figure}[t]
  \centering
  \fbox{\parbox{0.95\columnwidth}{\centering TODO: partition state diagram\\Full connectivity, mesh-only, isolated responder, isolated command, promoted responder}}
  \caption{Planned partition behavior diagram.}
  \label{fig:partition}
\end{figure}
```

**Delete the entire `\begin{figure}...\end{figure}` block.** No replacement.

The bulleted list of partition cases above it (responder loses mesh, command loses WAN, command lost) already covers the same ground in prose.

Search for any `\ref{fig:partition}` or `\cref{fig:partition}` in `paper/sections/`:

```bash
grep -rn 'fig:partition' paper/sections/
# Expected: 0 hits
```

If any reference exists, remove or rephrase it inline.

Acceptance:

```bash
grep -c 'TODO: partition state diagram' paper/sections/04_synchronization_protocol.tex
# Expected: 0
cd paper && latexmk -pdf -interaction=nonstopmode main.tex && cd ..
# No undefined-reference warnings.
```

---

## 8. T6 — Rewrite abstract

Replace the entire content of `paper/sections/00_abstract.tex` with:

```latex
Edge applications spanning vehicle nodes, field tablets, and intermittent wide-area links need replication protocols that remain useful during partitions without obscuring which node has authority to commit safety-relevant state. We present an offline-first incident-information architecture for rescue services that combines a regional core, vehicle edge nodes, and leaf tablets with a deliberately asymmetric synchronisation protocol: master data flows outward, tablets and responder vehicles submit forward-only outbox events, and exactly one command vehicle sequences the incident journal. The architecture occupies a different point in the replication design space from consensus-based state-machine replication, multi-primary replication, and CRDT-style merge. The design is derived from publicly available operational requirements of a Swedish municipal rescue service. We evaluate the prototype on a Docker Compose emulation across six scenarios totaling 365 measured runs, verify the single-writer safety property with TLA+ model checking and a Hypothesis property-test corpus, and compare against a 3-voter \texttt{hashicorp/raft} baseline. The comparison isolates the architectural trade-off: under quorum loss, the consensus baseline cannot make progress, while the proposed design preserves write availability at the cost of automatic failover.
```

Acceptance:

```bash
grep -c 'scheduled for the next submission phase' paper/sections/00_abstract.tex
# Expected: 0
grep -c '365 measured runs' paper/sections/00_abstract.tex
# Expected: 1
cd paper && latexmk -pdf -interaction=nonstopmode main.tex && cd ..
```

---

## 9. T7 — Fix §I roadmap final paragraph

Open `paper/sections/01_introduction.tex`. Find the line near the bottom:

```
Section~\ref{sec:validation} reports the planned NCA evaluation.
```

Replace with:

```
Section~\ref{sec:validation} reports the evaluation, the formal safety verification, and the Raft baseline comparison.
```

Acceptance:

```bash
grep -c 'planned NCA evaluation' paper/sections/01_introduction.tex
# Expected: 0
grep -c 'formal safety verification' paper/sections/01_introduction.tex
# Expected: 1
```

---

## 10. T8 — Fix §VIII conclusion future-work first item

Open `paper/sections/08_conclusion.tex`. Find the second paragraph beginning with "Three concrete lines of future work follow..." The first item currently reads:

```
First, formal protocol verification: the single-writer journal combined with manual promotion and forward-only outbox semantics is amenable to model checking, for example in TLA+, to verify the absence of split-brain commits across all interleavings of partition and promotion.
```

Replace this sentence with:

```
First, extending the formal verification with liveness properties and a refinement argument from the present TLA+ model down to the implementation; the current model establishes safety only.
```

Keep the second and third items (physical pilot, mesh-hardware measurement campaign) untouched — they remain genuine future work.

Acceptance:

```bash
grep -c 'First, formal protocol verification' paper/sections/08_conclusion.tex
# Expected: 0
grep -c 'extending the formal verification with liveness' paper/sections/08_conclusion.tex
# Expected: 1
```

---

## 11. T9 — Clean printable "Verify..." notes from `refs.bib`

Nine entries currently have `note = {... [Vv]erify ...}` fields that print in the rendered bibliography. One has a meaningful prefix worth keeping; the rest get the entire `note = {...}` line removed.

For each entry below, locate the line by bibkey and apply the change.

### `kohler2025consistent` — delete the note line entirely

Find:
```
  note      = {Authors and pages: verify before submission}
```
Delete this line (including the comma on the previous line if removing leaves a trailing comma — see safety rule below).

### `lindstrom2025tripod` — replace with the meaningful prefix only

Find:
```
  note      = {Swedish Ethical Review Authority approval No.~2023-04615-01. Verify full author list and DOI.}
```
Replace with:
```
  note      = {Swedish Ethical Review Authority approval No.~2023-04615-01.}
```

### `opach2023map` — delete the note line

Find:
```
  note      = {Verify full author list, volume, issue, pages, DOI.}
```
Delete this line.

### `paul2019crimp` — delete the note line

Find:
```
  note      = {Verify full author list, volume, pages, DOI.}
```
Delete this line.

### `almeida2014delta` — delete the note line

Find:
```
  note      = {Verify pages and publisher.}
```
Delete this line.

### `mentler2014cognitive` — delete the note line

Find:
```
  note      = {Verify volume, issue, pages, DOI.}
```
Delete this line.

### `liang2025holipaxos` — delete the note line

Find:
```
  note      = {Verify volume, issue, pages.}
```
Delete this line.

### `mucha2023database` — delete the note line

Find:
```
  note      = {Verify volume, pages, DOI.}
```
Delete this line.

### `gooding2025lark` — delete the note line

Find:
```
  note      = {Mark as preprint; cite only if a peer-reviewed version is not available by submission. Verify before camera-ready.},
```
Delete this line. (Note: this line ends with a comma; the line above must still end correctly — see safety rule.)

### Comment-only blocks — delete

The bottom of `refs.bib` has two comment-only blocks that don't render but are stale clutter:

Find this block (starts after the last `@`-entry):
```
% Verification notes:
% - walle2016situation: verify DOI.
...
% - gooding2025lark: preprint; verify peer-reviewed replacement before camera-ready.
% Still needed before submission:
% - Swedish authority and infrastructure sources (MSB, RAKEL, Lantmateriet, SOS Alarm)
% - Recent ISCRAM 2025-2026 papers on responder coordination, COPs, and field deployment systems
% - Product or standards references for Rajant, WireGuard deployment guidance, and any public-safety interoperability standards
```

Delete the entire block.

### Safety rule for BibTeX line removal

When deleting a `note = {...}` line that is *not* the last field in its entry, the previous field's trailing comma is fine — leave it. When deleting a `note` that *is* the last field (the one immediately above the closing `}`), the previous field's trailing comma may now leave a trailing comma before `}` — that's syntactically tolerated by BibTeX but flag it if you spot it. Most importantly, **do not accidentally delete the closing `}` of the entry**.

After all deletions, verify:

```bash
grep -nEi 'note\s*=.*verify' paper/refs.bib
# Expected: no matches.

grep -c '^% Verification notes:' paper/refs.bib
# Expected: 0

grep -c '^% Still needed before submission:' paper/refs.bib
# Expected: 0

cd paper && latexmk -pdf -interaction=nonstopmode main.tex && cd ..
# Build succeeds. Bibliography compiles cleanly. No "Verify" text appears
# in the rendered bibliography.
```

If `latexmk` fails with a BibTeX syntax error, the most likely cause is an entry where the deleted `note` line was the last field and now the closing `}` directly follows a trailing comma on a previous-field line. Inspect the diff and fix.

---

## 12. T10 — Fix matplotlib Type 3 font; regenerate `fig_recovery.pdf`

The current `paper/figures/fig_recovery.pdf` embeds a Type 3 font (`BMQQDV+DejaVuSans`) which fails IEEE PDF eXpress validation. Fix matplotlib's PDF backend to emit TrueType fonts (Type 42) instead.

Open `paper/scripts/generate_plots.py`. After the `import matplotlib` line and before `matplotlib.use("Agg")`, insert:

```python
matplotlib.rcParams["pdf.fonttype"] = 42
matplotlib.rcParams["ps.fonttype"] = 42
```

So the import block becomes:

```python
import matplotlib

matplotlib.rcParams["pdf.fonttype"] = 42
matplotlib.rcParams["ps.fonttype"] = 42
matplotlib.use("Agg")
import matplotlib.pyplot as plt
```

Re-run the figure generator:

```bash
python3 paper/scripts/generate_plots.py
```

Verify no Type 3 fonts remain in the output:

```bash
pdffonts paper/figures/fig_recovery.pdf | grep -i 'type 3' && echo "FAIL: Type 3 font present" || echo "OK: no Type 3 fonts"
```

Expected: `OK: no Type 3 fonts`.

Then rebuild the paper to embed the new figure:

```bash
cd paper && latexmk -pdf -interaction=nonstopmode main.tex && cd ..
pdffonts paper/main.pdf | grep -i 'type 3' && echo "FAIL: Type 3 font in main.pdf" || echo "OK: no Type 3 fonts in main.pdf"
```

Expected: `OK: no Type 3 fonts in main.pdf`.

If a Type 3 font persists in `main.pdf`, it may come from another source than the figure. Check the full font list:

```bash
pdffonts paper/main.pdf
```

The original gather showed only `BMQQDV+DejaVuSans` as Type 3; the rest are Type 1 with `emb yes`. After this fix, all should report `Type 1` or `TrueType` with `emb yes`. If something else surfaces as Type 3, **stop and report** with the full pdffonts output.

---

## 13. T11 — Build, anonymisation grep, page count check

```bash
cd paper && latexmk -pdf -interaction=nonstopmode main.tex 2>&1 | tail -20 && cd ..

echo "=== undefined references / citations ==="
grep -cE 'undefined (reference|citation)' paper/main.log || echo "OK"

echo "=== page count ==="
pdfinfo paper/main.pdf | grep Pages

echo "=== anonymisation grep ==="
grep -rniE 'lule|ltu|sissodiya|chiquito|kristiansson|bodin|colonyos|cop[- ]?pilot|aditya|eric|johan|ulf' \
    paper/sections/ paper/main.tex paper/refs.bib formal/ baseline-raft/ \
    && echo "FAIL: anonymisation leak" || echo "OK"

echo "=== TODO blocks remaining ==="
grep -rnE 'TODO|FIXME|XXX' paper/sections/ paper/main.tex || echo "OK: no TODO blocks"

echo "=== fonts ==="
pdffonts paper/main.pdf | grep -c 'Type 3' && echo "FAIL: Type 3 fonts" || echo "OK: no Type 3 fonts"
```

Expected outcomes:

- `latexmk` ends with `Latexmk: All targets (main.pdf) are up-to-date` or a normal build report; no errors.
- `OK` for undefined references / citations.
- Page count: 8 or 9. **If 10, it's borderline; if >10, stop and report.** The topology figure adds ~half a page; the abstract is slightly longer; everything else is the same length or shorter.
- `OK` for anonymisation grep.
- `OK` for TODO blocks.
- `OK` for Type 3 fonts.

If any check fails, **stop and report** with the failing check's output.

---

## 14. T12 — Single cleanup commit

```bash
git add paper/main.tex
git add paper/sections/00_abstract.tex
git add paper/sections/01_introduction.tex
git add paper/sections/03_system_architecture.tex
git add paper/sections/04_synchronization_protocol.tex
git add paper/sections/08_conclusion.tex
git add paper/refs.bib
git add paper/scripts/generate_plots.py
git add paper/figures/fig_recovery.pdf

git status
# Expected: only planning .md files and zips remain untracked. Working tree
# clean for committed paths.

git commit -m 'paper: pre-submission cleanup pass

- §III: replace TODO topology placeholder with TikZ three-tier diagram.
- §IV: remove TODO sequence and partition-state placeholder figures;
  the prose enumeration in §IV.C and the bullet list in §IV.D are
  sufficient.
- Abstract: rewritten to describe completed work (six scenarios, 365
  measured runs, TLA+/Hypothesis safety verification, Raft baseline
  comparison) instead of "scheduled for the next phase."
- §I roadmap: section reference now says "the evaluation" not "the
  planned NCA evaluation."
- §VIII conclusion: first future-work item changed from "formal
  protocol verification" (now done) to "extending the formal
  verification with liveness properties and refinement to the
  implementation."
- refs.bib: nine printable "Verify..." note fields cleaned (kohler,
  lindstrom partial, opach, paul, almeida, mentler, liang, mucha,
  gooding); two comment-only stale blocks removed.
- generate_plots.py: pdf.fonttype/ps.fonttype = 42 for IEEE PDF eXpress
  compliance; fig_recovery.pdf regenerated as TrueType-embedded.

Build clean, anonymisation grep clean, no Type 3 fonts in main.pdf,
8 pages.'
```

---

## 15. Hard rules

1. **Do not push to origin.** All commits stay local until end of Sitting 3.
2. **Do not modify `paper/data/eval_metrics.jsonl` or `paper/data/eval_metrics_raft.jsonl`.** They are canonical.
3. **Do not invent bibliography fields.** If a `Verify...` note's content suggests a real datum (like the ethical review number for `lindstrom2025tripod`), keep just that datum; otherwise delete the entire note line.
4. **Do not change architectural claims or §VI numbers.** This sitting is presentation polish only.
5. **Stop and report rather than guess** if any verbatim block in this plan does not match the file. Files were inspected before writing this plan; if drift, ask before proceeding.
6. **Do not move on to Sitting 2.** Sittings are run as separate Codex sessions to allow Aditya to review intermediate state.

---

## 16. Done criteria

- `git log --oneline -8` shows the four T1 commits plus the T12 cleanup commit, all on `nca2026-submission`, ahead of `b563dcd`.
- `git status` shows a clean tree (only planning .md files and `docs/*.zip` untracked).
- `paper/main.pdf` is 8 or 9 pages, builds cleanly, has no Type 3 fonts, no TODO blocks, no "Verify..." text in the bibliography.
- `paper/sections/00_abstract.tex`, `01_introduction.tex`, `08_conclusion.tex` no longer contain stale "scheduled for the next phase / planned NCA evaluation / formal protocol verification (future work)" claims.
- `paper/sections/03_system_architecture.tex` contains a real TikZ topology figure, not a placeholder.
- Anonymisation grep is clean.

When all hold, send a fresh sitrep with: page count, font check output, anonymisation grep result, and the diff stats from the cleanup commit. Do not start Sitting 2.

End of sitting1.md.
