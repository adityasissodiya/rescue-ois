# Baseline inventory and migration record

Written 2026-11-24 with AI assistance (Claude), at the start of the SRDS seed pass. This
file is the working record of the pass. It names the local snapshot and the local baseline
ref, so it is never part of an anonymous review export.

## 1. Starting identity

| Item | Value |
|---|---|
| Commit at start | `3ebd5853c87ab74316573cd6126adb2d0c57e3e9` (`main`, 2026-10-27, "feed-importer: drop four unused noqa comments") |
| Branch for this pass | `srds-2027-seed`, created from that commit. Nothing was committed during the pass; on 2026-11-25 the user asked for it to be committed and pushed |
| Git tags | none |
| `core.fileMode` | true; no mode changes in the starting tree |

Working tree at start (uncommitted):

* Modified: `paper/main.tex`, `paper/refs.bib`, `paper/sections/00_abstract.tex`,
  `paper/sections/01_introduction.tex` (the 11 November 2026 hostile-commander draft).
* Deleted: `paper/sections/02_related_work.tex` to `08_conclusion.tex` (the TCPS draft;
  recoverable with `git show 3ebd585:paper/sections/<file>`).
* Untracked: the hostile-commander draft sections `02_background.tex` to
  `10_conclusion.tex` and `A_search.tex`; `paper/STE.md`; `paper/model/mandate_sim.py`;
  `paper/scripts/ste_check.py`; `paper/ste/technical_{names,verbs}.txt`; `email.md`;
  `Hostile Commander Methodology.md`; the seed prompt; `graphify-out/`.
* Ignored: `paper/build/`, `paper/ste/dict.local.json` (via `.git/info/exclude`),
  `__pycache__/`.

## 2. Preservation

| What | Where | Check |
|---|---|---|
| Full snapshot (history bundle, working tree including untracked and ignored files, manifest) | `<private>/rescue-ois-private/snapshots/2026-11-24-pre-seed/`, outside the repository, made 2026-11-24T10:34:17Z by `artifact/private_snapshot.sh` | `sha256sum -c CHECKSUMS.sha256` in that directory |
| Private Git ref with the starting tree: HEAD plus the modified, deleted and untracked paper files. It leaves out ignored files, `graphify-out/`, `email.md`, the methodology notes and the task prompt, which only the full snapshot holds | `refs/snapshots/pre-seed-2026-11-24` = `40d0e25aa8ba9ed2c89389855b78efddcae45458` (tree `a40b9bf1`, parent `3ebd585`) | `git log -1 refs/snapshots/pre-seed-2026-11-24` |

`<private>` is the parent directory of this repository on the author's machine. Snapshot
checksums (from `CHECKSUMS.sha256`):

```
7748f2f3db1dc2e6f9c5c70c4dd6a37737c069e7a6b8d2eed3cbfa43ac6f4c28  history.bundle
856fcc59f2a133314bc259f221ec6e9cb457feb70938a331d46bcf7d35620e16  worktree.tar.gz
39ef82a1168fad2af55966aa5db2e4558a2b88c0a4c5d25b4e3917469ba0291c  MANIFEST.sha256 (426 files)
32f9ab5190071cc88dee5b15c08c52945e4b1ed2fc709f3e11dcbc813a54bc9f  STATE.txt
ccd74e1fef3a4947d0a58e7132c5409cf2355b647e1612edb59633287a781e15  git-info-exclude
```

The snapshot excludes two caches: `graphify-out/cache/` (272 files, 3.1 MB) and
`paper/scripts/__pycache__/`. It contains private material (email drafts, the ASD-derived
word list) and must stay private. The ref is local: it is not pushed (`git push` does not
send `refs/snapshots/*` unless named).

`artifact/review_diff.sh` shows every change of this pass against the private ref without
touching the real index. It leaves out the same paths as the ref. At the end of the
pass, `email.md`, the methodology notes, the task prompt, `graphify-out/` and
`paper/ste/dict.local.json` had the same SHA-256 as in the snapshot's `MANIFEST.sha256`:
the pass did not change them.

## 3. Active and legacy components

Tracked file counts and the date of the last commit that touched each path, at the start.

| Path | Files | Last commit | Status after this pass |
|---|---|---|---|
| `core/` | 60 | 2026-10-27 | Legacy prototype (incident information system); not used by the seed |
| `edge/` | 64 | 2026-09-19 | Legacy prototype |
| `baseline/`, `baseline-raft/` | 7, 9 | before 2026-09 | Legacy prototype baselines |
| `tablet/`, `ui_kits/`, `preview/` | 28, 8, 11 | before 2026-09 | Legacy scaffolds and mock-ups |
| `infra/` | 15 | 2026-04-07 | Legacy, never deployed |
| `scripts/` | 16 | before 2026-09 | Legacy Docker harnesses; **not run** in this pass (some are destructive) |
| `docs/` | 22 | before 2026-09 | Legacy documentation of the prototype |
| `formal/` | 26 | 2026-06-17 | Legacy TLA+ model of the prototype's single-journal write rule; it is **not** a model of the seed protocol and keeps its own scope |
| `testbed/` | 27 | before 2026-11 | Legacy AAS succession testbed (WONS draft `d1b1eca`, TCPS policies S0 to S5); non-Byzantine, so its numbers are not evidence about a hostile holder |
| `paper/` | 95 | — | Active: rewritten as the seed manuscript; older material listed below |

New in this pass: `spec/`, `src/mandate/`, `sim/`, `experiments/`, `tests/`,
`research/`, `artifact/`, `requirements/`, `ruff-seed.toml`, `Makefile`.

## 4. Path mapping

| Old | New | Why |
|---|---|---|
| `paper/main.tex`, `paper/sections/*.tex` as of 11 Nov 2026 | copied to `paper/history/2026-11-11-hostile-commander/` | Dated historical record; the seed manuscript replaces them |
| `paper/model/mandate_sim.py` (11 Nov random tests) | moved to `paper/history/2026-11-11-hostile-commander/model/` | Superseded by `src/mandate/`, `sim/`, `experiments/` |
| TCPS draft sections (`02_related_work.tex` to `08_conclusion.tex`) | unchanged in Git history (`3ebd585`) | Deleted before this pass; not restored |
| WONS draft | commit `d1b1eca` | Unchanged |
| `paper/data/`, `paper/tables/`, `paper/figures/`, `paper/scripts/generate_*`, `paper/model/` (TCPS era) | unchanged | Not used by the seed manuscript; kept for the TCPS line of work |
| `paper/STE.md`, `paper/scripts/ste_check.py`, `paper/ste/technical_*.txt` | unchanged | Advisory style check; `paper/ste/dict.local.json` stays local and ignored |
| `email.md`, `Hostile Commander Methodology.md` | unchanged, untracked | Private correspondence and notes; never edited or exported |
