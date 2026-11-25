# Roadmap and decision memo

Written 2026-11-24 with AI assistance (Claude); not reviewed by a person. Everything here
is planned work: nothing below has been done unless it names an existing file.

## Decision memo: is there a contribution beyond known compositions?

**Finding.** Removal by quorum renewal and expiry is in URSA (2004). Exclusive succession
is the grantor-side rule of quorum leases (Nerio, crash faults). Our Byzantine, signed,
device-checked composition of the two (`xl`, `sim/baselines.py`) gives the same separation
and withdrawal-to-expiry values as Mandate in every directed run we have
(`CMP-HANDOVER-*`, `CMP-REMOVAL-*`, `CMP-ISOLATION-*`) and avoids Mandate's same-holder
split-vote stall (`CMP-SPLIT-SAME-HOLDER-XL`). A candidate argument for `xl` separation
exists (positioning s. 3.2) but nobody has reviewed it, and it has no bounded model yet.

**Consequence.** The seed cannot honestly claim a new mechanism. It can claim, after
review: a precise problem statement for hostile authority holders at disconnected
verifiers; property definitions that separate isolation reach (existential) from
fresh-command availability (universal) and anchor removal at the withdrawal instant; a
candidate rule set with arguments; and an executable evaluation method (directed
scenarios, independent checker, negative controls, comparators).

**Options** (for the supervisors to decide; listed, not ranked by preference):

1. *Characterization paper.* Present the problem, the definitions, the bounds (with the
   lower bound credited to the indistinguishability tradition) and a reviewed proof that
   the composition `xl` meets them; Mandate becomes one instance. Risk: reviewers may see
   the result as a straightforward composition.
2. *Find a real difference.* Look for properties where epochs matter: ordering of commands
   across holders at a device (an epoch number gives a total order of terms; `xl` has no
   term identity when the same holder returns), audit, or re-appointment. Close only with a
   checked scenario or a proof where `xl` fails and Mandate holds.
3. *Change the question.* Move to an aspect the sources do not cover, for example
   membership change of the officer set under partitions, or semantic limits on what an
   authorized hostile holder can do in the bound (damage bounds). Each needs a new
   problem statement and new prior-art search.
4. *Evaluation-centred paper.* Use the scenario and checker method to compare published
   designs (threshold credentials, leases, quorum per order) under one hostile-holder model.
   Needs the strong comparators implemented faithfully and reviewed.

No option is chosen here. Experiment R1 below is the first input to the decision.

## Ranked open questions

| Rank | Question | Why it matters | Closure criterion |
|---|---|---|---|
| R1 | Does `xl` (threshold credentials + exclusive leases) already meet Mandate's guarantees at comparable cost? | Decides whether any mechanism novelty is left | Either a person reviews a proof that `xl` satisfies separation, withdrawal-to-expiry and fresh-command availability under the seed model, or a checked counterexample shows a property `xl` lacks and Mandate has |
| R2 | Are the candidate arguments for separation, withdrawal-to-expiry and fresh-command availability correct as stated in `spec/protocol.md`? | No proof has been reviewed by a person | A supervisor or co-author checks each step against the spec; `research/claims.csv` statuses change only then |
| R3 | What do HRCred (s. 4.7) and Stantchev 2026 do, and what do forward citations of URSA and Nerio contain (Byzantine leases, leader leases with signatures, epoch revocation in industrial control, IEC 62351-8)? | Prior art may already contain the composition or the bounds | Full texts read; positioning table updated with page pins; any overlapping mechanism recorded |
| R4 | Does the bounded model still pass with eps > 0, two verifiers, Byzantine withholding and epoch 3? | Current TLC bounds are small (`spec/tla/README.md`) | TLC runs with the new constants finish, logs saved; expected-violation configurations still fail |
| R5 | How should split votes be prevented or bounded without weakening one-vote-per-epoch? | `ORIG-SPLIT-STALL` and `V0-SPLIT-RECOVERY` show the gap; recovery needs delivery, quorum readiness and coordination | A specified proposal-coordination rule (or an argument that none is possible without consensus) plus scenarios showing recovery time under stated assumptions |
| R6 | What operations must continue when a control room is isolated, and for how long? | H and the availability requirement come from the domain, not from us | Answers from people who operate grids, recorded with consent; until then all values stay synthetic |
| R7 | Where would the verifier sit (relay, RTU, gateway), and what clock holdover gives eps? | Trusted enforcement and the clock bound are assumptions | A documented device model or a measured holdover bound |
| R8 | Membership change and key revocation | Out of scope in seed-v0 | Separate specification |

## Experiments and comparators

### E1. Composition decision (answers R1)

* Write `xl` as a second TLA+ module with the same abstractions as `MandateSeed.tla` and
  check separation and withdrawal-to-expiry at the same bounds.
* Run every `V0-*` scenario through an `xl` translation (holder-indexed leases) and compare
  checker results and metrics.
* Write the `xl` proof in the style of the Mandate candidate arguments and ask a person to
  review both.
* Closure: R1 criterion.

### E2. Prior-art closure (answers R3)

* Obtain HRCred and Stantchev 2026 through a legitimate route (library access or the
  authors) and read the relevant sections; forward-chain URSA and Nerio; search Byzantine
  lease literature.
* Closure: R3 criterion.

### E3. Review and wider bounded checking (answers R2, R4)

* Human review of the arguments in the paper appendix.
* TLA+: eps > 0 with two verifiers, epoch 3, Byzantine withholding; report state counts.
* Coverage report for any randomized schedule exploration added later: accepted commands,
  renewals, handovers, withdrawals, boundary acceptances (as `experiments/checker.py`
  metrics already record for directed runs). Random runs without coverage are not
  evidence.

### Strong comparators (specified; only `xl` and `qo-w` are implemented)

* `xl` exclusive-lease composition: implemented as a mechanism abstraction; semantics in
  `sim/baselines.py` and `research/positioning.md` s. 3.2. Still to do: bounded model,
  proof, review.
* `qo-n` fresh quorum per order: the verifier issues a nonce; officers sign
  (command, nonce, deadline); the verifier accepts once, before the deadline, and only for
  its own nonce. Expected properties to check: no acceptance of a command created after
  withdrawal; in-flight commands bounded by the deadline; zero fresh availability without
  a path to a quorum; one round trip verifier-officers-verifier per command. Not
  implemented in this pass because the round trip changes the network model of the
  simulator.
* `qo-w` windowed quorum per order: implemented (`sim/baselines.py`); not equal to any
  published system.

## Milestones

1. Decide among the memo options with the supervisors (input: E1 and E2).
2. Reviewed proofs (E3) before any claim moves from "candidate argument".
3. Only then: a runnable prototype with real processes and measured costs, if the chosen
   option needs one. The current seed is an executable specification with a real
   signature mode, not a deployable implementation.
