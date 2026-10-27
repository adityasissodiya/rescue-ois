# Steering the paper toward ACM TCPS

This manuscript turns the WONS conference draft (commit `d1b1eca`) into a journal
manuscript for ACM Transactions on Cyber-Physical Systems. The WONS draft stays as it is
at that commit until the supervisors sign off the system model. This file says what changes, why, and
what evidence the journal version still needs. The results it relies on come from the
testbed in `../testbed/`: `FINDINGS.md` and `results/REPORT.md` there.

## Why TCPS

- The draft's direction since the October reframing is human authority: command belongs to
  a person, the organization decides who, devices only enforce. TCPS lists human-in-the-loop
  and resilient system design in its scope; a dependable-systems venue would push the people
  into the background.
- The gap is open there. The Consensus review of human-in-the-loop authority transfer finds
  no work on what happens to authority and decisions when links return (its "reconnection"
  row is empty) and little on transfer between human operators under degraded links.
- Our evidence fits: a testbed with 8,950 simulated incidents, a prototype of one policy,
  formal models. Full proofs are not required; proof sketches plus model checking are.

## Working title and question

**Title (working):** Command Succession under Intermittent Connectivity: Enforcing and
Reconciling Human Authority in Incident Response.

**Research question:** How can an intermittently connected incident-response system
represent the transfer of command authority between people, enforce it on devices that
cannot reach each other, and reconcile it when they reconnect, and what does each
succession policy cost the people who act on its decisions?

The WONS question asked the first half. "Reconcile when they reconnect" and "cost the
people who act" are new; they are where the gap is.

## Contributions and the evidence for each

| | Contribution | Gap it answers | Evidence now | Evidence still needed |
|---|---|---|---|---|
| C1 | A model that separates a person's authority from a device's enforcement, with decision statuses shown to the people who act on orders | Human-in-the-loop work treats authority as human vs. automation over an actuator; nobody models succession between humans through devices | System model (`model/`), testbed | Sign-off; rescue-service practice (interviews) |
| C2 | The succession policies S0 to S5 with measured costs across connectivity cases and commander states (fit, fit but silent, unfit) | Operator-to-operator transfer under degraded links: proposals, no costs | Testbed matrix, sweeps of T and L | Prototype runs of the anchor policy on the multi-host testbed |
| C3 | Reconnection semantics: appointments that take effect on acceptance, settlement of decisions, and what crews see | Empty "reconnection" row; "how should authority tokens and leases expire and recover after partition?" | Testbed faults and settlement experiments | Expert walkthrough with rescue-service officers |
| L1 | Supporting result: an acknowledged timeout keeps one device accepting whenever T - T' > eps, under store-and-forward links; the unacknowledged rule does not | Heartbeat-bound credentials bound the window by W + delay + eps and assume the revoker stops beating | Counterexample, search, margin sweep | Proof sketch in the paper; TLA+ check |
| L2 | Supporting result: settlement never revokes a confirmed verdict, and completes only through the predecessor's records or an act by the appointing authority | ECAC: only the causal part of a verdict is final without coordination | Search (no revocation in 2,200 incidents), settlement experiment | Proof sketch; TLA+ check |

Not a contribution any more: the decision statuses as such (they are ECAC's causal and
topological authorization applied to command), the (a)/(b)/(c) trade-off (it holds by
construction; it stays as framing), and the prototype's replication path.

## What changes from the WONS draft

| WONS draft | TCPS manuscript |
|---|---|
| IEEEtran conference, 8 pages | `acmart`, `acmsmall` journal format |
| Research question on representing, enforcing and auditing succession | Adds reconnection and the cost to people |
| Trade-off as a contribution | Trade-off as framing, one paragraph |
| Table II entries as hypotheses | Table II revised by the testbed: six entries fail as stated |
| Prototype (S1) as the main evidence | Prototype as the implementation baseline; testbed as the evaluation of the policy space; prototype extension pending |
| Related work: leases, consensus, weak-consistency access control, CRDTs, incident command | Adds human-in-the-loop authority transfer (shared control, interlocked transfer, lost-link fallback, reconnection) and finality of authorization (ECAC, freshness, epochs, effect closure) |
| Raft and CRDT baselines in the evaluation | Kept short, as evidence that consensus and merge cannot carry the organization's decision |
| Throughput, fleet size, outbox replay | One paragraph of implementation checks |

## Decisions the supervisors need to make

These were `MODEL CHOICE`s in the testbed; the manuscript marks each with `\pending`.

1. **Anchor policy.** Proposal: S3 (takeover by C) with appointments effective on
   acceptance; S4 with acknowledged T' and ratification by C as the proposal for when C
   cannot act. Depends on rescue-service practice.
2. **Presence.** Is silence the device's or the person's? Device presence cannot detect a
   connected but unfit commander (S4 never moves command); person presence (a dead-man
   switch) can, at the price of needless takeovers.
3. **When appointments take effect.** On acceptance (proposal), not on signature.
4. **Settlement rule.** `closing` (an unconditional act by the appointing authority closes
   the predecessor's chain), plus ratification of S4 activations.
5. **Precedence inside a partition.** A handover by A and an activation by B in different
   parts: the current rule lets A's handover win and turns B's whole tenure residual.
6. **Relation to WONS.** If WONS publishes the conference version, the journal version
   cites it and states what is new; check ACM's policy on extended conference papers.

## Evidence plan, in order

1. **Sign-off** of the system model with decisions 1 to 5.
2. **Rescue-service interviews** on succession practice (questions in `model/`, section 10,
   and testbed `FINDINGS.md` section 5): how command moves, whether pre-authorized
   succession exists, how long commanders' data outages last, how fast unfitness is
   reported, and whether provisional orders are workable.
3. **TLA+** for L1 (one acceptor at a time, with relaying channels and acknowledged
   heartbeats) and L2 (no revoked confirmation). The existing model in `formal/tla` has no
   persons, no lease and no relaying; extend it rather than start over.
4. **Prototype**: persons, signed grants and succession acts, the anchor policy with
   acceptance and settlement, run on the multi-host testbed for the reconnection cases,
   and compared with the testbed's predictions for the same schedules.
5. **Expert walkthrough**: officers walk through the storyboard and the status display;
   record whether they read provisional and residual orders as intended.
6. **Write**: sections 5 and 6 of the manuscript change most once 3 to 5 exist.

## Before submission

- Remove every `\pending{}`; drop the `review` class option.
- Regenerate the CCS concepts with the ACM tool; confirm TCPS's current author guidelines
  (template options, length, review model).
- Fill the publisher and address fields BibTeX warns about (ACM reference format), and
  verify the entries marked VERIFY in `refs.bib`.
- Fix the citation the WONS draft gets wrong: the impossibility result is
  `yanakieva2021impossibility`, not `yanakieva2021access`.

## Risks

- **"An information system, not a CPS."** Make the physical coupling explicit: crews
  execute orders, terrain decides connectivity, and time without command is physical
  exposure. The manuscript states this in section 3.
- **No human evidence.** Step 5 is the minimum; without it the human claims are asserted.
- **Novelty of the statuses.** Cite ECAC and Bayou-style tentative writes up front and
  claim only what goes beyond them (L2's liveness condition, acceptance, enforcement).
- **Parameters.** Testbed magnitudes follow from chosen parameters; claim structure
  (which policies fail where), quote magnitudes as illustrations.

## Numbers

Every testbed number in the manuscript is a macro in `data/testbed_macros.tex`, generated
by `python -m aas_testbed latex` from committed results; `data/TESTBED_TRACE.md` maps each
to its CSV, filter and statistic. Prototype numbers keep their trace in `TRACEABILITY.md`.
