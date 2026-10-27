# What the testbed says about the paper

This memo interprets `results/REPORT.md` for the journal version of the AAS paper. Each
finding gives the evidence (a REPORT section, or a command that replays it), says what
it changes in the paper or the model document, and is marked:

- **[model]**: a property of the executable model under its stated assumptions,
  reproducible from a seed. It is not a field measurement.
- **[inference]**: my reading of what a result means for the paper.
- **[open]**: speculation, or a question the testbed cannot answer.

Section and table numbers refer to the WONS draft (tag `wons-draft`) and to the model
document (`../paper/model/`), which is what this memo was written against. The TCPS
manuscript (`../paper/`) is built on these findings; `../paper/TCPS_PLAN.md` says which
it adopts and which decisions are still open.

Robust results are structural: which cells are zero and which are not, counterexamples,
and invariants. Magnitudes (seconds of takeover delay and the like) follow from
parameters I chose (README, "Defaults"); treat them as orders of magnitude.

## 1. The direction, in one paragraph

**[inference]** The draft's centre of gravity, the (a)/(b)/(c) trade-off, is the weakest
part for a journal. Under any operational definition it holds by construction: if A
records throughout the outage and B records at some point in it, both record at that
point. The testbed checks it in every run and it cannot fail. Reviewers will read it as
CAP restated for one register. Keep it as one paragraph of framing, and do not spend TLA+
effort on "model-checking the trade-off per policy" (the open question in section II-C):
argue it. What the testbed shows to be non-trivial, and largely unaddressed in the draft,
is **finality** (when a command decision can no longer change status) and **device-local
enforcement** (when a device must stop on its own). Both have counterexamples against
the current model, both have fixes that the testbed validates, and together they answer
the paper's second question ("which rules need consensus?") more sharply than "none".
The policy cost map then becomes the evaluation, not the contribution.

## 2. Findings, most consequential first

### F1. S4's "one device at a time" fails on multi-hop links; an acknowledged T' fixes it

- **[model]** The model document argues that A (stopping after T' without hearing B) and
  B (activating after T without hearing A) "measure the same silence". On intermittent
  multi-hop links they do not: a relay can hand A an old heartbeat of B's, sent before
  B's activation, without the activation. A's T' timer restarts and A records beside B.
  Deterministic witness: `python -m aas_testbed run --policy S4 --relay-fault`. A stops
  at 840 s, B activates at 900.5 s, A starts again at 932 s and records beside B until
  1,040 s. Over 10 seeds the median is 106 s of overlap, with residual orders that crews
  see become residual (REPORT §9). In the random search, S4 overlaps in 8 of 60
  runs that have T − T' ≥ 5 s and no handover (H16).
- **[model]** Fix: A's timer runs from the last of **A's own** heartbeats that B is
  known to have received (B's heartbeats carry what B has heard), not from the last time
  A heard B. That is the textbook lease renewed by acknowledgment. With it, H16' holds in
  every run, the relay witness shows 0 s of overlap, and in the margin sweep (REPORT §6)
  T − T' ≥ 1 s suffices for every heartbeat period and ε tested. Without it, a 5 s
  heartbeat needs a margin of 8 to 16 s, and no margin is safe under relaying.
- **[inference]** Why: if x is A's latest heartbeat known to B and y the latest B holds,
  then x ≤ y. A stops at x + T' and B activates at y + T, each measured on its own clock,
  so the gap is at least (T − T') − ε. Delay and heartbeat period drop out. This is a
  short proof the paper can carry, and a property worth model-checking.
- **Changes:** the document's condition "T − T' exceeds the message delay plus ε" is wrong
  in both directions. Table II's S4 (c) entry must name the acknowledged timeout. The
  same applies to S2's lease (1 overlapping search run without acknowledgment, 0 with).

### F2. Settlement is safe, but not live, and the kind of succession act decides which

- **[model]** Safety: across the random search, 2,200 incidents, no device ever revoked
  an authoritative verdict, under both settlement rules (REPORT §10). Per-person sequence
  numbers carried in heartbeats are enough of a completeness proof.
- **[model]** Liveness fails as the document states the rule. Read literally (every
  person named in any authority record must be complete up to the decision), a commander
  whose device is lost blocks settlement of every later decision, forever: 24 to 30
  never-settled decisions per run (REPORT §8, `strict`, device lost).
- **[model]** The refinement `closing` (an unconditional act by the appointing authority
  closes the predecessor's chain) settles everything under S1 and S3 within about 7 s.
  It cannot help S4: an activation is conditional on A having been the holder, which only
  A's records can show. S4 decisions stay provisional until A's device returns (p95
  747 s with the device kept), or forever if it is lost (24 never settled).
- **[inference]** This is the answer to "which rules need consensus between devices?":
  none, for safety. For finality you need either the predecessor's records or an act by
  the appointing authority. Pre-authorized succession (S4) therefore needs a ratifying act
  by C (a takeover appointing B) to settle the deputy's tenure, at least from the
  ratification on. The draft does not say this, and it is a clean, defensible result.
- **Changes:** model document section 7 ("The rules of the journal"): adopt `closing`;
  add ratification under S4; state that the server's confirmation is safe but its
  progress depends on who can still sign.

### F3. A takeover that cannot reach the scene rewrites the past; make it take effect on acceptance

- **[model]** Under S3 in P-B or P-C, with A fit but not answering C, C signs a takeover
  at the centre that cannot reach the scene. A keeps commanding over the mesh, and crews
  see A's orders as valid. At heal the takeover arrives with its earlier timestamp, and
  every order A gave since becomes residual after the fact: 17 residual orders, each of
  which all three crew devices had shown as valid (51 flips, counted per crew device;
  REPORT §9).
- **[model]** Fix: a takeover or promotion takes effect when the appointee's device
  accepts it, as the document already says of handovers ("signed by A and accepted by
  B"). Result: no residual made during the outage, and an overlap of 1 to 3 s at heal
  (H19'). In P-A nothing changes: there the residuals are the irreducible cost of A not
  being told.
- **[model]** The fix has a cost the search exposed: settlement must also wait for
  anyone named in an appointment not yet accepted. Without that, 2 of 100 random
  incidents revoked authoritative verdicts. This is fixed, and pinned by regression tests.
- **Changes:** state in the model when each kind of act takes effect.

### F4. A lease renewed at the core costs most when nothing is wrong with the commander

- **[model]** In P-B (backhaul lost, mesh up, A fit), S1, S2 and S3L stop A after L, and
  nobody else can record: 1,111 s without command out of a 1,200 s outage, and 19 valid
  orders refused (REPORT §2, P-B). Under S0, S3 and S4 there is no cost in P-B.
- **[inference]** Table II gives S1's main cost as "residual decisions; needs the core".
  At the defaults S1 produces no residuals. Its dominant cost is having no command at all
  in exactly the case the document calls common ("commanders lose data but keep voice").
  This is gap 5 of section III-B, quantified. It is a strong argument for treating S1 as
  the prototype's baseline and not as a candidate.

### F5. S1 and S2 are the same policy unless the operator reacts faster than L

- **[model]** S1 overlaps only if the operator promotes B before A's lease runs out: 73 s
  of overlap at a 15 s reaction time, 0 from 90 s up with L = 90 s (REPORT §5); with a
  120 s reaction, 58 s at L = 180 s and 478 s at L = 600 s (REPORT §4). Table II's "S1:
  overlap of up to L" fails at the defaults (H6: 0 of 20 runs).
- **[inference]** What separates S1 from S2 is L against human reaction time. The
  prototype's L = 90 s is below any plausible operator reaction, so in practice the
  prototype runs S2. Say so; it also reframes the prototype's "fencing" results.

### F6. S3 with a lease needs C to wait for it; without the lease, voice decides everything

- **[model]** S3L with A fit and answering: the lease stops A, C hears A and does
  nothing, and nobody records for 1,112 s. Command continues by voice only, outside the
  journal. With A fit but not answering, S3L overlaps whenever L exceeds C's reaction
  time (120 s detection plus a 60 s call): 118 s of overlap at L = 300 s (H12 fails for
  L ≥ 300 s).
- **[inference]** Table II's "S3: (c) only with a lease on A's side" is incomplete. The
  lease must be shorter than C's reaction, and it reintroduces F4's cost.

### F7. "Silence" must say whose: a connected but unfit commander defeats S4

- **[model]** A commander who is incapacitated while their device stays connected is not
  silent. S0, S4 and S5 never move command, so nobody records for the whole incident.
  S1 and S2 act on a voice report (302 s), S3 and S3L on a report and a failed call
  (362 s). S4 with a dead-man switch (`presence="person"`) takes over at T (300 s),
  at a cost the testbed does not measure: needless takeovers when A is merely idle.
- **[model]** In P-B, with A unfit, neither S3 nor S4 moves command during the outage
  (H11: 0 of 40). S3 fails because C's act cannot reach the scene, S4 because A's device
  is still heard over the mesh. The draft's section II-D says both can.
- **Changes:** the storyboard's "cut off or incapacitated, and nobody can tell which"
  is half right. The network cannot tell, and a device heartbeat says the wrong thing.
  The model must say whether presence is the device's or the person's.

### F8. The document's failure cases are partly wrong

- **[model]** One-way links (model document section 9 says A and B both accept): if A
  can receive but not send, the overlap lasts 1 s, because A hears of the activation. If
  A can send but not receive, A stops at T', B never activates, and nobody records for
  962 s (H19 fails). The real failure is no command, not two commanders.
- **[model]** A handover inside a P-C partition (A to S, while B activates in the other
  part): the precedence rule makes A's handover win, so B's whole tenure is residual
  under a grant that was never valid. That is 16 decisions, 903 s of S and B both
  recording, and 16 flips on the crew device in B's part of the mesh. Two successions in two
  partitions are the plural case in disguise; any deterministic precedence makes one
  side's orders residual. The document's statuses have no name for "never valid".
- **[model]** A's device ignoring T' gives 902 s of overlap and 16 residuals, as the
  document says.

### F9. Clock error is not where the cost is

- **[model]** With ε ≤ 2 s the in-doubt status never fires at one decision per 20 s; it
  appears at ε = 10 s (median 2 per run) and 60 s (9). Errors beyond the bound
  misclassify decisions: over 20 runs, 2 at 1 s, 9 at 5 s, 39 at 30 s (REPORT §7).
- **[inference]** Keep the in-doubt status, which costs nothing, and give it a paragraph,
  not a section. The enforcement margin (F1) and finality (F2) are where time goes.

### F10. Choosing T is a question about outage lengths, and the testbed cannot answer it

- **[model]** Under S4 a needless takeover happens exactly when the outage outlasts T
  (REPORT §3: a step function by construction). Every takeover also costs decisions the
  successor never received: 0 at T = 60 s, 5 at 300 s, 20 at 1,200 s. There is a
  deliberate gap of T − T' with nobody recording (61 s at the defaults).
- **[open]** The expected cost is P(outage > T) under the real distribution of
  commanders' data outages. Only the rescue service can supply that distribution.
  Ask for it in those terms.

### F11. What holds as drafted

**[model]** S0's entries (H1 to H3); S1 losing command in P-B (H7); S2 never overlapping
on fixed partitions (H8, H9); S3 moving command when C can reach the scene (H10); S4's
(a) and (b) entries and its (c) on fixed partitions (H13 to H15); S5 overlapping (H17);
stopping A early avoiding residuals but not completeness gaps (H18a, H18b); in-doubt
containing errors within the bound (H21). REPORT §1 has the counts.

## 3. A journal structure this supports

**[inference]** Contributions, in order:

1. **The authority model with finality.** Persons, grants and succession acts; the four
   statuses; the settlement rule with its safety property (no authoritative verdict is
   ever revoked) and its liveness condition (the predecessor's records, or an
   unconditional act by the appointing authority). Evidence: proof sketch, TLA+ for
   safety, testbed for liveness by act kind.
2. **Device-local enforcement.** Acknowledged timeouts, with the margin condition
   T − T' > ε; appointments that take effect on acceptance. Evidence: counterexamples
   against the unacknowledged rules, proof sketch, TLA+ with store-and-forward.
3. **The policy cost map.** Policies by case and commander state, measuring overlap, time
   without command, residuals, refused valid orders, completeness, settlement latency
   and orders that crews later see become residual, plus the parameters the organization
   must set (T, L, how fast unfitness is reported) and the data needed to set them.
   Evidence: this testbed.
4. **Prototype validation.** The anchor policy implemented in the prototype and run on
   the multi-host testbed, only for the cells where the simulation depends on timing
   (relay, margin, P-B), compared with the testbed's predictions.

Demote: the (a)/(b)/(c) trade-off to framing; the Raft and CRDT baselines to a short
section on who decides; throughput and fleet scaling to a sentence.

**[open]** The venue depends on which of 1-2 or 3 leads. With TLA+ proofs, 1 and 2 suit
a dependable-systems journal; led by 3, with rescue-service grounding, an applied
emergency-communications venue suits better. Decide before rewriting.

## 4. Decisions the model document now needs

Each was a `MODEL CHOICE` in the code (README). Recommended answers first.

1. Silence and presence: device or person? Recommend device, with S3's voice report for
   unfitness (F7), and state the gap for S4.
2. T' and leases: acknowledged (F1).
3. When appointments take effect: on acceptance (F3).
4. Settlement: `closing`, plus C's ratification of an S4 activation (F2).
5. Precedence between A's handover and B's activation inside a partition, and a name
   for decisions made under a grant that was never valid (F8).
6. Anchor policy: the testbed favours S3 with acceptance. It costs nothing in P-B when A
   is fit, handles a connected but unfit commander, and settles fast. Its weaknesses are
   P-A with A fit but silent (overlap until A learns), and P-B with A unfit (no command
   until heal). S4 with acknowledged T' and ratification is the proposal for when C
   cannot act.

## 5. Questions for the rescue service, now quantitative

1. How long are commanders' data outages: a distribution, not a typical value? It sets T
   (F10) and L (F4 to F6).
2. How quickly does the centre learn that a commander is unfit? That sets takeover delay
   under S1 to S3 (F7).
3. Is command given by voice alone, unrecorded, for many minutes acceptable? S1, S2 and
   S3L produce exactly that (F4, F6).
4. Would a commander hand over locally while the deputy is out of reach (F8)?
5. Can crews and operators work with orders marked provisional for the whole outage?
   Every policy produces that in P-B and P-C (settlement p95 ≈ outage length; REPORT §2).

## 6. Limits of these results

- Parameters, not measurements: latencies, gossip and heartbeat periods, reaction
  times, decision rates. Structural results survive changing them; magnitudes do not.
- The truth oracle applies the same rule as the devices, so "misclassified" tests timing
  and clocks, not whether the rule is the right one for the organization.
- Gossip assumes in-order delivery per link; the completeness proof in F2 relies on it,
  and real links reorder. The sequence-number check still holds, but the argument needs
  restating.
- The random search is evidence, not proof: 2,200 incidents found the faults behind F1
  and F3, but it is not exhaustive. Use TLA+ for the two properties in section 3.
- One incident, one commander, one deputy, fixed topology; no mobility or radio model.
- An artifact to note: under S1 and S2 in P-C, the operator promotes B in the instant of
  heal, because B's link returns a moment before A's heartbeat does. A human operator
  would wait; the policy as specified does not.
