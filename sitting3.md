# sitting3.md — Final Review, Push to Origin, Submission Hand-Off

**Audience:** Codex, post-restart, with no prior project context.
**Owner:** Aditya Sissodiya (LTU).
**Goal:** Final review pass on §VII (Discussion) for any stale claims; remove the now-obsolete "Anonymous artefact mirror URL" line from `docs/submission-checklist.md`; final PDF metadata sanity check; commit if any changes were needed; push the entire `nca2026-submission` branch to origin. End the sitting with hand-off instructions for IEEE PDF eXpress and EDAS submission — both of which are manual Aditya-side steps that Codex prepares but does not execute.
**Branch:** `nca2026-submission`.
**Estimated time:** ~1 hour.
**Prerequisite:** Sittings 1 and 2 are complete and committed. Working tree is clean before this sitting starts.

---

## 1. Project orientation (read this first if you have no context)

This is a research paper for IEEE NCA 2026 (deadline Wed 17 Jun 2026, 23:59 AoE). Offline-first incident-information architecture for rescue services over intermittent mesh networks. Sittings 1 and 2 cleaned the rendered PDF (no TODO blocks, real topology figure, fresh abstract/intro/conclusion, clean bibliography, no Type 3 fonts) and sharpened two paragraphs in §VI (recovery framing, Raft comparison framing). This sitting is the final pass.

**Read these first to orient yourself:**

- `docs/decisions.md` — submission decisions, four authors, fallback policy, deadline.
- `paper/sections/07_discussion.tex` — the file you will review. Three subsections: "Why Single Writer Instead of CRDTs", "Limitations", "Generalizability".
- `paper/sections/06_evaluation.tex` — already final after Sitting 2; do not touch.
- `docs/submission-checklist.md` — the file you will edit. Has one line referring to an "Anonymous artefact mirror URL" that no longer applies (Aditya decided not to set up an anonymous mirror).
- `paper/main.pdf` — already built and clean from Sitting 1/2; this sitting verifies metadata and embedded fonts but does not regenerate.

**Hard constraints:**

- Anonymisation must remain clean.
- Do not modify §VI in any way; Sitting 2 finalised it.
- Do not modify any measurement number anywhere.
- Push origin only at the very end of this sitting, and only after all Done Criteria pass.

---

## 2. Task order

```
T1  review §VII for stale claims                             (15 min)
T2  remove obsolete checklist line for artefact mirror       (5 min)
T3  PDF metadata final check                                 (5 min)
T4  commit (only if T1 or T2 produced changes)               (5 min)
T5  final build, anonymisation, font, page-count check       (5 min)
T6  push to origin                                           (2 min)
T7  hand-off instructions (Aditya executes, not Codex)       (15 min reading)
```

---

## 3. T1 — Review §VII for stale claims

§VII (Discussion) was last touched during the genre-shift commit (`551a6fb`) and has not been revised against the §VI rewrite. Review every claim in §VII to confirm it is still consistent with the paper as a whole.

```bash
sed -n '1,200p' paper/sections/07_discussion.tex
```

Read the full file and check each of the following:

### 3.1 Subsection "Why Single Writer Instead of CRDTs"

Look for any sentence that says or implies:
- "we plan to verify safety formally" or similar (the safety property is now verified in §VI).
- "future work includes evaluation" or "evaluation is forthcoming" (the evaluation is now in §VI).
- "a measured comparison is forthcoming" (the Raft baseline is in §VI.E).

If any such sentence exists, replace it with a present-tense statement that matches §VI. If none exist, leave the subsection unchanged.

### 3.2 Subsection "Limitations"

The current bulleted list of limitations is:

1. "the command role remains a temporary single point of failure" — still accurate; keep.
2. "promotion is manual and therefore slower than automatic failover" — still accurate; keep.
3. "polling-based synchronization adds bounded but real latency" — still accurate; the §VI numbers quantify this; keep.
4. "the present validation is an emulation, not a physical pilot, and therefore does not establish field-realistic latency, mesh behaviour, or sustained tablet survivability" — still accurate; keep.
5. "evaluation at very large fleet sizes and under multi-incident concurrency at the regional core is not addressed" — still accurate; keep.

All five are still accurate. **Confirm none of them claim that the listed item is "a separate problem we will report on" — that wording would imply the limitation is being actively investigated for this paper. The wording should be plainly factual.** If the wording in the file uses defensive softeners like "for now" or "in this version", flag them but do not edit unless they explicitly contradict §VI's numbers.

### 3.3 Subsection "Generalizability"

This subsection should be unchanged. Confirm by reading.

### 3.4 If §VII review surfaces any required edits

Apply them as small in-place edits. Most likely outcome of T1: no edits needed; this is a confirmation pass. If edits are made, they go into the same commit as T2 (see T4).

Acceptance:

```bash
echo "=== future-work-style claims in §VII ==="
grep -inE 'future work|forthcoming|we plan to|will be reported|will be shown|next phase|next submission' \
    paper/sections/07_discussion.tex || echo "OK: no stale future-work claims"
```

Expected: `OK: no stale future-work claims`. Any hits should be either (a) genuinely future work (e.g. "physical pilot" is in §VIII conclusion, not here) or (b) cleaned up.

---

## 4. T2 — Remove the obsolete artefact-mirror line from the submission checklist

`docs/submission-checklist.md` was committed during Sitting 1. It contains a checklist line referencing an anonymous artefact mirror URL. Aditya has decided not to set one up; the line should be removed so the checklist does not list a step that will be skipped.

Open `docs/submission-checklist.md` and find the line that mentions "artefact mirror" (probably reads something like `- [ ] Anonymous artefact mirror URL ready (footnote in §VI).`). The exact wording may vary; locate by:

```bash
grep -n -i 'artefact\|artifact\|mirror' docs/submission-checklist.md
```

**Delete that single line.** Leave the rest of the checklist untouched.

Verify §VI does not reference an artefact mirror URL either:

```bash
grep -n -iE 'github|gitlab|anonymized|anonymised.*mirror|artefact.*mirror|reviewer convenience' paper/sections/06_evaluation.tex
```

Expected: no matches that look like a URL or a reviewer-facing artefact reference. (The word "artefact" appears in §VI in the sense of "HTTP-client artefact"; that is a different meaning and is correct.)

If §VI does contain an actual artefact-mirror reference, **stop and report**. Sitting 2's prose edits should not have introduced one, but if Sitting 1 or some earlier work did, removing it is part of this task and the diff goes into the same commit as the checklist edit.

Acceptance:

```bash
grep -c -i 'artefact mirror\|artifact mirror' docs/submission-checklist.md
# Expected: 0
```

---

## 5. T3 — PDF metadata final check

Sittings 1 and 2 did not change PDF metadata, but verify one more time:

```bash
pdfinfo paper/main.pdf
```

Expected output (the values that matter):

- `Title:` — empty.
- `Subject:` — empty.
- `Keywords:` — empty.
- `Author:` — empty.
- `Creator:` — `LaTeX with hyperref` (or similar; not a username).
- `Producer:` — a `pdfTeX-...` version string (not a username).
- `Pages:` — between 8 and 10.
- `Page size:` — `612 x 792 pts (letter)`.

If any of `Title`, `Subject`, `Keywords`, or `Author` is non-empty, or if `Creator`/`Producer` contain anything that looks like a username, real name, or email, **stop and report**. This is an anonymisation-equivalent check and a non-empty Author field is grounds for desk-rejection at NCA per the CFP.

Also re-verify the embedded font check:

```bash
pdffonts paper/main.pdf | grep -c 'Type 3' && echo "FAIL: Type 3 fonts" || echo "OK: no Type 3 fonts"
```

Expected: `OK: no Type 3 fonts`.

---

## 6. T4 — Commit (only if T1 or T2 produced changes)

If both T1 and T2 produced no file edits (the §VII review concluded clean and the checklist line was already absent), skip to T5.

If T1 or T2 produced edits, commit them together:

```bash
git add paper/sections/07_discussion.tex docs/submission-checklist.md
git status
# Expected: only the files you edited are staged.

git commit -m 'paper, docs: final review pass

§VII: <describe any edits made; if none, this commit covers only the
checklist edit>.

docs/submission-checklist.md: remove the obsolete "Anonymous artefact
mirror URL" line. Aditya decided against an anonymous artefact mirror
for this submission; §VI does not reference one.'
```

Adjust the commit message to reflect what actually changed. If only the checklist was edited, drop the §VII line from the message.

---

## 7. T5 — Final build, anonymisation, font, page-count check

```bash
cd paper && latexmk -pdf -interaction=nonstopmode main.tex 2>&1 | tail -10 && cd ..

echo "=== page count ==="
pdfinfo paper/main.pdf | grep Pages

echo "=== anonymisation grep (paper, formal, baseline-raft) ==="
grep -rniE 'lule|ltu|sissodiya|chiquito|kristiansson|bodin|colonyos|cop[- ]?pilot|aditya|eric|johan|ulf' \
    paper/sections/ paper/main.tex paper/refs.bib formal/ baseline-raft/ \
    && echo "FAIL: anonymisation leak" || echo "OK"

echo "=== anonymisation grep (entire repo, broader sweep) ==="
grep -rniE 'aditya@|sissodiya|sissodiya@|chiquito@|kristiansson@|bodin@' \
    --exclude-dir=.git --exclude-dir=.venv-eval --exclude-dir=node_modules . \
    && echo "WARN: identifier in non-paper paths (review for safety)" || echo "OK: no identifier traces anywhere"

echo "=== TODO blocks (anywhere in paper/) ==="
grep -rnE 'TODO|FIXME|XXX' paper/sections/ paper/main.tex || echo "OK: no TODO blocks"

echo "=== Type 3 fonts ==="
pdffonts paper/main.pdf | grep -c 'Type 3' && echo "FAIL: Type 3 fonts" || echo "OK: no Type 3 fonts"

echo "=== \\TODO macro definitions still in main.tex ==="
grep -n '\\\\TODO' paper/main.tex
# The macro definition itself can stay; what matters is that no TODO is rendered.
```

All checks must report `OK`. The broader-repo identifier sweep may surface hits in commit messages, planning .md files (`pickUpFromHere.md`, `paperPlan*.md`, etc.), or your local `.venv-eval` — those are not in the submission. The paper-scoped grep is the binding one; the broader sweep is informational only.

If any binding check fails, **stop and report**.

---

## 8. T6 — Push to origin

```bash
git status
# Expected: clean tree.

git log --oneline @{u}..HEAD
# Expected: a stack of commits ahead of origin/nca2026-submission, including
# at minimum the four T1 commits from Sitting 1, the cleanup commit from
# Sitting 1, the prose-sharpening commit from Sitting 2, and (optionally)
# the final review commit from this sitting.

git push origin nca2026-submission
```

Expected: push succeeds. If it fails (network, auth, or non-fast-forward), **stop and report** — do not force-push.

After the push:

```bash
git log --oneline -10
git branch -vv
# Expected: nca2026-submission is now in sync with origin/nca2026-submission.
```

---

## 9. T7 — Hand-off instructions for Aditya

The remaining steps before submission are manual and must be done by Aditya through external systems (IEEE PDF eXpress portal, EDAS conference site). Codex's job here is to print the steps clearly so Aditya can follow them without further planner round-trips.

Print the following block as the final output of this sitting:

---

**FINAL HAND-OFF: Manual steps before submission**

**Submission deadline:** Wed 17 Jun 2026, 23:59 local time. Do not aim for the AoE deadline of Thu 18 / Fri 19 — EDAS queues at deadline are unreliable.

**Step 1 — IEEE PDF eXpress validation.**

PDF eXpress is IEEE's required pre-flight validator. Do this **at least 48 hours before submission**, because rejected submissions need a rebuild + re-validation.

1. Go to https://ieee-pdf-express.org (the official portal).
2. Create a conference account using the NCA 2026 conference ID. The ID is published in the NCA 2026 CFP at https://www.nca-ieee.org/2026/cf-papers.html — search the CFP page for "PDF eXpress" or "Conference ID".
3. Upload `paper/main.pdf`.
4. Choose "Check PDF compliance" (not "Convert"; you already have a compliant PDF source).
5. Wait for the validation report by email. Typical turnaround: minutes to a few hours.
6. **If validation passes:** download the certified PDF; replace `paper/main.pdf` with the certified output, OR save the certified output as `paper/submission.pdf`. The certified PDF is the file you upload to EDAS.
7. **If validation fails:** read the failure reason. Common ones for this paper:
   - Type 3 fonts: should not happen post-Sitting-1, but if it does, re-run `python3 paper/scripts/generate_plots.py` and rebuild.
   - Page size: should not happen with IEEEtran; if it does, verify `\documentclass[conference]{IEEEtran}` and rebuild from a clean state (`latexmk -C && latexmk -pdf paper/main.tex`).
   - Embedded forms: should not happen; if it does, ensure `\usepackage[hidelinks]{hyperref}` is set (it is).

**Step 2 — EDAS submission.**

1. Go to the NCA 2026 EDAS submission link (in the CFP at https://www.nca-ieee.org/2026/cf-papers.html — section "Submission instructions" or "Authors").
2. If no EDAS account exists yet, create one.
3. Click "Submit a paper" or equivalent.
4. Enter:
   - **Title** (verbatim from `paper/main.tex` `\title{...}`).
   - **Abstract** (verbatim from `paper/sections/00_abstract.tex` after the Sitting 1 rewrite).
   - **Keywords** (from `paper/main.tex` `IEEEkeywords` block: offline-first systems, edge computing, distributed systems, single-writer replication, intermittent connectivity, mesh networks, prototype evaluation).
   - **Authors in submission order:** Aditya Sissodiya, Eric Chiquito, Johan Kristiansson, Ulf Bodin.
   - **Affiliations:** **leave blank for double-blind submission.** They are entered at camera-ready time only. Do not enter LTU, Luleå, or anything else here.
   - **Topic tags / track:** primary "Applications, Prototypes & Experiences"; secondary "Distributed Systems & Platforms" and "Cloud, Edge, Computing Continuum"; tertiary "Mobile Ad-Hoc Networks" if multi-tag is allowed.
5. Upload the certified PDF from Step 1.
6. **Verify in EDAS preview:**
   - The author block in the rendered PDF says "Anonymous Author(s) / Anonymous Affiliation".
   - Page count is what you submitted (8–10).
   - All citations resolve.
   - PDF eXpress certification is recognised.
7. Submit. Take a screenshot of the confirmation page.

**Step 3 — After submission.**

```bash
git tag nca2026-submitted-2026-06-17
git push origin nca2026-submitted-2026-06-17
```

Tag the exact commit you submitted from. This is the reference point for any post-acceptance camera-ready divergence.

**After-notification (11 Sep 2026):**

- Accept: small revisions for camera-ready (25 Sep 2026 deadline). Affiliation block returns; acknowledgements section returns; if you decided to set up an artefact mirror later, this is when the URL goes in.
- Major revision / shepherding: real work; come back to the planner with reviewer comments in hand.
- Reject: pivot to next venue (ICDCS, SRDS submission windows are typically late Sep / Oct).

Do not plan the camera-ready phase or the reject-pivot phase now. Cross those bridges in September.

---

## 10. Hard rules

1. **Push to origin only after all done criteria pass.** Force-push is forbidden.
2. **Do not run PDF eXpress or EDAS yourself (Codex).** Those are manual Aditya-side steps. Codex prepares the artefact and the hand-off; Aditya executes.
3. **Do not modify `paper/main.pdf` after Sitting 2 except via PDF eXpress certification.** Manual edits to the binary will desync from the source.
4. **Do not introduce author identifying information.**
5. **Stop and report rather than guess** if any verbatim block does not match the file or if any check produces unexpected output.

---

## 11. Done criteria

- §VII (Discussion) reviewed and confirmed clean (or edited where stale).
- `docs/submission-checklist.md` no longer contains the "Anonymous artefact mirror URL" line.
- `paper/main.pdf` builds cleanly, page count ≤ 10, no Type 3 fonts, anonymisation grep clean, PDF metadata clean.
- All commits pushed to origin; `git status` clean; `git branch -vv` shows `nca2026-submission` in sync with origin.
- Hand-off block in §9 above printed at the end of the Codex output so Aditya has the manual-step instructions.

When all hold, Aditya proceeds with PDF eXpress and EDAS manually. Codex is done.

End of sitting3.md.
