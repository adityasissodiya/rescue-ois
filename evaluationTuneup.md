# Codex task: tie §V (Evaluation) into one coherent argument

You are operating inside the AAL prototype + paper repository, on the
`nca2026-submission` working tree. The numerical fixes and re-runs are already
done: the WAN partition is now a surgical command↔core cut, throughput is split
into a direct linearization-point number and an end-to-end number, an outbox
crash-restart durability cell exists, the CRDT partition row is relabeled, and a
batch of prose/doc corrections has been applied. The paper builds clean
(10 pages, 0 undefined refs).

Your job is **not** to re-measure or re-audit. It is to make §V read as a single
argument instead of six disconnected measurement cells, and to guarantee the
prose, the generated tables, the JSONL, and the §VI disclosures all agree on the
same numbers and the same story.

---

## The thesis §V must prove

> **The evaluation traces the contract AAL makes, cell by cell, across the
> authority-bearing path and the non-authority path — and shows that the obvious
> mergeability-based alternative cannot encode the authority that contract
> requires.**

Every subsection must visibly serve this thesis. Each subsection opens by stating
which part of the contract it tests and why that test is well-defined, then
reports the measurement. No subsection may read as a free-standing number dump.

The cell ordering and what each cell is *for*:

- **V-A** — frames the five properties §V establishes and the methodology
  (this is the spine; it must precede the existing methodology paragraph).
- **V-B** — the safety boundary (single-writer across command transitions) holds,
  and enforcing it is cheap on both the commit and the stale-rejection path. M1/M2/M4.
- **V-C** — authority-bearing writes commit independent of responder reachability;
  the linearization-point serializer is characterized in isolation. M1/M2.
- **V-D** — the non-authority path (outbox, idempotent forwarding, crash-restart
  durability) survives realistic link impairment and process restart. M3 / R2.
- **V-E** — a Hanssen-style CRDT-LWW baseline preserves availability but cannot
  satisfy R3, on the same workload shape. Contrast.
- **V-F** — command-to-core backhaul recovers within seconds of WAN heal; this is
  a support-path property, not an authority property.

---

## Ground-truth rule (read before touching prose)

The regenerated tables under `paper/tables/` and the JSONL under `paper/data/`
are ground truth. The numbers quoted in this document are the values the human
reported after the re-runs and may contain transcription error. **For every
number you write into prose, read it from the generated `.tex` table or the JSONL
and use that value.** If a number in this document disagrees with the repo,
trust the repo and add a line to the changelog noting the discrepancy. Do not
silently reconcile.

Canonical post-re-run values to expect (verify each against the repo):

| Cell | Quantity | Expected value |
|---|---|---|
| V-C | command-local commit during responder isolation | 20/20 commits, contiguous seq, **median 5.8 ms, p95 7.3 ms**, n=20 |
| V-C | direct linearization-point throughput (`/accept/event-batch`) | **≈356 events/s**, n=29 after warm-up |
| V-D | end-to-end submission throughput (responder→outbox→journal) | **≈159 events/s**, n=29 after warm-up |
| V-D | outbox crash-restart durability (new cell) | **50 events survive a Postgres power-cycle, 0 duplicates, contiguous seq, recovery ≈2.6 s** |
| V-F | command-to-core WAN recovery, partitions 1/10/60 s | **≈0.75 / 0.91 / 0.23 s, p95 ≈1 s; monotone, no non-monotonic artifact** |
| V-B | promotion phase cost A/B/C | unchanged: median 6.3 / 2.5 / 5.7 ms |
| V-D | propagation floor / qd100 | unchanged: ≈947 ms at qd≤10, ≈1.22 s at qd100 |

Two caveats the human flagged:
- The V-C latency rising from 2.8 to **5.8 ms** is the honest current number
  (host was under load during back-to-back runs). It is still single-digit ms.
  **Do not "correct" it back toward 2.8.** The claim it supports is "single-digit
  millisecond commit, independent of responder reachability" — that holds.
- `/accept/event-batch` now requires an `X-Command-Epoch` header. If you describe
  the accept path in §V-C or the protocol text, reflect that the header is
  mandatory and that stale/absent epochs are rejected before journal work.

---

## Integration instructions, per section

For each block below: integrate the target prose into the named section file,
adapting wording to match the surrounding text and the verified repo numbers.
Where the section already contains a measurement paragraph, prepend the framing
sentence(s) and keep the existing measurement, fixing only stale numbers.

### V-A — ensure the five-property spine precedes the methodology paragraph

A methodology paragraph with parameter justifications already exists. Add the
spine *before* it (do not duplicate the parameter rationales):

> The evaluation establishes five properties of AAL, in order. First, that the
> single-writer boundary over the incident journal holds across command
> transitions and is cheap to enforce (§V-B). Second, that authority-bearing
> writes commit independently of responder reachability (§V-C). Third, that the
> non-authority path — durable outbox, idempotent forwarding, and crash-restart
> durability — survives mesh-grade impairment and process restart (§V-D). Fourth,
> that a mergeability-based CRDT-LWW baseline preserves availability but cannot
> satisfy R3, on the same workload shape (§V-E). Fifth, that backhaul to the
> regional core recovers within seconds of WAN heal, as a support-path property
> rather than an authority property (§V-F). The first three cells exercise the
> mechanisms M1–M4 of §IV directly; the last two probe the boundary of what AAL
> does not promise.

Then confirm the methodology paragraph states: n=30 default, the queue-depth
ladder (1/10/100) and partition ladder (1/10/60 s) with their rationales, the
netem profiles with their citations, and the single-host topology (one core, one
command edge, **three responder edges** — the stack now runs RESPONDERS=3, so the
prose must say three, not one). Fix the responder count if it still says one.

### V-B — give the cell a reason to exist

Prepend:

> Fenced promotion is the only mechanism in AAL that can split authority if it
> fails, so it is measured first. The model side and the service-path side answer
> different questions: the TLA+ and Hypothesis models establish the safety
> invariants over a bounded state space, while the service-path measurement shows
> stale-epoch traffic is rejected before any incident-journal work and that the
> rejection latency is bounded.

Keep the existing phase-cost numbers, the falsification-cost table, and the
"five live service-path runs" paragraph unchanged.

### V-C — frame, then split the two throughput numbers

Opening framing:

> V-B established that the safety boundary holds across transitions at single-digit
> millisecond protocol cost. The next question is whether the boundary holds during
> ordinary operation: whether an authority-bearing write commits while a responder
> is unreachable. If responder isolation can delay the journal, R3 reduces to a
> connectivity assumption rather than a protocol property.

First measurement paragraph (responder isolation, with verified numbers):

> With one responder isolated for ten seconds, twenty single-event POSTs to the
> command-edge `/accept/event-batch` endpoint commit 20/20 (HTTP 200), the assigned
> `event_seq` values are contiguous with no duplicates, and per-attempt latency has
> median 5.8 ms and p95 7.3 ms (n=20). The endpoint requires a current
> `X-Command-Epoch`; stale or absent epochs are rejected before journal work.
> Nothing about responder reachability participates in the commit.

Second measurement paragraph (replace the old 1000-concurrent paragraph):

> Saturation throughput at the linearization point — direct concurrent POSTs to
> `/accept/event-batch` — is ≈356 events/s (n=29 after warm-up exclusion). This
> characterizes the prototype serializer in isolation; same-incident writes are
> linearized through `SELECT … FOR UPDATE` over an asyncpg pool capped at eight
> connections. End-to-end submission throughput, which traverses the responder
> ops-api, outbox, and forwarding path, is reported separately in §V-D and is the
> relevant number for delivered M3 throughput.

### V-D — frame, explain the floor, add the crash-restart cell, move the e2e number here

Opening framing:

> V-B and V-C exercise the authority-bearing path. The remaining M3 responsibility
> is that responder submissions reach the journal durably, without duplication
> under retry, and within bounded time under link conditions characteristic of mesh
> deployment — and that they survive process restart.

Replace the propagation sentence with the explained version:

> Propagation latency is approximately constant at queue depth ≤10 (≈947 ms) and
> rises to 1.22 s at queue depth 100. The floor reflects the responder push loop,
> which polls the outbox at 250 ms with a four-poll backoff on empty results, so a
> freshly inserted row waits up to one polling cycle. The rise at qd=100 follows
> from the BATCH_SIZE=50 contract: 100 events require two batches separated by the
> 250 ms post-success sleep, adding ≈250 ms over the qd-10 baseline.

Duplicate-replay sentence (fix the wording):

> The duplicate-replay scenario issues 50 unique `client_event_id` values and
> replays each five times; across n=30 runs the journal contains exactly 50 rows.
> Forwarding is at-least-once and deduplicated at the journal, so submission is
> effectively exactly-once at the linearization point.

**New paragraph — crash-restart durability (this closes R2's boundary):**

> Durability across process restart is tested directly. Fifty submissions are
> accepted into the responder outbox, the responder Postgres is power-cycled before
> any forwarding, and the stack is allowed to recover. All 50 events survive the
> restart, forward with no duplicates and contiguous `event_seq`, and the journal
> reaches consistency ≈2.6 s after recovery. This is the runtime witness for R2:
> the outbox is durable, not merely in-flight.

E2e throughput paragraph (moved from V-C):

> End-to-end submission throughput from the responder ops-api to a journal commit
> is ≈159 events/s (n=29 after warm-up). This includes durable outbox insert, push
> batching, polling, and the M1/M2 commit path, and is the relevant figure for
> delivered M3 throughput under continuous load. It and the ≈356 events/s
> linearization-point figure of §V-C measure different things and are read
> separately.

### V-E — frame, then disclose the asymmetry as part of the argument

Opening framing:

> V-D shows the non-authority path holds under impairment and restart. V-E asks the
> inverse: if the linearization boundary were removed and all incident data were
> treated as mergeable, would the result satisfy R3? The comparison runs on the same
> queue-depth and netem workload shape, on the executable service path where it is
> well-defined.

Comparability paragraph (place before the table or fold into §VI, consistent with
how the human chose to disclose it):

> The comparison is well-defined on field-edit propagation, no-partition write
> acceptance, and the application-level conflicts CRDT-LWW produces. It is not
> symmetric on infrastructure. The CRDT baseline runs in memory, has no background
> anti-entropy, and converges only through harness-triggered `full_sync()` calls;
> the relabeled convergence row therefore reports post-quiescence convergence after
> a forced anti-entropy round, not an injected network partition. AAL carries a
> durable Postgres outbox in the critical path. Every asymmetry favors the CRDT
> baseline on the metrics where it leads. We keep them: the point is not which
> design has the better infrastructure, but whether mergeable-by-default semantics,
> given every benefit of the doubt, can encode authority. The concurrent-edit and
> delete-resurrection rows show they cannot.

### V-F — delete the old artifact hedge, write the clean result

**Remove entirely** any sentence attributing the recovery shape to an
"asyncpg-timer artefact" or "implementation bound, not a recovery law," and the
matching explanation in the figure caption. That non-monotonicity is gone.

Opening framing + result:

> V-B through V-E concern paths where the system must make a correctness choice.
> V-F concerns one where it does not: command-to-core forwarding is eventually
> consistent backhaul, and the only question is recovery time after the WAN link
> returns. The partition is a surgical `tc` cut of the command↔core path only; the
> command edge retains its local Postgres and its responder reachability throughout,
> so the measurement isolates backhaul flush time. For partitions of 1, 10, and 60 s
> the median recovery is ≈0.75, 0.91, and 0.23 s respectively (p95 ≈1 s). The shape
> is monotone within noise; because the command edge never loses its own database,
> recovery is bounded by the size of the backlog to flush, not by a connection
> timeout.

Rewrite the two figure captions (`fig_partition_timeline`, `fig_recovery`) to
match: surgical command↔core cut, command keeps DB and responders, no artifact
language.

### §V closing — add one synthesis paragraph (end of §V)

> Read together, the cells trace the contract AAL makes. V-B shows the boundary
> holds across operator-driven transitions and is cheap to enforce. V-C shows an
> unreachable responder cannot delay the journal. V-D shows responder submissions
> cross the boundary durably, idempotently, and across process restart. V-E shows
> that removing the boundary in favor of mergeability fails to encode the authority
> R3 requires. V-F shows the support path recovers within a second. The cost of the
> contract — no automatic failover, lower write availability for authority-bearing
> operations during partition — is concentrated where §IV claimed it would be: at
> command transitions, on the operator.

### §VI — make the limitations consistent with what §V now discloses

- Confirm the four-vs-six invariant-witness sentence is present (SingleAuthority
  and SingleCommand are model-only; the other four have service-path witnesses).
- The §VI limitations paragraph must now point at the **specific** asymmetry §V-E
  discloses: the CRDT baseline has no background gossip, so its convergence is
  harness-triggered and the partition row is post-quiescence, not an injected
  partition. State that this favors the baseline and is retained deliberately.
- Confirm the throughput unit-boundary disclosure now references both the ≈356
  linearization-point number and the ≈159 end-to-end number rather than the old
  single 156.7 figure.

---

## Cross-cutting consistency checks (run these and report results)

1. Every number in §V prose matches the value in the generating `paper/tables/*.tex`
   or `paper/data/*.jsonl`. List any mismatch; do not auto-fix prose to a number
   that isn't in the repo.
2. No occurrence of "Cairn" remains anywhere in `sections/` or `main.tex`.
3. No "exactly-once" remains except the qualified "effectively exactly-once at the
   [journal | linearization point]" phrasing in §V-D.
4. No "asyncpg-timer artefact" / non-monotonic-artifact language remains in §V-F or
   its figure captions.
5. §V-C reports median/p95 (5.8/7.3 ms), not median/max, and the two throughput
   numbers (356 direct, 159 e2e) appear in the correct subsections.
6. Section cross-references (`\S\ref`, `\cref`) resolve — no undefined references.
7. The intro's closing roadmap sentence lists the real sections (no leftover
   "\S II … \S V" enumeration, no Cairn).

---

## Hard constraints

- Do not invent measurements or reintroduce numbers that aren't in the regenerated
  repo artifacts.
- Do not soften or re-hedge the V-F result — the artifact explanation is gone for a
  reason.
- Match the existing IEEE-conference voice: indicative mood, short declarative
  sentences, measurement reported in active voice ("commits 20/20", "rejects stale
  traffic"), setup in passive. No "we believe", no "great", no marketing adjectives.
- Touch only `sections/`, the two `figures/fig_*recovery*` and `*partition_timeline*`
  caption files, and `sections/07_discussion.tex` (§VI). Do not regenerate tables or
  re-run harnesses — the data is fixed.
- After editing, rebuild the paper and confirm it still compiles to a clean PDF with
  zero undefined references and report the page count.

## Deliverables

1. The edited section files.
2. A short changelog: per section, what framing/transition was added and which stale
   numbers were corrected (with old → new and the repo source for the new value).
3. The output of the seven consistency checks above, each PASS/FAIL with evidence.
4. Build confirmation: page count and undefined-reference count.
