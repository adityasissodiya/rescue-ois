# "Linearization": where it appears, why it is contested, and what to use instead

Working note for the AAL author team. Prompted by the co-supervisor's objection that
"linearization" should not be used in this context.

Status: **Option A applied to the working tree on 2026-09-30, not yet committed** (see the
next-steps block). Parts 1–6 below are the diagnosis as checked on 2026-09-24, against the
working tree (including the uncommitted 21 Sept edits) and the `build/main.pdf` of that
date; their `file:line` references describe the source before the rename. Section, figure
and table numbers are the PDF's.

**Timing:** WONS 2027 paper registration closes **2 October 2026** and submission
**9 October 2026** (2027.wons-conference.org). Registration normally records the title, so
the name should be settled before 2 October.

<!-- next-steps:start -->
## Next steps (as of 2026-10-04)

WONS 2027 is dropped (decided 2026-10-04). Ulf and Johan rejected the 30 Sept framing: R3
is not met, and "authority" mixed a person's right to command with a node's right to
write. Johan asked that the paper stay frozen until the research problem and the system
model are agreed. The working plan is now `D:/work/aal/AAS_PLAN.md`; meeting notes for
Monday 5 Oct are in `D:/work/aal/meeting-2026-10-05.md`, with Beamer slides in
`D:/work/aal/slides-2026-10-05/slides.pdf`.

The 30 Sept state is committed on `master` (21 Sept baseline `564e789`, rename `3fc8ca8`,
revision `8a9564d`). A reframe draft that follows `AAS_PLAN.md` is on branch
`reframe-aas-plan` (`0e9104c`). It is a working draft that goes beyond the freeze, so don't
send it as a paper. Text that depends on the unagreed model, or on results not yet
measured, is marked `\pending{}`.

1. **Hold the 5 Oct meeting**: agree the use case, research question and system model;
   fill in the Notes, Decisions and Action items in the meeting file. Then bring the
   `reframe-aas-plan` draft into line with what was agreed and resolve the `\pending{}`
   markers that the meeting settles.
2. **Draw the clip book**: storyboard frames 1 to 8 from the meeting notes, iterated with
   the supervisors.
3. **Check succession practice with the rescue service** (questions in `AAS_PLAN.md`
   Phase 1).
<!-- next-steps:end -->

---

## Part 1 — Where "linearization" appears, and where it is explained

21 occurrences on 20 source lines across 12 files (the abstract's one line holds two). The
rendered PDF shows 16 in the body, one of them produced by `\methodname` at
`01_introduction.tex:24`, plus two in the PDF metadata. The first and most important
finding:

> **The term is never defined anywhere in the paper.** There is no sentence that says what
> a linearization point *is*. Five sites say where ours *sits*; the rest either use it as a
> name or assume the reader already holds the definition.

`refs.bib` contains **no Herlihy & Wing entry** and no citation for linearizability. The
paper borrows a formal term of art, never attributes it, and never establishes it.

### 1a. Sites that name the method (7)

These carry the term as a proper noun. No explanation is attempted or expected here.

| File | Line | Text |
|---|---|---|
| `main.tex` | 54 | `\title{Authority-Aligned Linearization: Fenced Command Authority for Vehicle-Edge Networks under Intermittent Connectivity}` |
| `main.tex` | 26 | `pdftitle={Authority-Aligned Linearization: ...}` |
| `main.tex` | 28 | `pdfkeywords={authority-aligned linearization; ...}` |
| `main.tex` | 49 | `\newcommand{\methodname}{authority-aligned linearization}` |
| `main.tex` | 74 | IEEEkeywords: `authority-aligned linearization, intermittent connectivity, ...` |
| `sections/00_abstract.tex` | 1 | "We present Authority-Aligned Linearization (AAL), a design discipline composed from established mechanisms..." |
| `sections/08_conclusion.tex` | 3 | "Authority-aligned linearization rests on an operational fact consensus and CRDT designs do not directly address..." |

### 1b. Sites that gloss *placement* — the closest thing to an explanation (5)

Each of these tells the reader **where** the linearization point is. None tells them **what**
it is. A reader who does not already know Herlihy–Wing learns only that some unexplained
point sits at the command edge.

- **`sections/00_abstract.tex:1`** — "...under a domain rule: the incident-journal
  linearization point sits at whichever vehicle-edge node currently holds externally
  assigned command authority."
- **`sections/01_introduction.tex:24-26`** — "The answer is `\methodname{}` (AAL), a
  consistency discipline that places the incident-journal linearization point at the
  command edge, the vehicle edge node currently holding operational command authority."
- **`sections/02_problem_analysis.tex:55-56`** — "...under a domain rule (the command edge
  is the incident-journal linearization point)."
- **`sections/02_problem_analysis.tex:87-88`** — "`\systemname{}` places the linearization
  point at the command edge precisely so the authoritative order survives backhaul
  partition."
- **`sections/08_conclusion.tex:5-6`** — "The incident-journal linearization point is the
  command edge, the vehicle edge node holding that authority."

This is the crux. **The paper fixes the *location* of a term whose *meaning* it never
supplies.** Where a reader supplies the standard meaning themselves, they get a promise the
paper does not keep (Part 2).

### 1c. Sites that use the term as settled vocabulary (6)

These presuppose the definition that 1b never gave.

- **`sections/03_architecture.tex:25`** — "...immutable artifacts, audit records, and
  command-to-core backhaul use validation or eventual forwarding rather than command-edge
  linearization."
- **`sections/04_synchronization_protocol.tex:11-12`** — "The command edge linearizes
  authority-bearing operations into a totally ordered journal." *(the verb form; note it is
  immediately re-glossed as "totally ordered", which is the weaker and accurate claim)*
- **`sections/06_evaluation.tex:41`** — "Saturation throughput at the linearization point
  bounds what a single writer can absorb."
- **`sections/06_evaluation.tex:56-57`** — "...so at-least-once forwarding is exactly-once
  at the linearization point."
- **`sections/06_evaluation.tex:228-229`** — "It holds: the linearization point absorbs a
  ten-edge fleet without becoming the bottleneck."
- **`tables/tab_evaluation.tex:14`** — Table II, Interpretation column of the direct
  `/accept` row: "linearization point: command accept + journal write only"

In all six, "linearization point" is doing the work of "the single writer" or "the
serialization boundary". Substituting either phrase changes no claim in the paper.

### 1d. Build and artifact plumbing (3)

Not prose, but these emit the wording into Table II and the traceability map.

- `scripts/generate_tables.py:123` — hard-coded string emitted into Table II
- `scripts/generate_traceability.py:68` — row label for claim IV-B
- `TRACEABILITY.md:18` — generated output of the above

The traceability gate resolves each row against the data files, not against the paper's
wording, so it will **not** catch a missed site: a stale label passes the gate and stays.
The final grep in Part 5 is the only check.

### 1e. Outside the paper tree

- **Overleaf.** `overleaf-update/` (21 Sept) is a staging copy of `main.tex` and
  `sections/06_evaluation.tex`, both with the old wording. The Overleaf project itself holds
  every file.
- **Artifact repo.** `rescue-ois/README.md:3` names the paper "Authority-Aligned
  Linearization (AAL)", still as the NCA 2026 paper, and that README is on GitHub
  (`origin/main`). Also `docs/what-fails-without-our-solution.md:1,6`,
  `docs/architecture/sync-protocol.md:4`, and code comments in `scripts/evaluate-pilot.py`
  and `scripts/evaluate-fleet-scaling.py`.
- **Leave as record:** `paper-snapshots/`, `tools/`, and the planning notes.

---

## Part 2 — What the paper actually establishes

Judge any replacement against this list, not against the title.

**Established:**

1. A single writer assigns a total order on the incident journal, atomically with insertion
   (§III-B, Fig. 1).
2. That writer is pinned by *externally designated* authority, not by reachability or quorum
   (§III-D).
3. Authority transfer does not fork the journal (invariant `NoForkedJournal`, model-checked
   for the promotion rule described at the end of this part).
4. Duplicate submissions fold onto existing entries (`LocalIdempotency`).

**Where the paper departs from linearizability.** The claim is scoped: "The command edge
linearizes *authority-bearing* operations" (`04_synchronization_protocol.tex:11`). The
departures that count are the ones inside that scope.

*Inside the claimed scope:*

1. **Two acceptors during transfer.** `04_synchronization_protocol.tex:79-85` — an isolated
   former command "fences *itself*" when its lease lapses, "bounding the window in which two
   edges can both believe they hold authority." Bounded is not zero, and the prototype makes
   the window concrete: promotion does not wait for the old lease
   (`rescue-ois/scripts/promote-responder.sh:22-26`: "it cannot detect whether the previous
   command is alive"), and the default lease is 90 s (`rescue-ois/edge/syncd/src/config.py:40`). For up
   to one lease window both edges accept authority-bearing writes; the stale edge's writes
   from that window are refused at the journal boundary when it reconnects.
2. **Stale reads away from the command edge.** R1 has every tier keep working "from
   previously synchronized data" (`02_problem_analysis.tex:28-29`), and consumers replay the
   journal in `event_seq` order (Fig. 1 caption). Linearizability constrains reads as well
   as writes, so it can hold at most for operations served by the command edge itself. That
   shrinks the claim to "one node applies its own writes atomically", which is true of any
   single-writer store.

*Outside the claimed scope (the M3 responder path, non-authority data by §III-C):*

3. **Acknowledgement precedes ordering.** `04_synchronization_protocol.tex:32-34` — "a
   responder may acknowledge local acceptance after the outbox insert, but marks an item
   forwarded only after incident-journal acceptance or duplicate recognition."
4. **No cross-responder order before assignment.** `04_synchronization_protocol.tex:50-52`
   — "there is no claim of causal ordering across independent responder outboxes before
   command assignment."

Points 3 and 4 show that the end-to-end submission path is not linearizable: the journal
orders submissions by arrival, not by when their local acknowledgements returned. But a
defender can answer "we never claimed it for M3", so do not lead with them. (The 23 Sept
draft said point 4 "alone rules it out" because linearizability implies causal consistency.
That over-reaches: causal consistency imposes no order on independent events, so disclaiming
one is not itself a violation. What fails is real-time order relative to the local
acknowledgement, which is point 3.)

**The category point, which needs no claim about the system at all.** In the Herlihy–Wing
sense a linearization point is an *instant* inside an operation's invocation–response
interval. The paper uses it as a *place*: a node that "sits" at the command edge, has a
"saturation throughput", and "absorbs a ten-edge fleet". Systems papers do sometimes use the
phrase loosely for "the node where operations are ordered", so this is a register mismatch
rather than an outright error. It is still the first thing a formally trained reader
notices, and it holds however the consistency question is settled.

**The formal model corroborates less than it appears to.** The six TLA+ invariants named in
§V-A are `SingleAuthority`, `SingleCommand`, `EpochAuthorityCoupling`, `NoForkedJournal`,
`DurabilityAcrossPromotion`, `LocalIdempotency`: state predicates about authority and
journal shape. None is a linearizability property, which would need a refinement mapping to
an atomic-journal specification. And the model has no lease: `PromoteStrict` is enabled only
when every current command is reachable from the candidate, and it demotes that command
atomically (`rescue-ois/formal/tla/RescueOIS.tla:149`). The 38.56M states establish
authority and fork-freedom for reachable-incumbent promotion. The isolated-incumbent case in
point 1 is outside the model.

---

## Part 3 — Why the objection holds

Three independent readings of the objection. All three point the same way.

**(a) The formal-property reading.** The title names a consistency model the paper never
defines, never cites, and never proves, while §III-D discloses a bounded window in which two
edges accept authority-bearing writes, inside the very scope the claim covers. A
distributed-systems reviewer opens on the title, looks for the linearizability argument, and
finds §V-A's non-claims instead. The paper's candour — which is real; the non-claims section
is unusually honest — then reads as a retreat from a promise the title made on its behalf.

**(b) The oversell reading.** §I:31-33 states plainly: "`\systemname{}` is a newly named
design discipline, not a newly invented primitive." Naming that discipline after a
consistency model works against the sentence. It invites the reviewer question the paper has
already pre-emptively answered no to.

This has already happened once. At NCA 2026, Review 2 took AAL for prior art: "Since AAL is
presented as an established methodology, the proposed contribution appears ... to consist
primarily of applying an existing approach", and it asked for "a more precise comparison with
previous applications of AAL" (`reviews.txt:51,62`). It rated innovation "Not innovative"
(`reviews.txt:46`). `reviewer-comment-to-paper-map.md:103` already diagnosed this as a
clarity failure. The WONS plan then kept the name as an "established brand from the NCA
submission, reviewers already engaged with it" (`WONS_2027_ACTION_PLAN.md:604`), but the one
reviewer on record who engaged with the name read it as an existing technique. The
introduction still calls AAL "a consistency discipline" (`01_introduction.tex:24`), the NCA
phrasing, right beside "linearization".

**(c) The ambiguity reading.** In a Cyber-Physical Systems group, and for any reader with a
control background, "linearization" first means local linear approximation of a nonlinear
system around an operating point. "Authority-Aligned Linearization" parses as control
theory before it parses as distributed systems.

**The paper already prefers a different word.** Its own vocabulary, unprompted:

- §III-B is titled **"Incident Journal Sequencing"**
- Fig. 1 caption: "producing a **totally ordered** log"
- §IV-B heading: "Authority boundary and journal **sequencing**"
- §IV-F2 (`06_evaluation.tex:226`): "a single-writer **serializer**"
- §IV-F2 (`06_evaluation.tex:233`): "**serializer** capacity"
- Table II row group: "Command journal **serialization**"
- §II-B (`02_problem_analysis.tex:81-83`): "No server can **serialize** writes it cannot
  reach", so decisions "must **serialize** at the incident"
- §III-D (`04_synchronization_protocol.tex:64-69`): core issuance "makes promotion
  **serializable**"; the core insert "**serializes** concurrent attempts"

"Linearization" is the outlier: the paper's one prominent consistency-model term, and one it
cannot back. Eight nearby sites already use accurate words. One of them repeats the problem
on a small scale: "serializable" (`04_synchronization_protocol.tex:65`) is a
transaction-isolation term, used loosely there to mean "given a single order by core".

---

## Part 4 — Alternatives

### Option A — Authority-Aligned **Sequencing** (AAS) *(recommended)*

> **Title:** Authority-Aligned Sequencing: Fenced Command Authority for Vehicle-Edge Networks
> under Intermittent Connectivity
>
> **Abstract:** "...under a domain rule: the incident-journal **sequencing point** sits at
> whichever vehicle-edge node currently holds externally assigned command authority."

- **For:** Already the paper's own word for this exact mechanism (§III-B title, §IV-B
  heading, Fig. 1 caption). "Sequencer" is established distributed-systems vocabulary for the
  component that assigns a total order, and `balakrishnan2013tango` is **already cited**
  (`02_problem_analysis.tex:62,124`), so the lineage is covered without adding a reference.
  Claims precisely what §III-B delivers and nothing more. Nothing for a reviewer to demand
  you prove. The evaluation sentences read naturally: "saturation throughput at the
  sequencer", "exactly-once at the sequencer", "the sequencer absorbs a ten-edge fleet".
  Optional, at the cost of one reference: the total-order-broadcast taxonomy of Défago,
  Schiper and Urbán (ACM Computing Surveys, 2004) separates *fixed* from *moving* sequencers.
  AAL's sequencer is fixed within a tenure and moves only by fenced, operator-confirmed
  promotion, which is a one-sentence positioning a reviewer can check.
- **Against:** Acronym changes, and "AAL" also appears as literal text at seven sites
  (Part 5). "Sequencing" is mildly overloaded in a public-safety context (call sequencing,
  dispatch sequencing), though the adjacent nouns disambiguate.

### Option B — Authority-Aligned **Serialization** (AAS)

> "...the incident-journal **serialization point** sits at whichever vehicle-edge node..."

- **For:** Closest to existing prose (`serializer`, `serializes`, "Command journal
  serialization"). Minimal vocabulary churn in §II, §III-D and §IV.
- **Against:** Trades one loaded term for another. "Serializability" is a formal
  transaction-isolation property (ANSI / Papadimitriou); a database-side reader can ask the
  same question the co-supervisor just asked. Also collides with serialization-as-marshalling.
  And the design already has a second serialization point: core's epoch insert "serializes
  concurrent attempts" (`04_synchronization_protocol.tex:69`), which the artifact calls "the
  serialization point" (`rescue-ois/scripts/promote-responder.sh:10`). **This option risks
  re-running the present conversation with a different reviewer.**

### Option C — Authority-Aligned **Ordering** (AAO)

> "...the incident-journal **ordering point** sits at whichever vehicle-edge node..."

- **For:** Zero formal baggage. Promises a total order, which is exactly and only what is
  delivered. Unambiguous to control-theory, database, and rescue-service readers alike. The
  safest option if the objection turns out to be (c).
- **Against:** Generic. Weak hook for a WONS title; "Authority-Aligned Ordering" does not
  signal a mechanism the way "Sequencing" does.

### Option D — Authority-Aligned **Logging** (AAL) *(acronym-preserving)*

> "...the incident-journal **append point** sits at whichever vehicle-edge node..."

- **For:** **Keeps AAL.** No change to `\systemname`, to the 18 rendered "AAL"s, or to how
  the four of you already refer to the work in conversation and to funders. The incident
  journal *is* an append-only log, so the noun is accurate. Cheapest possible change: one
  `\newcommand`, one title line, and the prose sites. (The repo directory name spells out
  "Linearization", so it goes stale under every option, D included. The artifact URL,
  `github.com/adityasissodiya/rescue-ois`, contains neither word and is unaffected by all of
  them.)
- **Against:** "Logging" reads as observability / syslog / printf to many systems readers
  before it reads as replicated log. Weaker than "Sequencing" at signalling that ordering is
  the contribution. Worth taking only if preserving AAL is a hard constraint.

### Option E — Keep "Linearization", cite it and scope it

Add Herlihy & Wing to `refs.bib`, define the term at first use, and state the scope explicitly
in §III-B. The scope sentence has to cover the transfer window as well as the responder path,
because the window sits inside the command journal's own scope:

> "We use *linearization* in the sense of Herlihy and Wing [X], for authority-bearing
> operations served by the command edge within one command tenure. Responder submissions are
> acknowledged before journal assignment and are not linearizable, and across a transfer the
> authority lease admits a bounded interval in which two edges may both accept writes."

- **For:** Keeps the title, the acronym, and the submitted framing. Turns a latent weakness
  into a disclosed one, consistent with how §V-A already handles non-claims.
- **Against:** Costs roughly five lines in a paper that has already cut three floats to reach
  its 8-page limit. Concedes the point in prose while keeping it in the title: the awkward
  position of advertising a property and then immediately bounding it away, twice. And it
  does not answer reading (b) or (c) at all.

### Comparison

| | Accurate to §III | Keeps AAL | Reviewer-proof | Title strength | Cost |
|---|---|---|---|---|---|
| **A. Sequencing** | yes | no | yes | good | ~27 edits |
| **B. Serialization** | yes | no | **no** | good | ~27 edits |
| **C. Ordering** | yes | no | yes | weak | ~27 edits |
| **D. Logging** | yes | **yes** | yes | weak–medium | ~19 edits, no acronym churn |
| **E. Keep + scope** | after a two-part caveat | **yes** | partly | unchanged | ~5 lines + 1 ref, at the page limit |

The edit counts are 19 hand edits for "linearization" (the two generated files are
regenerated, not edited) plus 8 for the acronym under A–C. The title itself is not a layout
risk for any option: a scratch build with each of the five title words gives the same
three-line title block and 8 pages.

**Recommendation: Option A**, falling back to **Option D** if AAL must survive for external
reasons (funder reporting, artifact DOI, an abstract already circulated). The NCA review
(Part 3b) is the strongest single argument for moving: a reviewer has already read the name
as prior art once.

---

## Part 5 — Change surface, for whichever option is chosen

All sites, in the order a single pass would touch them. Sites in 1b and 1c need a
sentence-level read, not a blind substitution: §III-B's "linearizes ... into a totally
ordered journal" (`04_synchronization_protocol.tex:11`) becomes redundant under Options A–C
and should be rewritten, not swapped.

```
main.tex:26,28,49,54,74        title, pdftitle, both keyword lists, \methodname
main.tex:48                    \systemname                                (A-C)
sections/00_abstract.tex:1     x2 - the name, and the placement gloss
                               + "(AAL)" and "We specify AAL"             (A-C)
sections/01_introduction.tex:25                (line 24 follows \methodname)
sections/01_introduction.tex:24,26             "(AAL)", "verify AAL"     (A-C)
sections/02_problem_analysis.tex:56,87
sections/03_architecture.tex:25
sections/04_synchronization_protocol.tex:11    *rewrite, do not substitute*
sections/06_evaluation.tex:41,57,228
sections/06_evaluation.tex:172                 Table III header "AAL result" (A-C)
sections/08_conclusion.tex:3,5
sections/08_conclusion.tex:17                  "whereas AAL"              (A-C)
scripts/generate_tables.py:123                 hard-coded Table II string
scripts/generate_tables.py:235                 Table III "AAL keeps ..."  (A-C)
tables/tab_evaluation.tex:14                   regenerate, do not hand-edit
tables/tab_crdt_comparison.tex:6               regenerate, do not hand-edit (A-C)
scripts/generate_traceability.py:68            claim IV-B row label
TRACEABILITY.md:18                             regenerate, do not hand-edit
```

Worth a look in the same pass: `01_introduction.tex:24` calls AAL "a consistency discipline"
where the abstract says "design discipline", and `04_synchronization_protocol.tex:65` says
"makes promotion serializable" (Part 3). `figures/fig_linearization_boundary.pdf` is no
longer included and can be ignored.

Outside the paper tree (1e): push every touched file to Overleaf, not only the ones in
`overleaf-update/`, and update `rescue-ois/README.md` and the two docs files when the WONS
artifact is prepared.

Before the pass, commit the pending 21 Sept work (11 paths, including `main.tex` and
`06_evaluation.tex`, are modified or untracked), so the rename lands as one revertible
commit. After it: regenerate the tables and `TRACEABILITY.md`, rebuild, and grep both the
source and the rendered PDF (`pdftotext build/main.pdf - | rg -i lineariz`), because the
traceability gate will not catch a missed site.

---

## Part 6 — What to confirm with the co-supervisor first

Reading (a) is inferred from the text; the co-supervisor may have meant (b) or (c). It
changes the ranking:

- If **(a), the formal-property objection** — A, C and D all resolve it. E is defensible only
  with the two-part scope sentence, which is costly. B does not fully resolve it.
- If **(b), the oversell objection** — A, C and D resolve it. B partly. E does not. The NCA
  review is direct evidence for this reading.
- If **(c), the control-theory ambiguity** — any of A–D resolve it equally; pick on other
  grounds. E does not resolve it at all.

Also worth settling before the edit: whether the objection is to the **title** specifically or
to the **word anywhere in the paper**, and whether **AAL** is load-bearing outside the paper.
The second is partly answered: AAL has gone out in the NCA 2026 submission (where it was
misread) and in the `rescue-ois` README on GitHub, and neither binds the WONS paper. Still
unknown: funder deliverables (IndTech, COP-PILOT, RemaNet) and any circulated abstract. If
AAL appears in one of those, Option D moves to the top.

**Johan's reply (24 Sept).** Linearization for commander orders and eventual consistency for
observations is fine, as long as the two are not combined on the same data model; combining
them would be "an impossible problem", and the paper "can still get accepted, but cause
problems later at the PhD defense". Johan also asks why an order needs linearization at all,
suggests that teams get an acknowledgement that all other teams received an order (2PC/3PC),
and will send fuller feedback after rereading the paper.

This is reading (a) with a concrete test, plus the contribution question. Both point to
Option A. What the design gives the commander's decisions is one authoritative order that
does not fork across handover, and copies away from the command edge (such as the core's)
see only a prefix of it. That is sequencing, not linearizability, and each journal entry
has exactly one contract, so the rename also answers the "same data model" test.

The acknowledgement question exposes a scope gap. Neither the paper nor the prototype has a
path that delivers the commander's decisions to responder vehicles: the six flows in
`rescue-ois/docs/architecture/sync-protocol.md` all run toward the commander or down from
core, and the incident-state read in `edge/ops-api/src/incident.py` is a command-only stub.
The paper should either state that the journal records decisions and delivery is out of
scope, or name delivery as future work. Any delivery acknowledgement has to be
non-blocking, or orders would stall whenever a team is out of coverage (R1).

---

*Revised 2026-09-24.* Section, figure and line references corrected to the current PDF and
source. Part 2 re-scoped: the M3 points moved outside the claim, and the transfer window and
model coverage made precise. Change surface extended with the acronym sites, Overleaf and
the artifact repo. The title-length claim replaced by a test build. NCA review evidence and
the registration deadline added. Johan's 24 Sept reply and the order-delivery gap recorded in
Part 6.
