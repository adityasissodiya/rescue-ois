# reasonableUpdates.md

## Purpose

Use this file as a concrete revision brief for Codex. Codex has access to the paper LaTeX files, repository source code, evaluation scripts, figures, tables, and generated results. The goal is to strengthen the paper by making its claims match the actual implementation and evaluation evidence.

The revision should make the paper harder to reject by being precise, modest, technically correct, and reproducible. Do not fabricate evidence. Do not claim field deployment, real mesh measurements, tablet evaluation, crash safety, mTLS overhead, WireGuard overhead, or production completeness unless the repository contains direct support for those claims.

The intended final framing is:

> This paper presents a domain-specific, authority-aware, offline-first architecture for rescue-service incident operations. It composes known mechanisms - durable outboxes, append-only journals, edge caches, single-command authority, and bounded promotion rules - and evaluates a prototype in an emulated environment.

Avoid framing the work as an entirely new replication paradigm or as a completed field-ready system.

---

## Global revision principles

1. Narrow unsupported claims rather than making them sound more impressive.
2. Separate measured results from analytic consequences of the architecture.
3. Separate operational requirements from design assumptions and deployment choices.
4. Be explicit about what is implemented, what is scaffolded, and what is not evaluated.
5. Treat the Raft comparison as contextual, not workflow-equivalent.
6. Treat the formal model as bounded validation of a specific safety invariant, not proof of full system correctness.
7. Preserve the core contribution: a practical authority-aware offline-first design for incident data under intermittent connectivity.

Search the paper for language that overclaims and revise it. Examples to soften or remove:

- "No existing replication pattern satisfies..."
- "the smallest protocol structure..."
- "field-realistic" unless the evaluation actually exercises field conditions
- "equivalent scenarios" when comparing non-equivalent Raft and Rescue OIS paths
- "verified" when the evidence is bounded model checking
- "by architecture" when presented as if it were measured data
- "complete implementation" if the implementation is actually scaffolded or partial

Preferred wording:

- "we argue"
- "under the stated assumptions"
- "in this operational setting"
- "in emulation"
- "bounded validation"
- "contextual comparison"
- "prototype path"
- "not yet crash-validated"
- "deployment design, not evaluated in this experiment"

---

## 1. Abstract

Revise the abstract so it is defensible.

The abstract should state that:

- the system is a prototype, not a completed production deployment;
- the evaluation is a Docker Compose or emulated evaluation, not a real field deployment;
- Rajant mesh, WireGuard, mTLS, Android tablet clients, and physical deployment are target deployment components unless the repository proves they were exercised in the experiments;
- the formal validation is bounded and checks an abstract authority/promotion model;
- the Raft comparison is contextual and illustrates the availability trade-off under quorum loss, not an end-to-end workflow-equivalent benchmark.

Do not let the abstract imply that all production components were implemented and evaluated if that is not true.

Suggested abstract direction:

> We present an authority-aware offline-first architecture for rescue-service incident operations under intermittent connectivity. The design uses core-to-edge distribution for reference data, durable forward-only outboxes for responder submissions, and a single command-side journal for authority-bearing incident decisions. A prototype is evaluated in an emulated deployment covering bootstrap, forwarding latency, partition recovery, replay, and selected baseline comparisons. Bounded model checking and property tests validate the single-writer and promotion invariants in an abstract model. The results show the trade-off made by the design: responder and WAN partitions need not block command-local progress, but command promotion requires explicit fencing and does not provide automatic failover.

Adjust the wording to fit the paper's actual terminology and results.

---

## 2. Introduction

Revise the introduction to avoid overselling novelty.

Keep the motivation: rescue-service incident operations require local operation, intermittent connectivity tolerance, durable field submissions, and command authority.

But reduce claims that existing replication systems are categorically unsuitable. Replace broad dismissal with trade-off language:

- CRDTs are useful for mergeable state, but authority-bearing command decisions cannot always be resolved through commutative merge semantics.
- Consensus gives strong ordering when quorum is available, but quorum availability may not hold during vehicle isolation or degraded incident networks.
- Multi-primary/offline-first systems allow local writes, but require conflict semantics that may be unacceptable for command decisions.
- The paper chooses a different point in the design space: preserve a single operational command writer and allow non-command nodes to submit durable forward-only events.

Revise the contribution list. A defensible contribution list would be:

1. A requirements and constraint analysis for authority-bearing incident information in rescue-service operations.
2. A tiered offline-first architecture combining core-to-edge reference-data distribution, responder outboxes, and a single command-side incident journal.
3. An explicit synchronization and consistency contract for field submissions, command sequencing, and materialized edge state.
4. An emulated prototype evaluation covering bootstrap, field-edit forwarding, partition recovery, replay/idempotency, and contextual baseline scenarios.
5. Bounded model checking and property testing of the single-writer and promotion safety invariant.
6. A discussion of operational trade-offs, especially strict promotion/fencing versus automatic failover.

Do not claim a complete production implementation unless the repo supports it.

---

## 3. Requirements section

Strengthen the requirements section by separating:

- externally motivated operational requirements;
- design assumptions;
- deployment and integration choices.

At present, some requirements may read like architectural decisions disguised as external requirements. Revise them so the paper is honest about the derivation.

Suggested distinction:

- Offline local operation: operational requirement.
- Durable forward-only submission: system requirement derived from not losing field observations.
- Single command authority: operational/organizational assumption for authority-bearing decisions.
- Predictable mesh/network behavior: network-engineering constraint.
- Existing organizational identity: deployment/integration constraint.

Add a small traceability table if space allows. Example:

| Item | Type | Rationale | Architectural consequence |
|---|---|---|---|
| Offline local operation | Operational requirement | Incident work must continue during degraded WAN or vehicle isolation | Edge cache and local services |
| Durable field submission | System requirement | Field observations must survive disconnection and restart | Tablet/edge outbox and retry |
| Attributable command authority | Operational assumption | Command decisions require an identifiable authority | Single command-side journal writer |
| Predictable network behavior | Deployment constraint | Avoid uncontrolled cross-vehicle write traffic | Mesh as transit, segmented routing |
| Existing identity integration | Integration constraint | Avoid separate emergency-only identity namespace | mTLS/CA integration and mapped identities |

Make clear that these are the requirements and constraints adopted for this design, not universal laws for all rescue-service systems.

Important nuance: distinguish operational command authority from storage/replication authority. Do not imply that because one person has command authority, the only possible storage design is a single writer. Instead, argue that the single-writer journal is the design choice made to align the storage authority boundary with the operational authority boundary.

---

## 4. Related work

Make the related-work section less adversarial and more precise.

Add or revise text to acknowledge that the architecture composes known mechanisms:

- event sourcing or append-only incident journals;
- transactional outbox patterns;
- durable store-and-forward messaging;
- materialized views;
- single-primary replication;
- offline-first client caches;
- manual failover and fencing.

The novelty should be framed as domain-specific composition and consistency-boundary selection, not invention of every component.

Revise any text that makes CRDTs, consensus, or multi-primary replication sound generically wrong. Suggested phrasing:

> These techniques are not unsuitable in general. They optimize different correctness and availability properties. Our setting distinguishes mergeable reference or observation state from authority-bearing command decisions. For the latter, the design deliberately avoids concurrent command writers and instead uses a single command-side journal with durable submissions from non-command nodes.

If related work references are incomplete, add citations only if they already exist in the bibliography or can be added properly. Do not add unverified citations casually.

---

## 5. Add or strengthen data-model taxonomy

Add a concise subsection, likely near the architecture or protocol section, that separates state classes and their consistency contracts.

The paper should not imply that all incident data has identical consistency requirements. Add a taxonomy similar to this:

| State class | Examples | Consistency/replication contract |
|---|---|---|
| Master/reference data | maps, site plans, preplans, hydrants, static layers | core-to-edge distribution, eventual convergence |
| Immutable artifacts | packaged maps, manifests, attachments | content-addressed or manifest-validated distribution where applicable |
| Field observations | responder notes, observations, local reports | durable append-only outbox, at-least-once forwarding, idempotent acceptance |
| Command decisions | assignments, orders, incident-level state transitions | single command writer, total order by sequence number |
| Materialized operational views | current incident view, task status, local map overlays | derived from journal, rebuildable |
| Audit events | access, submission, promotion, replication events | append-only, eventually forwarded to core |

This section should explicitly state that the single-writer constraint is for authority-bearing incident journal entries, not necessarily every byte of data in the system.

---

## 6. Protocol specification

Strengthen the protocol description. Add precise language for identifiers, idempotency, acknowledgements, retries, and transaction boundaries.

The protocol section should answer these questions:

1. What is the globally unique identity of a submitted event?
2. Where is the event durably stored before acknowledgement to the user or tablet?
3. When does the command node assign the authoritative sequence number?
4. How are duplicate submissions handled?
5. What exactly does an acknowledgement mean?
6. When may a responder mark an outbox item as forwarded?
7. How do edge nodes replay or catch up after disconnection?
8. Which state is authoritative, and which state is derived/rebuildable?

Add a compact protocol contract such as:

- Each client submission contains `incident_id`, `client_id`, and `client_event_id`.
- The responder edge or tablet stores the submission in a durable outbox before acknowledging local acceptance.
- The command node accepts a submission only once for each idempotency key.
- The command node assigns `seq` atomically with journal insertion.
- A responder marks a submission forwarded only after receiving acknowledgement from the command writer.
- Consumers apply committed journal entries in sequence order.
- Materialized state is derived from the journal and can be rebuilt.

Only include fields that match the actual implementation, or mark them as intended protocol fields if implementation is partial.

If repository code has actual names for these fields, use those names rather than the illustrative names above.

---

## 7. Command promotion, epochs, and fencing

This is a high-priority revision.

The paper should explicitly state the command promotion trade-off. The system must not vaguely rely on "manual promotion" as if that alone prevents split brain.

Add or strengthen a subsection called something like:

> Command promotion, epochs, and fencing

The section should define the intended safety mechanism. Use actual implementation details if they exist. If not implemented, present it clearly as protocol design and limitation.

Desired content:

- Each command tenure has a monotonically increasing `command_epoch` or equivalent term.
- Journal entries include enough information to distinguish command epochs, such as `incident_id`, `command_epoch`, and `seq`.
- Promotion produces an explicit promotion record.
- Nodes reject command traffic from stale epochs once they learn a newer epoch.
- A recovering old command node must rejoin as a non-command node until reconciled.
- Weak promotion can produce split brain and is deliberately excluded.
- Strict promotion/fencing preserves safety but may sacrifice availability if the previous command node cannot be fenced or its status cannot be established.

Use sober wording:

> The design does not provide automatic failover. It chooses operator-confirmed promotion and fencing to preserve command authority and avoid implicit split brain.

Do not claim this is fully implemented if only the model or scaffold exists. If the repository contains TLA+ models of strict and weak promotion, cite them in the text and describe the weak-promotion counterexample as evidence for the chosen rule.

---

## 8. Implementation status

If the paper currently says something like "working scaffold rather than complete implementation," restructure that into a precise implementation-status table. This is more credible and less damaging than a vague admission.

Add a table similar to this, adapted to actual repository contents:

| Component | Prototype status | Evaluated in paper? |
|---|---|---|
| Core/edge Docker services | Implemented or emulated | Yes, if true |
| Baseline package/bootstrap path | Implemented in emulation | Yes, if true |
| Responder outbox forwarding | Implemented/scaffolded | Yes, without crash injection if true |
| Command sequencing and idempotency | Implemented/scaffolded | Replay-tested if true |
| PostgreSQL logical replication | Partial or configured | State actual status |
| mTLS | Deployment design or partial | State whether exercised |
| WireGuard | Deployment design or partial | State whether exercised |
| Rajant mesh integration | Target deployment component | State whether exercised |
| Android tablet app | Partial or not used | State if Python stub was used |
| Audit forwarding | Scaffolded or implemented | State validation status |
| Ansible provisioning | Partial or complete | State validation status |

Use actual repo facts. Do not invent statuses.

Make sure the abstract, introduction, and conclusion are consistent with this table.

---

## 9. Evaluation section: general cleanup

Reframe the evaluation as an emulated prototype evaluation unless real field data exists.

Add missing reproducibility details where available from scripts, configs, or logs:

- hardware and operating system;
- CPU and RAM;
- Docker or container runtime version;
- database version and relevant durability settings;
- number of containers/services;
- event payload size;
- number of clients or workers;
- queue depths;
- polling intervals;
- retry/backoff parameters;
- number of repetitions;
- warm-up handling;
- whether TLS/mTLS/WireGuard was enabled;
- whether Android tablets or Python stubs generated load.

If a detail is not available, add a limitation rather than guessing.

Separate three kinds of claims:

1. directly measured experimental results;
2. analytic consequences of the architecture under stated assumptions;
3. deployment expectations not evaluated in the paper.

Tables should not mix these without clear labels.

---

## 10. Evaluation: bootstrap latency

Review the bootstrap results. If the medians are non-monotonic across AOI size, do not describe them as a scaling law.

Replace claims such as "sub-linear scaling" with something like:

> In this emulation, bootstrap latency is dominated by fixed overheads and remains below X ms across the tested AOI sizes. The non-monotonic medians indicate that these runs should not be interpreted as a scaling law.

Use the actual maximum or range from the paper/evaluation files.

If the evaluation data supports a stronger claim, state it carefully and include uncertainty or repetitions.

---

## 11. Evaluation: field-edit latency

Clarify what the measured field-edit latency includes.

The paper should state whether the latency includes:

- local outbox enqueue;
- polling delay;
- connection setup;
- command sequencing;
- database commit;
- acknowledgement;
- materialized view update;
- responder catch-up.

If the median is roughly one polling interval or close to a timeout value, explain it as a consequence of the implementation configuration rather than inherent architecture.

Avoid implying that these numbers are field-radio latency measurements unless real radio tests were run.

---

## 12. Evaluation: partition and recovery

Clarify which partitions were evaluated:

- responder isolated from command;
- command isolated from core;
- command isolated from responder;
- WAN partition;
- mesh partition;
- process crash;
- container restart.

If only some were tested, say so.

If shorter partitions recover slower than longer partitions due to polling or backoff phase effects, explain this as an implementation artifact and avoid overinterpreting it.

Suggested wording:

> Recovery time in the emulation is affected by the phase of polling and retry timers, so the measured recovery latency should be interpreted as behavior of this implementation configuration rather than a general network-recovery law.

---

## 13. Evaluation: replay and idempotency

If replay/idempotency tests exist, strengthen the description. Include:

- how duplicates are generated;
- which idempotency key is used;
- whether duplicates are dropped, acknowledged, or mapped to an existing journal entry;
- whether sequence numbers remain gap-free or merely monotonic;
- whether duplicate submissions can occur across restart.

If crash/restart was not tested, state that clearly.

Suggested limitation:

> The current evaluation validates replay idempotency in the emulated service path, but it does not yet inject crashes at all durable boundaries, such as after local enqueue, after command append before acknowledgement, or during forwarded-state marking.

---

## 14. Evaluation: Raft comparison

This is a high-priority correction.

Do not call the Raft scenarios "equivalent" if they are not workflow-equivalent. Rename them to:

- "contextual baseline scenarios"
- "selected comparison points"
- "quorum-dependence comparison"
- "availability trade-off comparison"

Clarify that the Raft comparison isolates quorum-dependent progress, not end-to-end application performance.

If the paper compares Rescue OIS end-to-end responder path latency against direct Raft leader-write latency, explicitly state that these are not equivalent measurements and should not be read as an application-performance comparison.

Suggested wording:

> The Raft measurements are included to illustrate the quorum-availability trade-off. They are not workflow-equivalent to the Rescue OIS responder outbox path, which includes application-level forwarding and sequencing.

### Correct the Raft quorum formula

Check and fix the quorum-loss formula.

Correct formulation:

- A Raft cluster with `n` voting members requires a reachable majority of `floor(n/2) + 1` voters to make progress.
- Therefore progress is lost once at least `ceil(n/2)` voters are unreachable.
- For `n = 3`, losing 2 voters prevents progress.

Make sure the text, table captions, and any evaluation comments are consistent with this.

---

## 15. Evaluation: measured versus analytic claims

Remove or relabel table entries that present unmeasured architectural consequences as experimental results.

For example, do not put a row like this in a measured-results table without qualification:

> Rescue OIS writes succeeded: 100% - by architecture

Better options:

1. Remove the row from the measured table and discuss it in prose.
2. Move it to a separate "analytic consequence under assumptions" table.
3. Add an explicit label such as "not measured; consequence of design assumption that the command node and local storage remain available."

Suggested prose:

> Because the command writer does not require a responder quorum, responder isolation alone does not block command-local commits. This is an architectural consequence rather than a measured quorum-loss experiment. It assumes that the command node and its local storage remain available.

This distinction is important.

---

## 16. Formal verification section

Keep the TLA+ and property-testing material, but make the scope precise.

Clarify:

- the model checks the abstract authority and promotion rules;
- the bounds are intentionally small;
- the model is not a proof of production implementation correctness;
- weak promotion produces a split-brain counterexample, which motivates strict promotion/fencing;
- the model does not cover storage crashes, fsync behavior, certificate revocation, transport authentication, deployment misconfiguration, operator mistakes, or physical compromise.

Suggested wording:

> The model is not a proof of the production implementation. It is a bounded check of the authority and promotion rules. Its main value is that it distinguishes the adopted strict-promotion rule from a weak-promotion variant that produces a split-brain counterexample.

If the paper currently says "verified," consider replacing it with "model-checked," "bounded model-checked," or "validated under the model bounds."

---

## 17. Security and threat model

Add a short explicit threat-model subsection if it does not already exist.

The current security discussion should not merely list technologies. It should state assumptions, handled threats, and limitations.

Include, where relevant:

- trusted organizational CA or identity provider;
- enrolled devices and users;
- compromised or stolen tablet;
- stolen vehicle node;
- stale certificates during disconnection;
- old command node returning after promotion;
- replayed field events;
- malicious or buggy responder;
- backend trust in mTLS-derived headers;
- data at rest on tablets and edge nodes;
- offline revocation limitations;
- audit log integrity limitations.

Suggested wording:

> The design authenticates enrolled devices and users through the existing organizational certificate infrastructure, but it does not provide instantaneous revocation during total disconnection. Revocation takes effect when nodes regain contact with the authority infrastructure or receive an updated trust bundle.

Also state what is out of scope. For example:

- Byzantine command nodes;
- compromised organizational CA;
- physical tamper resistance beyond device encryption/MDM, if applicable;
- real-time revocation during full isolation.

Do not imply that mTLS alone solves offline identity or authorization.

---

## 18. Figures and tables

Improve readability and make captions precise.

Specific tasks:

1. Inspect Figure 1. If labels overlap or are cramped, redraw or simplify it.
2. Avoid cramming product/tool names into the main architecture figure.
3. Split dense tables if they read like a bill of materials.
4. Rename any Raft comparison table so it does not imply full equivalence.
5. Add caption notes distinguishing measured results from analytic claims.
6. Ensure all table values are generated from evaluation artifacts if possible, not manually copied.

For architecture figures, prefer logical roles over tool names:

- Core services
- Command edge
- Responder edge
- Tablet/client
- Mesh transit
- WAN/core link
- Durable outbox
- Command journal
- Materialized views

Tool names such as PostgreSQL, PostGIS, WireGuard, Rajant, or Nginx can appear in implementation tables, not necessarily in the conceptual figure.

---

## 19. Limitations section

Add or strengthen limitations. This should be honest but not self-destructive.

Cover these points if true:

- evaluation is emulated and not a field deployment;
- real mesh-radio behavior is not measured;
- WireGuard/mTLS overhead is not measured if disabled in experiments;
- Android tablet path is represented by a stub if true;
- crash injection at all durable boundaries is not complete;
- promotion/fencing may be protocol-level or model-level rather than fully implemented;
- security validation does not include compromised nodes or offline revocation under total isolation;
- results are single-incident or limited-scale unless multi-incident workloads were evaluated.

Use precise limitation language:

> This limitation bounds the claim to the prototype and emulation environment; it does not invalidate the architectural argument, but it means field deployment remains future work.

Avoid vague language such as "more work is needed" without saying exactly what work.

---

## 20. Conclusion

Revise the conclusion to match the narrowed claims.

The conclusion should say the paper demonstrates an architectural trade-off, not that it solved emergency-service distributed computing.

Suggested direction:

> The design preserves a single command authority for incident-journal state while allowing disconnected responders to continue durable forward submission. The prototype and model checking support the feasibility of this trade-off in emulation and in the abstract promotion model. The design deliberately does not provide automatic multi-writer failover; strict promotion and fencing are required to avoid split brain. Field-radio evaluation, full crash-injection validation, and production hardening remain future work.

---

## 21. Repository and evaluation checks

Before editing claims, inspect the repository to determine what is actually implemented and tested.

Recommended checks:

1. Locate the main LaTeX files and bibliography.
2. Locate evaluation scripts, raw results, JSONL/CSV outputs, and plotting/table-generation scripts.
3. Check whether evaluation tables in the paper are generated or manually written.
4. Check whether TLS, mTLS, WireGuard, Rajant mesh, and Android clients were enabled in the experiments.
5. Check whether crash-injection or restart tests exist.
6. Check whether replay/idempotency tests exist.
7. Check whether TLA+ models include both strict and weak promotion variants.
8. Check whether generated numbers in the paper match raw evaluation outputs.
9. Check whether all cited implementation components are actually present in the repo.

If possible, regenerate tables from source data. If regeneration is not possible, do not silently change numbers. Instead, update captions and prose to make existing numbers defensible.

---

## 22. Do not fabricate

Do not add unsupported claims. Specifically, do not claim:

- real Rajant mesh measurements unless raw evidence exists;
- WireGuard overhead measurements unless WireGuard was enabled in the experiment;
- mTLS overhead measurements unless mTLS was enabled in the experiment;
- Android tablet evaluation if a Python stub was used;
- production deployment if only Docker Compose was used;
- full crash safety unless crash-injection tests exist;
- complete Ansible provisioning unless verified;
- complete audit integrity unless implemented and tested;
- practitioner validation unless interviews, workshops, or field exercises are documented;
- multi-incident scalability unless evaluated.

If a claim is desirable but unsupported, downgrade it to future work or a design intention.

---

## 23. Concrete search-and-edit targets

Search the LaTeX source for the following terms and inspect each occurrence:

- "No existing"
- "existing replication"
- "smallest"
- "field-realistic"
- "field realistic"
- "equivalent"
- "by architecture"
- "verified"
- "complete implementation"
- "working scaffold"
- "Raft"
- "quorum"
- "ceil"
- "CRDT"
- "multi-primary"
- "mTLS"
- "WireGuard"
- "Rajant"
- "Android"
- "tablet"
- "promotion"
- "split brain"
- "single writer"
- "outbox"
- "idempot"
- "crash"
- "partition"

For each occurrence, decide whether the wording is supported by evidence. If not, revise.

---

## 24. Acceptance criteria

The final revision should satisfy these criteria:

1. The abstract accurately describes the scope of the prototype and evaluation.
2. The introduction frames the contribution as a domain-specific composition and trade-off, not a universal replication breakthrough.
3. Requirements are separated from assumptions and deployment constraints.
4. The data model distinguishes reference data, observations, command decisions, materialized views, and audit data.
5. The synchronization protocol states identifiers, idempotency, transaction boundaries, acknowledgements, and authoritative state.
6. Command promotion includes explicit discussion of epochs/fencing or clearly states that this is protocol design/future implementation.
7. Implementation status is presented in a precise table.
8. Evaluation claims are limited to the actual emulation/test environment.
9. The Raft comparison is labeled as contextual and the quorum formula is correct.
10. Measured results are not mixed with unmeasured architectural assertions without clear labels.
11. Formal verification is described as bounded model checking of an abstract invariant.
12. Security discussion includes threat assumptions and offline revocation limitations.
13. Figures and tables are readable and not misleading.
14. Limitations are explicit, precise, and aligned with the evidence.
15. The paper builds successfully after edits.

---

## 25. Expected Codex output

When done, Codex should provide:

1. A concise changelog listing modified files and major content changes.
2. The corrected Raft quorum wording and where it was changed.
3. A summary of claims that were narrowed or moved to limitations.
4. A note on whether tables were regenerated from data or only captions/prose were revised.
5. A LaTeX build result, including any warnings or failures.
6. Any repository evidence found for or against real mesh, WireGuard, mTLS, Android, crash-injection, and field-deployment claims.

