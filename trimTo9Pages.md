# Claude Code task: trim the paper to ≤9 pages and reframe for the APE track

You are working in the AAL paper repository (`paper/`). The paper currently
builds to **10 pages**, with all references on page 10. Two goals, in priority
order:

1. **Hard constraint: the compiled PDF must be ≤9 pages including references.**
   This is non-negotiable. The submission track caps at 9 pages.
2. **Reframe for the target track.** This paper is going to the *Applications,
   Prototypes & Experiences* track at NCA 2026, not a theory/algorithms track.
   It should read like **"this is the operational problem, this is the prototype
   we built to meet it, and this is what measuring it taught us"** — not like a
   novel-mechanism paper. The authors already concede the mechanisms aren't
   novel; lean into that.

Do **not** sacrifice goal 1 for goal 2. Hit the page limit first; the reframe is
how you decide *what* to cut, not an excuse to add.

---

## Method: measure, cut, re-measure (mandatory loop)

1. Compile first (`latexmk -pdf main.tex` or the repo's build command) and record
   the baseline page count and undefined-reference count.
2. Make one batch of cuts from the prioritized list below.
3. Recompile, record the new page count.
4. Repeat until ≤9 pages. **Stop cutting as soon as you hit 9** — do not
   over-trim. If you reach 9 after the float cuts alone, leave the prose mostly
   intact beyond the reframe edits.
5. Never estimate page count from word count; always read it from the compiled
   PDF.

You need to remove roughly **two columns (~one page)** of content. The float and
related-work cuts below are sized to deliver that without touching §V's
measurement story.

---

## The reframe lens (use this to judge every cut)

Cut text that does **neither** of these:
- helps a reviewer judge whether the prototype is real, sound, and reproducible, **or**
- surfaces an actual insight from building or measuring it.

Survey-style "here is a body of related work, it doesn't solve our exact problem"
prose fails both tests for this track and is the first thing to go. Keep the
implementation/artifact detail (it proves the prototype exists) and the
evaluation insights (they're the "experiences").

---

## Prioritized cut list

Work top-down. Each item notes the file and why it's safe to cut for this track.

### Tier 1 — floats (highest page-leverage, lowest insight loss)

- **Drop `fig_recovery`** (`sections/06_evaluation.tex`, the second V-F figure).
  The V-F result is now sub-second and monotone; three medians in prose
  (0.75/0.91/0.23 s) fully convey it. A scatter plot of a boring-good result
  earns no space.
- **Drop `fig_partition_timeline`** (the first V-F figure, the scope diagram).
  The prose already states the surgical command↔core cut and what stays
  reachable. If after Tier 1+2 you are exactly at 9 and want to keep one V-F
  figure for readability, keep this one over `fig_recovery` — but default to
  cutting both.
- **Drop Table II `tab:req-trace`** (`sections/02_problem_analysis.tex`). It
  restates the R1/R2/R3 bullets directly above it plus two deployment
  constraints. Fold the two deployment constraints (mesh-as-transit; reuse
  rescue-service identity infra) into one sentence of the surrounding prose and
  delete the table.
- **Remove the commented-out `fig_topology_scope` block** in
  `sections/03_architecture.tex` (dead LaTeX). Cosmetic, but do it.

Keep these floats — they carry results or prove the artifact is real, both of
which the APE track rewards:
- `fig_promotion_cost` (the "fence is cheap" headline; only cut as a last resort
  if you are still over 9 after all of Tier 1–3).
- Table I `tab:state-contracts`, Table `tab:impl-mapping` (the
  concept→artifact map — high value for a prototype track), and the three
  results tables `tab:evaluation`, `tab:falsification-cost`,
  `tab:crdt-comparison`.

### Tier 2 — survey-style prose (compress hard for this track)

- **`sections/02_problem_analysis.tex`, §II-B "Position Relative to…"** — this is
  four `\subsubsection` blocks of literature survey. Collapse to **at most two
  short paragraphs** with grouped citations. Keep the one sentence that actually
  positions AAL ("we are not aware of prior work that uses operational command
  authority as the linearization boundary…") and the CoNICE contrast (it's the
  nearest neighbor). Delete the textbook asides (e.g. "the underlying
  single-leader-plus-idempotency-key patterns are textbook…"). Preserve every
  `\cite` key by grouping them; do not orphan references (see constraints).
- **`sections/01_introduction.tex`, ¶2** (the Räddningstjänsten Storgöteborg
  guidance detail: "generally available part… facility-specific part… layered
  information about buildings, adjacent risks, incident risks, and technical
  protection systems"). Compress to two sentences: public Swedish rescue-service
  guidance + the academic corroboration, keep the citations, drop the
  enumeration of plan contents. A systems reviewer gets no signal from the
  plan-structure detail.

### Tier 3 — over-hedged limitations (compress, don't delete the honesty)

- **`sections/07_discussion.tex`, §VI-C Limitations**, the CRDT-comparison
  paragraph. It re-walks the four-vs-six invariant accounting already implied by
  §V-B and §V-E. Compress the invariant walk-through to two sentences: *four of
  the six checked invariants have service-path witnesses in §V-B (name them in a
  clause); the remaining two — SingleAuthority, SingleCommand — are model-only
  because the harness is single-edge.* Keep the throughput unit-boundary
  disclosure, the single-host/Android/mesh scope disclosure, the
  operator-initiated/no-failover disclosure, and the crash-fault-not-Byzantine
  disclosure — those are the honest limits and must stay.
- **`sections/03_architecture.tex`**, the RedBlue framing (two sentences doing
  one job). Trim to one sentence: AAL is a RedBlue-style split with
  authority-bearing decisions in the strong set, citation retained.

### Tier 4 — last resort only (touch only if still >9 after Tier 1–3)

- Thin reference clusters where the compressed related-work prose no longer needs
  every citation in a group (e.g. the shared-log/replication cluster, the
  local-first cluster). **Only** drop a `\cite` if its sentence is gone; never
  leave a `\bibitem` referenced nowhere or a `\cite` to a missing key.
- Cut `fig_promotion_cost` and move its three medians fully into prose.

---

## Do NOT touch

- The §V evaluation narrative spine (V-A→V-F framing, the per-subsection
  "what this tests and why" sentences, and the closing synthesis paragraph). The
  authors are satisfied with it. You may compress the **V-A methodology
  parameter-justification paragraph** lightly if needed, but keep every numeric
  choice and its one-clause rationale.
- Any measurement number. Do not round, re-derive, or "tidy" values. If a number
  appears in prose and in a table, they must stay identical.
- The R1/R2/R3 definitions, the CRDT comparison result, the fenced-promotion
  result, and the four honest limitation disclosures named in Tier 3.
- The macros from `data/promotion_summary.tex` and `data/throughput_summary.tex`
  (`\promotion*`, `\Tput*`). Keep using the macros; don't inline their values.

---

## Constraints

- **No new claims.** Trimming only. You may merge or rephrase sentences for
  density, but you may not introduce a result, comparison, or assertion not
  already supported by the current text and data.
- **Voice:** keep the existing IEEE-conference register — indicative, terse,
  active voice for measurements. Don't make it chatty in the name of
  "experiences." The reframe is about *what* is included, not a tone change.
- **Reference integrity:** after editing, every `\cite` must resolve and every
  `\bibitem` should still be cited at least once (or be deliberately removed in
  Tier 4). Report any orphans.
- **Cross-references:** if you delete a float, remove or redirect every `\ref`/
  `\cref` to it. Zero undefined references in the final build.
- Touch only files under `sections/`, `figures/` (caption/float files), and
  `main.tex` if a float include must be removed. Do not modify `data/`,
  `tables/*.tex` content, or any harness/script.

---

## Deliverables

1. The edited source.
2. **Build confirmation:** baseline page count → final page count, and
   undefined-reference count (must be 0).
3. **Changelog**, per file: what was cut or compressed, and for each cut float
   the page-count delta it produced. Note explicitly which tier you stopped at
   and the final page count.
4. **Reference report:** any `\cite` removed and confirmation no orphaned
   `\bibitem` remains.
5. A one-paragraph note on whether the ≤9-page target was met by Tier 1–2 alone,
   or required Tier 3/4, so the authors know how much margin exists if they later
   add a sentence.
