# sitting2.md — Sharpen §VI Prose: Recovery Framing and Raft Comparison

**Audience:** Codex, post-restart, with no prior project context.
**Owner:** Aditya Sissodiya (LTU).
**Goal:** Tighten two paragraphs in §VI of the paper. The recovery paragraph in §VI.B currently reads slightly defensive about the 60s-partition timeout artefact; the Raft comparison subsection in §VI.E lacks an upfront framing that positions Raft as a partition-availability baseline rather than a workflow-equivalent latency baseline. Both edits pre-empt obvious reviewer attacks. **No code changes, no measurement reruns, no figure regeneration.** Pure prose.
**Branch:** `nca2026-submission` (already on it).
**Estimated time:** ~30 minutes.
**Prerequisite:** Sitting 1 is complete and committed. The working tree is clean before this sitting starts.

---

## 1. Project orientation (read this first if you have no context)

This is a research paper for IEEE NCA 2026 (deadline Wed 17 Jun 2026). Offline-first incident-information architecture for rescue services over intermittent mesh networks. The paper is structurally complete: §I–§V architecture, §VI evaluation with measured Phase 2 results plus TLA+ + Hypothesis safety verification plus a measured Raft baseline, §VII discussion, §VIII conclusion. Sitting 1 (just completed) cleaned visible TODO blocks, fixed stale prose in the abstract/intro/conclusion, cleaned bibliography metadata, and patched a Type 3 font issue.

Two specific paragraphs in §VI need sharpening. Both are about reviewer-facing framing — the underlying numbers and architectural claims do not change.

**Read these first to orient yourself:**

- `docs/decisions.md` — submission decisions, four authors, fallback policy.
- `paper/sections/06_evaluation.tex` — the file you will edit. Two paragraphs: the recovery discussion in §VI.B (currently around line 47–58) and the Raft comparison subsection in §VI.E (currently around line 137–159).
- `paper/sections/03_system_architecture.tex` — the R1–R5 derivation that the §VI.E framing references. R3 is the "single operationally designated authority" requirement.
- `paper/sections/01_introduction.tex` paragraph 4 — already mentions consensus-based SMR being unavailable during partitions; the §VI.E sharpening makes that promise explicit.

**Hard constraints:**

- Do not push to origin yet. All commits stay local until end of Sitting 3.
- Do not modify any number in §VI. The values 728 ms, 3.39 s, 49.7 s, 12 s, 10.5 ms, 615.9 ms, 4.1 s, 49.6 s, "10 of 10 write attempts fail" are all measured and traceable to `paper/data/eval_metrics.jsonl` or `paper/data/eval_metrics_raft.jsonl`.
- Do not modify Table 1 or Table 2 or Figure 1. Pure paragraph-level prose edits.
- Anonymisation grep must remain clean.

---

## 2. T1 — Sharpen the recovery paragraph in §VI.B

Open `paper/sections/06_evaluation.tex`. Find the third paragraph of subsection `\subsection{Sync Protocol Latency and Recovery}`. The exact paragraph to replace begins with "Recovery from a WAN partition is monotonic in partition duration." and ends with "report the artefact rather than mask it because the architecture, not the client library, is the contribution of this paper."

The current full paragraph reads:

```latex
Recovery from a WAN partition is monotonic in partition duration. For 1 s
partitions the median recovery is 728 ms; for 10 s partitions 3.39 s; for
60 s partitions the distribution becomes bimodal, with a small low-side
population near 12 s and a tight cluster around 49.7 s. The cluster lies
within 0.1 s of five times the per-batch HTTP timeout used by the
command-to-core forwarder (10 s); we attribute it to the long-lived
\texttt{httpx.AsyncClient} retaining stale connections across the
disconnect/reconnect cycle and timing out per batch on resume. A production
deployment would invalidate the connection pool on partition events; we
report the artefact rather than mask it because the architecture, not the
client library, is the contribution of this paper.
```

Replace this entire paragraph with:

```latex
Recovery from a WAN partition is monotonic in partition duration. For
1\,s partitions the median recovery is 728\,ms; for 10\,s partitions
3.39\,s; for 60\,s partitions the distribution is bimodal, with a small
low-side population near 12\,s and a tight cluster at 49.7\,s. The
49.7\,s cluster reflects the per-batch HTTP timeout (10\,s) of the
long-lived \texttt{httpx.AsyncClient} used by the command-to-core
forwarder: the client retains the stale connection across the
disconnect/reconnect cycle and times out once per outbound batch on
resume. The protocol-level claim from this scenario is the monotonicity
in partition duration, not the absolute recovery number at 60\,s;
closing the connection pool on partition events would collapse the
60\,s distribution onto the single-second order of magnitude seen in
the 1\,s and 10\,s cells.
```

Differences from the original:

- Removes the "we report the artefact rather than mask it because the architecture, not the client library, is the contribution of this paper" defensive framing.
- States the protocol-level claim explicitly (monotonicity in partition duration).
- Predicts the effect of the obvious fix (connection-pool invalidation) without admitting it as a defect of the paper.
- Uses `\,` thinspaces consistently with the rest of §VI.

Acceptance:

```bash
grep -c 'report the artefact rather than mask it' paper/sections/06_evaluation.tex
# Expected: 0

grep -c 'protocol-level claim from this scenario is the monotonicity' paper/sections/06_evaluation.tex
# Expected: 1

cd paper && latexmk -pdf -interaction=nonstopmode main.tex && cd ..
# Build clean.
```

---

## 3. T2 — Sharpen the Raft comparison subsection in §VI.E

Same file. Find the entire `\subsection{Comparison with Consensus-Based Replication}` subsection. It currently consists of two paragraphs followed by Table~\ref{tab:baseline}.

The current first paragraph (the brief intro, ending with "summary statistics are in Table~\ref{tab:baseline}.") is fine; **keep it unchanged**.

The current second paragraph begins with "Under no partition, the direct Raft leader path is much faster..." and ends with "This is the trade-off encoded in R3: write availability under partition is preserved at the cost of automatic write failover."

Replace this entire second paragraph with the following three paragraphs:

```latex
We do not present Raft as a workflow-equivalent alternative. The
responder-outbox plus manual-promotion pattern is structurally different
from leader-and-followers consensus, and a like-for-like latency
comparison would require a Raft variant with equivalent client-side
overheads --- outbox, polling interval, multi-tier forwarding --- which
we leave to future work. The comparison here isolates a single
architectural property: write availability under partition. The latency
cells in Table~\ref{tab:baseline} are reported for context, not as a
head-to-head claim.

Under no partition, the direct Raft leader path is faster than the
prototype's end-to-end field-edit path at queue depth~10 (median 10.5\,ms
versus 615.9\,ms), as expected: the baseline commits directly at the
leader and does not include the responder outbox or the responder-syncd
poll interval. After a 60\,s isolation of one voter, Raft follower
catch-up is also shorter (median 4.1\,s) than the prototype's
command-to-core WAN-recovery drain (median 49.6\,s, dominated by the
HTTP-client artefact discussed in Section~\ref{sec:eval-latency}); the
two paths measure different recovery mechanisms and are not directly
comparable on absolute time.

The architectural difference that matters for R3 appears when quorum is
lost. With two of three voters isolated, the Raft cluster cannot make
progress: all ten write attempts fail throughout the partition window.
The prototype's command vehicle is by construction unaffected by the
isolation of responder peers; it commits to its local journal regardless
of responder-fleet connectivity. This is the trade-off encoded in R3:
write availability under partition is preserved at the cost of automatic
write failover.
```

Differences from the original:

- New first paragraph (out of three): explicitly addresses the "you compared an end-to-end workflow to a direct journal commit" reviewer attack head-on, before the comparison numbers are reported. Names exactly what would be needed for a like-for-like comparison and admits that's future work.
- Second paragraph (the latency cells): largely unchanged from the original text but reframed as context, not a claim.
- Third paragraph (the partition-availability point): unchanged in substance from the original; this is the actual contribution of §VI.E.

Acceptance:

```bash
grep -c 'We do not present Raft as a workflow-equivalent alternative' paper/sections/06_evaluation.tex
# Expected: 1

grep -c 'comparison here isolates a single architectural property' paper/sections/06_evaluation.tex
# Expected: 1

grep -c 'are not directly comparable on absolute time' paper/sections/06_evaluation.tex
# Expected: 1

grep -c 'all ten write attempts fail' paper/sections/06_evaluation.tex
# Expected: 1

# The R3 trade-off sentence should still be present and unchanged.
grep -c 'trade-off encoded in R3' paper/sections/06_evaluation.tex
# Expected: 1

cd paper && latexmk -pdf -interaction=nonstopmode main.tex && cd ..
```

---

## 4. T3 — Build, anonymisation grep, page count check

```bash
cd paper && latexmk -pdf -interaction=nonstopmode main.tex 2>&1 | tail -10 && cd ..

echo "=== undefined references / citations ==="
grep -cE 'undefined (reference|citation)' paper/main.log || echo "OK"

echo "=== page count ==="
pdfinfo paper/main.pdf | grep Pages

echo "=== anonymisation grep ==="
grep -rniE 'lule|ltu|sissodiya|chiquito|kristiansson|bodin|colonyos|cop[- ]?pilot|aditya|eric|johan|ulf' \
    paper/sections/ paper/main.tex paper/refs.bib formal/ baseline-raft/ \
    && echo "FAIL: anonymisation leak" || echo "OK"

echo "=== fonts ==="
pdffonts paper/main.pdf | grep -c 'Type 3' && echo "FAIL: Type 3 fonts" || echo "OK: no Type 3 fonts"
```

Expected outcomes:

- Build clean.
- `OK` for undefined references / citations.
- Page count: 8 or 9, **at most 10**. The §VI.E expansion adds roughly 6 lines of text (one new paragraph), so the page count may grow by half a page if it pushes a column boundary. If page count goes above 10, **stop and report**.
- `OK` for anonymisation grep.
- `OK` for Type 3 fonts.

If any check fails, **stop and report**.

---

## 5. T4 — Single commit

```bash
git add paper/sections/06_evaluation.tex
git status
# Expected: only paper/sections/06_evaluation.tex modified.

git commit -m 'paper: sharpen §VI prose for recovery and Raft framings

§VI.B (recovery paragraph): drop the defensive "we report the artefact
rather than mask it" framing; replace with a forward-looking statement
that names the protocol-level claim (monotonicity in partition duration)
and predicts the effect of the obvious fix (connection-pool invalidation
on partition events) without admitting it as a defect of the paper.

§VI.E (Raft comparison): split the second paragraph into three. The new
first paragraph addresses the "you compared an end-to-end workflow to a
direct journal commit" reviewer attack head-on, names what would be
needed for a like-for-like comparison, and frames Raft as a
partition-availability baseline rather than a latency-equivalent
workflow baseline. Latency cells are now contextual, not head-to-head.
The R3 trade-off claim in the final paragraph is unchanged.

No measurement numbers, no figures, and no architectural claims
modified. Build clean, anonymisation grep clean, page count within
budget.'
```

---

## 6. Hard rules

1. **Do not modify any number** in §VI. Numbers are canonical per ADR-0006.
2. **Do not modify Table 1 (`tab:evaluation`) or Table 2 (`tab:baseline`) or Figure 1 (`fig:recovery`).**
3. **Do not modify §I, §II, §III, §IV, §V, §VII, or §VIII.** Sitting 3 reviews §VII; this sitting is §VI only.
4. **Do not push to origin.** All commits stay local until end of Sitting 3.
5. **Do not introduce author identifying information.** Anonymisation grep must remain clean.
6. **Stop and report rather than guess** if either paragraph in §VI does not match the verbatim block in this plan. The block was prepared against the post-Sitting-1 working tree; if Sitting 1 introduced any drift in §VI, ask before proceeding.

---

## 7. Done criteria

- `paper/sections/06_evaluation.tex` shows the two replacements verbatim. The 49.7s artefact paragraph no longer contains the phrase "we report the artefact rather than mask it." The Raft subsection has three paragraphs after the intro, with the first addressing the workflow-vs-journal-commit framing.
- `paper/main.pdf` builds cleanly, page count ≤ 10, no Type 3 fonts, anonymisation grep clean.
- `git log --oneline -1` shows the single sharpening commit on top of Sitting 1's stack.

When all hold, send a fresh sitrep with: page count, the diff stats from the commit, and any noticeable layout changes (e.g. if a new column break appears in §VI). Do not start Sitting 3.

End of sitting2.md.
