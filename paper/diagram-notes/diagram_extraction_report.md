# Diagram Extraction Report

## 1. Paper Map

### Abstract
- File: `paper/sections/00_abstract.tex`, lines 1-1.
- Purpose: frames the paper as an authority-aware, offline-first architecture and states the evaluated scope.
- Dense concepts: regional core, vehicle edges, durable outboxes, command-side journal, bounded manual promotion, model checking, Raft comparison.
- Existing labels: none.
- Overloaded paragraphs: the single abstract paragraph carries system design, evidence, exclusions, and trade-off claims. A compact scope diagram could reduce the burden on this paragraph.

### Section I - Introduction
- File: `paper/sections/01_introduction.tex`, lines 1-21.
- Purpose: motivates the operational problem, separates requirements from design choices, and lists contributions.
- Dense concepts: operational authority, durable tablet observations, command-local progress, Raft as contextual comparison.
- Existing labels: `sec:introduction`.
- Overloaded paragraphs: lines 7-11 explain connectivity, durable submission, requirements, and why consensus/CRDT patterns do not directly match the workflow.

### Section II - Problem Analysis
- File: `paper/sections/02_problem_analysis.tex`, lines 1-170.
- Purpose: combines operational setting, related-work gap, requirements, state taxonomy, and architecture rationale.
- Dense concepts: operational command authority, CRDT/local-first limits, consensus comparison, state-specific contracts, target-vs-evaluated path.
- Existing labels: `sec:problem-analysis`, `sec:requirements`, `tab:req-trace`, `sec:state-taxonomy`, `fig:state-contracts`, `fig:topology-scope`.
- Overloaded paragraphs: the related-work contrast and architecture consequence remain the densest parts, but the section now follows a problem-analysis sequence.

### Section IV - Synchronization Protocol
- File: `paper/sections/04_synchronization_protocol.tex`, lines 1-70.
- Purpose: defines bootstrap, tablet edit flow, protocol contract, partition behavior, promotion/fencing, and consistency guarantees.
- Dense concepts: enqueue/ack boundary, `client_event_id`, command-side `event_seq`, journal vs materialized state, replay/idempotency, strict promotion, missing durable epochs.
- Existing labels: `sec:sync`, `sec:protocol-contract`, `sec:promotion`.
- Overloaded paragraphs: lines 14-26 list field-edit steps in prose; lines 28-41 define the protocol contract; lines 43-57 define partition and promotion behavior.

### Section V - Implementation
- File: `paper/sections/05_implementation.tex`, lines 1-31.
- Purpose: maps the prototype, scaffolding, and evaluated paths.
- Dense concepts: service coverage, synthetic bootstrap/backfill, emulation plain HTTP, target authentication controls.
- Existing labels: `sec:implementation`.
- Overloaded paragraphs: line 6 and lines 8-29 carry the main status taxonomy; line 31 carries an important target-vs-emulation caveat.

### Section VI - Evaluation
- File: `paper/sections/06_evaluation.tex`, lines 1-285.
- Purpose: describes the emulation environment, measured scenarios, results, safety/model checks, Raft comparison, and limitations.
- Dense concepts: measured vs unmeasured paths, queue depths, WAN recovery timing, outbox polling, throughput lock bottleneck, formal-model bounds, Raft quorum comparison, limitations.
- Existing labels: `sec:evaluation`, `sec:validation`, `sec:eval-env`, `sec:eval-latency`, `tab:evaluation`, `sec:eval-throughput`, `sec:eval-safety`, `sec:eval-baseline`, `tab:baseline`, `sec:eval-limits`.
- Overloaded paragraphs: lines 8-28 define the evaluation substrate and data counts; lines 39-84 define measurement scope and caveats; lines 143-168 define formal-model scope; lines 184-233 define Raft comparison scope and quorum math; lines 258-285 list limitations.

### Section VII - Discussion
- File: `paper/sections/07_discussion.tex`, lines 1-30.
- Purpose: explains the design trade-off, security scope, limitations, and transferability.
- Dense concepts: CRDT unsuitability for command decisions, single-writer applies only to authority-bearing journal entries, offline revocation limits, stolen node assumptions.
- Existing labels: none.
- Overloaded paragraphs: lines 5-13 combine consistency, security, and threat-model caveats that would benefit from visual trust boundaries.

### Section VIII - Conclusion
- File: `paper/sections/08_conclusion.tex`, lines 1-5.
- Purpose: summarizes the contribution and remaining work.
- Dense concepts: command-side writer, durable forward submission, bounded abstract promotion model, no automatic multi-writer failover.
- Existing labels: none.
- Overloaded paragraphs: lines 3-5 summarize the full evidence boundary and future work.

## 2. Existing Figures and Tables

### `tab:req-trace`
- Source: `paper/sections/03_system_architecture.tex`, lines 19-35.
- Caption: traceability from adopted constraints to architectural consequences.
- Explains: R1-R5 and the design consequences used later.
- Status: keep, but a future diagram could visually connect R3/R5 to the single-writer and trust-boundary choices.
- Claim type: design rationale and requirements mapping, not measured data.

### `tab:state-taxonomy`
- Source: `paper/sections/03_system_architecture.tex`, lines 74-91.
- Caption: state classes and replication contracts.
- Explains: six state classes and their synchronization contracts.
- Status: strong candidate for replacement or visual compression as Candidate B; current table is accurate but dense.
- Claim type: implementation/design contract with explicit validation limits for audit events.

### `fig:topology`
- Source: `paper/sections/03_system_architecture.tex`, lines 97-133.
- Caption: three-tier deployment topology with core, command edge, responder edge, tablet, WAN, and mesh transit.
- Explains: target topology and role split.
- Status: should be replaced or split by Candidate A. Current figure is useful, but it risks blending target deployment components with the Docker/Python evaluation unless labels are made more explicit.
- Claim type: architecture design. The caption caveat at lines 128-132 states that physical network components were not evaluated.

### Implementation status prose
- Source: `paper/sections/05_implementation.tex`, lines 8-18.
- Explains: implemented, scaffolded, model-only, and evaluated/not-evaluated components.
- Status: table removed for page budget; keep prose guardrail or convert into Candidate H only if page budget allows.
- Claim type: implementation-status claims.

### `tab:evaluation`
- Source: `paper/sections/06_evaluation.tex`, lines 86-98 and generated rows in `paper/tables/tab_evaluation.tex`, lines 1-21.
- Caption: Phase 2 emulation measurements per scenario.
- Explains: bootstrap latency, field-edit propagation, WAN recovery, and throughput.
- Status: keep; Candidate H and Candidate E can reference selected values without duplicating the full table.
- Claim type: measured emulation data.

### Recovery plot
- Source: generated file `paper/figures/fig_recovery.pdf`; not included in the submitted manuscript after page-budget trimming.
- Explains: recovery-time distribution for 1 s, 10 s, and 60 s WAN partitions.
- Status: do not re-add unless page budget allows; Candidate E can add mechanism context around the tabulated/prose result.
- Claim type: measured emulation data, limited to command-core WAN isolation.

### `tab:baseline`
- Source: `paper/sections/06_evaluation.tex`, lines 235-253 and generated rows in `paper/tables/tab_baseline.tex`, lines 1-13.
- Caption: selected Rescue OIS and Raft comparison points.
- Explains: propagation, follower catch-up, and quorum-loss comparison.
- Status: keep, but Candidate G should visually mark that the comparison is contextual and not workflow-equivalent.
- Claim type: mixed measured emulation data and analytic quorum consequence.

## 3. Hard-to-Understand Concepts

### Three-tier deployment model
- References: `paper/sections/03_system_architecture.tex`, lines 53-67 and 97-133; `edge/docker-compose.yml`, lines 13-87; `core/docker-compose.yml`, lines 12-91; `docs/deployment/vehicle-edge-setup.md`, lines 1-22.
- Why hard: the same vehicle hardware can be command or responder, while tablets are leaf clients and the core has separate service responsibilities.
- Likely misunderstanding: readers may see "edge" as homogeneous and miss the command/responder role split.
- Diagram role: Candidate A should support prose and replace the current topology figure if it can show role, network, and evaluation scope without clutter.

### Target deployment vs evaluated emulation
- References: `paper/sections/00_abstract.tex`, line 1; `paper/sections/05_implementation.tex`, lines 8-31; `paper/sections/06_evaluation.tex`, lines 8-19; `tablet/README.md`, lines 1-29; `edge/nginx/nginx.conf`, lines 33-43.
- Why hard: the repo contains real scaffolding for Rajant, WireGuard, mTLS, and Android, but the reported results use Docker Compose, plain HTTP, and a Python tablet stub.
- Likely misunderstanding: reviewers could infer that radio, VPN, TLS, or Android overheads were measured.
- Diagram role: Candidate H should prevent overclaiming by separating target-only, implemented, and evaluated paths.

### State taxonomy and consistency contracts
- References: `paper/sections/03_system_architecture.tex`, lines 69-91; `paper/sections/07_discussion.tex`, lines 5-7; `docs/architecture/sync-protocol.md`, lines 5-52.
- Why hard: the system does not apply one consistency model to all state.
- Likely misunderstanding: readers may assume the whole architecture is single-writer or, conversely, all data is eventually merged.
- Diagram role: Candidate B can replace part of the table and make the per-state contract explicit.

### Responder outbox lifecycle
- References: `paper/sections/04_synchronization_protocol.tex`, lines 14-26 and 28-41; `edge/ops-api/src/routes/api.py`, lines 34-61; `edge/syncd/src/outbox.py`, lines 11-49; `edge/syncd/src/push.py`, lines 1-90; `edge/db/migrations/002_outbox.sql`, lines 1-17.
- Why hard: ACK semantics cross tablet API, durable outbox, responder push, command acceptance, and duplicate suppression.
- Likely misunderstanding: an ACK to the tablet could be mistaken for command commit.
- Diagram role: Candidate C should show the durable boundaries and distinguish local acceptance from command ack.

### Command journal sequencing and materialized state
- References: `paper/sections/04_synchronization_protocol.tex`, lines 28-41 and 59-70; `edge/syncd/src/accept.py`, lines 49-129; `edge/db/migrations/003_incident_journal.sql`, lines 18-44; `docs/adr/0001-single-incident-writer.md`, lines 13-31.
- Why hard: `event_seq` allocation, idempotency, append-only journal, and derived state are described across prose, code, and migrations.
- Likely misunderstanding: materialized state might appear authoritative rather than derived.
- Diagram role: Candidate D should identify the authoritative journal and the rebuildable derived state.

### Partition and recovery behavior
- References: `paper/sections/04_synchronization_protocol.tex`, lines 43-50; `paper/sections/06_evaluation.tex`, lines 57-84; `scripts/inject-partition.sh`, lines 1-68; `scripts/evaluate-pilot.py`, lines 174-225.
- Why hard: responder local enqueue, command-local commits, and command-to-core catch-up have different failure behavior.
- Likely misunderstanding: WAN recovery measurements may be read as mesh recovery or all-partition recovery.
- Diagram role: Candidate E can show which path is partitioned and what continues.

### Promotion, epochs, and fencing
- References: `paper/sections/04_synchronization_protocol.tex`, lines 52-57; `paper/sections/06_evaluation.tex`, lines 143-168; `formal/tla/RescueOIS.tla`, lines 114-140 and 173-199; `scripts/promote-responder.sh`, lines 1-43; `docs/runbooks/command-failover.md`, lines 1-30; `docs/adr/0004-promotion-authority-model.md`, lines 1-40.
- Why hard: the desired strict-promotion rule exists in the model and procedure, but durable epochs and stale-epoch rejection are not implemented in services.
- Likely misunderstanding: readers may infer production-grade autonomous failover or durable epoch fencing.
- Diagram role: Candidate F should show strict and weak paths, with weak promotion explicitly unsafe.

### Raft comparison scope
- References: `paper/sections/02_related_work.tex`, lines 8-10; `paper/sections/06_evaluation.tex`, lines 184-233 and 235-253; `scripts/evaluate-raft-baseline.py`, lines 1-8, 137-224, and 227-263.
- Why hard: the comparison is intentionally selected and contextual, not an end-to-end replacement benchmark.
- Likely misunderstanding: reviewers may see the Raft baseline as a strawman or as a full alternative implementation.
- Diagram role: Candidate G should show where Raft majority progress and command-local progress differ.

### Formal model boundaries
- References: `paper/sections/06_evaluation.tex`, lines 143-168; `formal/tla/RescueOIS.tla`, lines 20-43, 92-98, 114-140, and 173-199; `formal/tla/README.md`, lines 7-13 and 54-57; `formal/python/tests/test_no_two_writers.py`, lines 1-8 and 74-96.
- Why hard: the model validates a bounded abstract safety property, not the whole implementation.
- Likely misunderstanding: bounded model checking could be overread as crash, fsync, certificate, or transport verification.
- Diagram role: Candidate J should show included and excluded state.

### Security and trust boundaries
- References: `paper/sections/03_system_architecture.tex`, lines 14-16, 65-67, and 93-95; `paper/sections/07_discussion.tex`, lines 9-13; `docs/architecture/network-topology.md`, lines 16-30 and 44-60; `docs/adr/0005-revocation-under-partition.md`, lines 7-21; `edge/nginx/nginx.conf`, lines 33-43.
- Why hard: the design depends on identity integration and network segmentation, while the emulation does not evaluate those controls.
- Likely misunderstanding: diagrams with locks could imply measured security behavior.
- Diagram role: Candidate I should show trust boundaries as target-design assumptions and call out revocation delay.

### Crash-consistency gaps
- References: `paper/sections/05_implementation.tex`, lines 8-29; `paper/sections/06_evaluation.tex`, lines 125-141 and 258-285; `formal/python/tests/test_against_real.py`, lines 15-18 and 53-70.
- Why hard: duplicate replay and smoke tests exist, but crash injection at every durable boundary does not.
- Likely misunderstanding: "durable outbox" could be read as fully crash-validated end to end.
- Diagram role: Candidate H or J should mark crash validation as incomplete.

## 4. Candidate Diagrams

### A. System Boundary and Deployment Layers

- Priority: High.
- Proposed type: layered architecture diagram.
- Target section: Problem Analysis, `paper/sections/02_problem_analysis.tex`.
- Replace or support: replace existing `fig:topology` or split it into architecture and evaluation-scope figures.
- Reader problem solved: makes core, command edge, responder edge, tablet, WAN, mesh, and emulation boundaries obvious.
- Entities to show: regional core, command K430, responder K430s, field tablets, Docker bridge emulation, Rajant mesh, WireGuard overlay, Nginx/mTLS, Python tablet stub.
- Flows or relationships to show: tablet-to-local-K430 HTTPS, responder-to-command event forwarding, command-to-core backhaul, core-to-edge baseline sync, target-only network paths.
- Required labels: `regional core`, `command edge`, `responder edge`, `tablet leaf client`, `target deployment`, `evaluated Docker path`, `not measured`.
- Data/results to include: none, or a small badge saying "Docker Compose, N=30 cells" from `paper/sections/06_evaluation.tex`, lines 8-19.
- Assumptions/caveats to show visually: Rajant, WireGuard, mTLS, and Android are target/scaffolded, not evaluated.
- Source references: `paper/sections/02_problem_analysis.tex`; `paper/sections/06_evaluation.tex`, lines 8-19; `docs/deployment/vehicle-edge-setup.md`, lines 1-22.
- Risk if drawn badly: implies field-radio, VPN, TLS, or Android performance was measured.
- Suggested caption idea: "Target deployment layers and the narrower Docker/Python path used for the reported emulation."

### B. State Taxonomy and Consistency Contract

- Priority: High.
- Proposed type: matrix or layered contract diagram.
- Target section: Problem Analysis, `paper/sections/02_problem_analysis.tex`.
- Replace or support: replace or compress `tab:state-taxonomy`.
- Reader problem solved: prevents the false impression that one consistency model applies to all data.
- Entities to show: master/reference data, immutable artifacts, field observations, command decisions, materialized state, audit events.
- Flows or relationships to show: core-to-edge replication, package validation, durable outbox forwarding, single command writer, rebuild from journal, eventual audit forwarding.
- Required labels: `one-way replication`, `manifest/hash validation`, `append-only outbox`, `single-writer journal`, `derived/rebuildable`, `eventual audit forwarding`.
- Data/results to include: none.
- Assumptions/caveats to show visually: audit forwarding validation remains incomplete; single-writer applies only to authority-bearing journal entries.
- Source references: `paper/sections/02_problem_analysis.tex`; `paper/sections/07_discussion.tex`, lines 5-7; `docs/architecture/sync-protocol.md`, lines 5-52.
- Risk if drawn badly: overgeneralizes the command-writer rule.
- Suggested caption idea: "State classes use different synchronization contracts; only command decisions require a single authoritative sequencer."

### C. Responder Outbox Sequence Diagram

- Priority: High.
- Proposed type: swimlane sequence diagram.
- Target section: Synchronization Protocol, `paper/sections/04_synchronization_protocol.tex`.
- Replace or support: replace dense protocol-step prose.
- Reader problem solved: makes the local ACK, command commit, retry, and duplicate handling boundaries explicit.
- Entities to show: tablet/Python stub, responder `ops-api`, responder Postgres `outbox.device_outbox`, responder `syncd.push`, command `syncd.accept`, command Postgres `incident.journal`.
- Flows or relationships to show: `POST /api/events`, local insert, batch fetch, `POST /accept/event-batch`, idempotency check, `event_seq` allocation, journal insert, ack, `forwarded_at` update, retry.
- Required labels: `client_event_id`, `forwarded_at`, `ack_seq`, `event_seq`, `local accepted`, `command ack`.
- Data/results to include: `POLL_INTERVAL_S=0.25`, `BATCH_SIZE=50` from `edge/syncd/src/push.py`, lines 22-23; queue-depth scenarios 1, 10, 100 from `scripts/evaluate-pilot.py`, lines 125-171.
- Assumptions/caveats to show visually: crash injection at every durable boundary is not validated.
- Source references: `edge/ops-api/src/routes/api.py`, lines 34-61; `edge/syncd/src/outbox.py`, lines 11-49; `edge/syncd/src/push.py`, lines 1-90; `edge/syncd/src/accept.py`, lines 49-129.
- Risk if drawn badly: suggests the tablet ACK equals command commit.
- Suggested caption idea: "Responder submissions are locally durable first, then forwarded at least once until the command journal acknowledges them."

### D. Command Journal and Materialized View Pipeline

- Priority: High.
- Proposed type: data-flow diagram.
- Target section: Synchronization Protocol or Evaluation Safety, `paper/sections/04_synchronization_protocol.tex` or `paper/sections/06_evaluation.tex`.
- Replace or support: support prose on journal authority and derived state.
- Reader problem solved: clarifies why the journal is authoritative and materialized state is rebuildable.
- Entities to show: accepted events, command transaction, `incident.journal`, `incident.state`, core `master.incident_events`, `sync.state` cursor.
- Flows or relationships to show: sequence allocation under row lock, journal append, state update, command-to-core batch, core idempotent ingest, replay/rebuild path.
- Required labels: `FOR UPDATE`, `UNIQUE (incident_id, event_seq)`, `UNIQUE client_event_id`, `last_acked_seq_to_core`.
- Data/results to include: throughput median 156.7 events/s and p95 160.4 events/s from `paper/tables/tab_evaluation.tex`, lines 19-20, if this diagram is placed near throughput.
- Assumptions/caveats to show visually: `FOR UPDATE` is a measured bottleneck, not a distributed consensus mechanism.
- Source references: `edge/syncd/src/accept.py`, lines 77-127; `edge/syncd/src/forward.py`, lines 30-111; `core/sync-api/src/routes/sync.py`, lines 78-126; migrations in `edge/db/migrations/003_incident_journal.sql`, lines 18-44, and `004_idempotency_and_sync_state.sql`, lines 45-77.
- Risk if drawn badly: makes materialized state look like the source of truth.
- Suggested caption idea: "The command transaction appends the authoritative journal and updates derived incident state; backhaul to core is idempotent and cursor-based."

### E. Partition and Recovery Timeline

- Priority: High.
- Proposed type: timeline.
- Target section: Evaluation, `paper/sections/06_evaluation.tex`.
- Replace or support: support WAN recovery prose and `tab:evaluation`.
- Reader problem solved: shows what continues during command-core WAN isolation and what resumes after reconnect.
- Entities to show: responder outbox, command journal, core backhaul, partition window, reconnect, replay.
- Flows or relationships to show: normal operation, WAN disconnect, local enqueue, command-local commit, core-forward pause, reconnect, cursor-based catch-up.
- Required labels: `WAN partition`, `mesh partition not measured here`, `20 events`, `partition_s=1/10/60`, `recovery_to_core_ms`.
- Data/results to include: 1 s partition median/p95 2073/2227 ms, 10 s 5793/5922 ms, 60 s 706/2727 ms from `paper/tables/tab_evaluation.tex`, lines 14-17.
- Assumptions/caveats to show visually: only command-core WAN isolation was measured; responder isolation, crashes, restarts, and physical radio behavior were not measured.
- Source references: `scripts/evaluate-pilot.py`, lines 174-225; `scripts/inject-partition.sh`, lines 1-68; `paper/sections/06_evaluation.tex`, lines 57-84.
- Risk if drawn badly: suggests a general network-recovery law or physical radio-performance result.
- Suggested caption idea: "WAN recovery measures command-to-core catch-up after Docker network isolation, not radio mesh recovery."

### F. Promotion, Epochs, and Fencing

- Priority: High.
- Proposed type: state machine or decision tree.
- Target section: Synchronization Protocol, `paper/sections/04_synchronization_protocol.tex`, and Evaluation Safety, `paper/sections/06_evaluation.tex`.
- Replace or support: support promotion and model-checking prose.
- Reader problem solved: makes the safety/availability trade-off explicit.
- Entities to show: old command, candidate responder, operator, promotion record/token, epoch, stale command rejoin.
- Flows or relationships to show: strict promotion requires current command reachable/fenced, weak promotion allows split brain, stale command must rejoin as responder or be rejected.
- Required labels: `StrictPromotion=TRUE`, `StrictPromotion=FALSE`, `SingleAuthority`, `NoForkedJournal`, `stale epoch rejection not implemented`.
- Data/results to include: weak `SingleAuthority` counterexample depth 3 and weak `NoForkedJournal` counterexample depth 5 from `formal/tla/README.md`, lines 21-27 and 54-57.
- Assumptions/caveats to show visually: durable `command_epoch` and stale-epoch rejection are design/model requirements, not service implementation in the evaluated path.
- Source references: `formal/tla/RescueOIS.tla`, lines 114-140 and 173-199; `paper/sections/04_synchronization_protocol.tex`, lines 52-57; `docs/runbooks/command-failover.md`, lines 1-30; `docs/adr/0004-promotion-authority-model.md`, lines 15-35.
- Risk if drawn badly: implies autonomous failover or implemented epoch fencing.
- Suggested caption idea: "Promotion is safe only under strict fencing; the weak path admits split-brain counterexamples in the abstract model."

### G. Raft Comparison Scope

- Priority: Medium.
- Proposed type: side-by-side comparison diagram.
- Target section: Evaluation baseline, `paper/sections/06_evaluation.tex`.
- Replace or support: support Raft comparison prose and `tab:baseline`.
- Reader problem solved: reduces the chance of a strawman-reading of the baseline.
- Entities to show: 3-node Raft cluster, leader, voters, command edge, responders, command-local journal.
- Flows or relationships to show: Raft majority requirement, follower isolation, quorum loss, Rescue OIS command-local progress when command storage is available, command-node failure trade-off.
- Required labels: `contextual comparison`, `not workflow-equivalent`, `majority required`, `single command authority`.
- Data/results to include: Rescue OIS q10 946.3/1018.5 ms vs Raft q10 10.5/18.1 ms; Raft follower catch-up 4109/5109 ms; Raft quorum loss 0 percent writes succeeded from `paper/tables/tab_baseline.tex`, lines 1-13.
- Assumptions/caveats to show visually: both designs have failure modes when the authority/leader/command node is unavailable.
- Source references: `paper/sections/06_evaluation.tex`, lines 184-233; `scripts/evaluate-raft-baseline.py`, lines 137-263.
- Risk if drawn badly: implies Raft and Rescue OIS are substitutable end-to-end systems.
- Suggested caption idea: "The Raft baseline illustrates quorum-progress behavior; it is not a workflow-equivalent replacement for the authority-aware protocol."

### H. Evaluation Coverage Map

- Priority: Highest.
- Proposed type: coverage matrix.
- Target section: Implementation or Evaluation, `paper/sections/05_implementation.tex` or `paper/sections/06_evaluation.tex`.
- Replace or support: support implementation status prose and evaluation environment prose.
- Reader problem solved: makes evidence boundaries readable at a glance.
- Entities to show: target components, implemented prototype components, Docker-evaluated components, model-only components, not-evaluated components.
- Flows or relationships to show: target vs prototype vs evaluated/emulated path.
- Required labels: `target design`, `implemented`, `evaluated in Docker`, `scaffold only`, `model only`, `not evaluated`.
- Data/results to include: primary metrics 390 records, Raft metrics 160 records, 30 skipped promotion records from `paper/sections/06_evaluation.tex`, lines 21-28.
- Assumptions/caveats to show visually: no physical Rajant, no WireGuard/mTLS overhead, no Android tablet path, no crash injection at all durable boundaries.
- Source references: `paper/sections/05_implementation.tex`, lines 8-31; `paper/sections/06_evaluation.tex`, lines 8-28 and 258-285.
- Risk if drawn badly: hides limitations or turns scaffolded items into validated claims.
- Suggested caption idea: "Coverage map separating target design, prototype implementation, emulated measurements, and model-only safety evidence."

### I. Threat Model and Trust Boundaries

- Priority: Medium.
- Proposed type: trust-boundary diagram.
- Target section: Discussion, `paper/sections/07_discussion.tex`.
- Replace or support: support security scope prose.
- Reader problem solved: turns a list of security technologies into a scoped model.
- Entities to show: organizational CA/IdP, core, command edge, responder edge, tablets, RUTX50 VLANs, WireGuard overlay, Rajant transit, audit path.
- Flows or relationships to show: certificate-derived identity, local tablet reachability, K430-to-core overlay, K430-to-K430 mesh transit, CRL/OCSP refresh on reconnect.
- Required labels: `target deployment only`, `offline revocation delay`, `backend trusts reverse-proxy identity`, `not Byzantine-fault-tolerant`.
- Data/results to include: none.
- Assumptions/caveats to show visually: mTLS and revocation behavior are not exercised by the emulation.
- Source references: `paper/sections/07_discussion.tex`, lines 9-13; `docs/architecture/network-topology.md`, lines 44-60; `docs/adr/0005-revocation-under-partition.md`, lines 7-21; `edge/nginx/nginx.conf`, lines 33-43.
- Risk if drawn badly: lock icons imply evaluated or production-complete security.
- Suggested caption idea: "Trust boundaries in the target deployment; the emulation uses plain HTTP and synthetic identities."

### J. Formal Model Scope

- Priority: Medium.
- Proposed type: scope boundary diagram.
- Target section: Evaluation Safety, `paper/sections/06_evaluation.tex`.
- Replace or support: support model-checking prose.
- Reader problem solved: shows exactly what the TLA+/Hypothesis checks cover.
- Entities to show: vehicles, role, authority, partition, journal, cursor, `client_event_id`, invariants, excluded implementation concerns.
- Flows or relationships to show: commit, promote, partition, heal, strict vs weak promotion.
- Required labels: `bounded abstract model`, `SingleAuthority`, `NoForkedJournal`, `LocalIdempotency`, `SingleCommand`, `excluded: fsync/certs/crash/transport`.
- Data/results to include: TLA constants and invariants from `formal/tla/RescueOIS.tla`, lines 20-43 and 173-199; Hypothesis 2000 examples and 50 steps from `formal/python/tests/test_no_two_writers.py`, lines 74-75.
- Assumptions/caveats to show visually: does not validate production fencing implementation or crash safety.
- Source references: `formal/tla/RescueOIS.tla`, lines 20-43, 92-98, 114-140, and 173-199; `formal/tla/README.md`, lines 54-57; `formal/python/tests/test_no_two_writers.py`, lines 74-96.
- Risk if drawn badly: makes formal evidence appear broader than it is.
- Suggested caption idea: "The formal checks cover single-writer promotion safety in an abstract bounded model, not the full deployment stack."

## 5. Evidence and Data Inventory

| Evidence item | Value | Type | Source | Diagram use |
|---|---:|---|---|---|
| Evaluation environment | one core, one command edge, three responder edges, Docker bridge | configured/measured setup | `paper/sections/06_evaluation.tex`, lines 8-19 | Candidate A/H |
| Runs per cell | 30 | configured | `scripts/evaluate-pilot.py`, lines 33-37 | Candidate H/E |
| Primary metrics records | 390 records plus 30 skipped promotion records | measured/output count | `paper/sections/06_evaluation.tex`, lines 21-28 | Candidate H |
| Raft metrics records | 160 records | measured/output count | `paper/sections/06_evaluation.tex`, lines 21-28 | Candidate G/H |
| Bootstrap AOI sizes | 10, 50, 200, 1000 polygons | configured | `scripts/evaluate-pilot.py`, lines 98-122 | Candidate H |
| Bootstrap medians/p95 | 7.24/9.79, 3.76/4.25, 2.83/4.28, 9.88/19.24 ms | measured | `paper/tables/tab_evaluation.tex`, lines 3-7 | Candidate H if needed |
| Field edit queue depths | 1, 10, 100 | configured | `scripts/evaluate-pilot.py`, lines 125-171 | Candidate C/H |
| Field edit medians/p95 | 947.9/986.9, 946.3/1018.5, 1224.0/1314.6 ms | measured | `paper/tables/tab_evaluation.tex`, lines 9-12 | Candidate C/H |
| WAN partition durations | 1, 10, 60 s | configured | `scripts/evaluate-pilot.py`, lines 174-225 | Candidate E/H |
| WAN recovery medians/p95 | 2073/2227, 5793/5922, 706/2727 ms | measured | `paper/tables/tab_evaluation.tex`, lines 14-17 | Candidate E |
| Throughput workload | 1000 events/run, run 0 warmup excluded | configured | `scripts/evaluate-pilot.py`, lines 228-283 | Candidate D/H |
| Throughput median/p95 | 156.7/160.4 events/s, 29 runs | measured | `paper/tables/tab_evaluation.tex`, lines 19-20 | Candidate D/H |
| Duplicate replay workload | 50 unique IDs, 5 replays each | configured/measured | `scripts/evaluate-pilot.py`, lines 286-330 | Candidate C/J |
| Promotion measurement | skipped, interactive script required | unsupported in harness | `scripts/evaluate-pilot.py`, lines 333-346 | Candidate F/H |
| Responder push poll interval | 0.25 s | configured | `edge/syncd/src/push.py`, lines 22-23 | Candidate C |
| Responder push batch size | 50 events | configured | `edge/syncd/src/push.py`, lines 22-23 | Candidate C |
| Command-to-core forward poll interval | 1.0 s | configured | `edge/syncd/src/forward.py`, lines 22-23 | Candidate D/E |
| Command-to-core batch size | 200 events | configured | `edge/syncd/src/forward.py`, lines 22-23 | Candidate D/E |
| Raft cluster | 3 nodes | configured | `scripts/evaluate-raft-baseline.py`, lines 23-42 | Candidate G |
| Raft propagation queue depths | 1, 10, 100 | configured | `scripts/evaluate-raft-baseline.py`, lines 137-162 | Candidate G |
| Raft follower catch-up partitions | 10 s, 60 s, 1 follower isolated | configured/measured | `scripts/evaluate-raft-baseline.py`, lines 165-224 | Candidate G |
| Raft quorum loss | 2 of 3 non-leader nodes isolated, max 10 runs | configured/measured | `scripts/evaluate-raft-baseline.py`, lines 227-263 | Candidate G |
| TLA vehicles/client IDs/journal bound | constants `Vehicles`, `ClientIds`, `MaxJournal` | modeled | `formal/tla/RescueOIS.tla`, lines 20-25 | Candidate J |
| TLA invariants | `SingleAuthority`, `NoForkedJournal`, `LocalIdempotency`, `SingleCommand` | modeled | `formal/tla/RescueOIS.tla`, lines 173-199 | Candidate F/J |
| Weak promotion counterexamples | depth 3 and depth 5 | modeled result | `formal/tla/README.md`, lines 54-57 | Candidate F/J |
| Hypothesis strict machine | 2000 examples, 50 steps | tested/model-based | `formal/python/tests/test_no_two_writers.py`, lines 74-75 | Candidate J |
| Host CPU/RAM/OS/Docker/TLS/VPN metadata | missing from repo | missing | `paper/sections/06_evaluation.tex`, lines 21-28 | Candidate H caveat |

## 6. Text Replacement Opportunities

### TRO-1 - Deployment layers and emulation boundary
- File: `paper/sections/03_system_architecture.tex`, lines 53-67 and 93-133.
- Current topic: roles, tablet boundary, target network segmentation, and topology.
- Approximate current word count: 390 plus figure caption.
- Proposed diagram candidate: A.
- Text that can be shortened: role descriptions and target-vs-emulation caveats if the figure labels the three evidence categories.
- Caveat that must remain: physical router, mesh, VPN, and mTLS behavior were not evaluated.
- Overclaiming risk reduction: high.

### TRO-2 - State taxonomy
- File: `paper/sections/03_system_architecture.tex`, lines 69-91.
- Current topic: state classes and replication contracts.
- Approximate current word count: 230 plus table.
- Proposed diagram candidate: B.
- Text that can be shortened: explanatory lead-in and repeated contract language.
- Caveat that must remain: single-writer applies only to authority-bearing incident-journal entries.
- Overclaiming risk reduction: high.

### TRO-3 - Outbox ACK semantics
- File: `paper/sections/04_synchronization_protocol.tex`, lines 14-41.
- Current topic: field-edit flow and protocol contract.
- Approximate current word count: 520.
- Proposed diagram candidate: C.
- Text that can be shortened: ordered step list and ACK/idempotency explanation.
- Caveat that must remain: `command_epoch` is not stored in evaluated services.
- Overclaiming risk reduction: high.

### TRO-4 - Partition behavior
- File: `paper/sections/04_synchronization_protocol.tex`, lines 43-50 and `paper/sections/06_evaluation.tex`, lines 57-84.
- Current topic: partition behavior and WAN recovery measurement scope.
- Approximate current word count: 470.
- Proposed diagram candidate: E.
- Text that can be shortened: repeated explanation of what continues and what waits.
- Caveat that must remain: measured WAN isolation is command-core only.
- Overclaiming risk reduction: high.

### TRO-5 - Promotion safety
- File: `paper/sections/04_synchronization_protocol.tex`, lines 52-57 and `paper/sections/06_evaluation.tex`, lines 143-168.
- Current topic: strict promotion and formal model boundaries.
- Approximate current word count: 520.
- Proposed diagram candidate: F or J.
- Text that can be shortened: weak-vs-strict promotion narrative.
- Caveat that must remain: durable epoch/fencing implementation is absent from services.
- Overclaiming risk reduction: high.

### TRO-6 - Implementation/evaluation coverage
- File: `paper/sections/05_implementation.tex`, lines 8-31 and `paper/sections/06_evaluation.tex`, lines 8-28.
- Current topic: what exists, what was evaluated, and what remains scaffolding.
- Approximate current word count: 470 plus table.
- Proposed diagram candidate: H.
- Text that can be shortened: implementation-status prose around the table.
- Caveat that must remain: current traffic uses plain HTTP on Docker bridge with synthetic identities.
- Overclaiming risk reduction: very high.

### TRO-7 - Raft comparison
- File: `paper/sections/06_evaluation.tex`, lines 184-233.
- Current topic: why Raft is included and what the selected comparison means.
- Approximate current word count: 700.
- Proposed diagram candidate: G.
- Text that can be shortened: majority-vs-command-local progress explanation.
- Caveat that must remain: comparison is contextual, not workflow-equivalent.
- Overclaiming risk reduction: high.

### TRO-8 - Threat model
- File: `paper/sections/07_discussion.tex`, lines 9-13.
- Current topic: identity assumptions, mTLS-derived identity, revocation, stolen devices, and non-Byzantine scope.
- Approximate current word count: 250.
- Proposed diagram candidate: I.
- Text that can be shortened: network/trust boundary enumeration.
- Caveat that must remain: offline revocation and compromised-command behavior are not solved by the prototype.
- Overclaiming risk reduction: medium.

## 7. Visual Vocabulary

- Canonical actor names: `regional core`, `command edge`, `responder edge`, `field tablet`, `operator`, `organizational CA/IdP`.
- Canonical service names: `ops-api`, `syncd.push`, `syncd.accept`, `syncd.forward`, `sync-api`, `audit-api`, `package-cache`, `Nginx`.
- Canonical stores: `outbox.device_outbox`, `incident.journal`, `incident.state`, `sync.state`, `master.incident_events`, `package cache`, `tablet local DB`.
- Arrow labels: `bootstrap`, `baseline sync`, `POST /api/events`, `batch forward`, `ACK last_acked_seq`, `journal backhaul`, `audit forward`, `CRL/OCSP refresh`.
- Line styles: solid for evaluated/emulated paths; dashed for target deployment paths not measured; dotted for scaffolded or future integration; double line for formal/model-only evidence.
- Boundary styles: thick outer boundary for target deployment; shaded or bracketed inset for evaluated Docker path; trust boundary as a labeled perimeter rather than decorative lock icons.
- Authority markers: thick border or crown-like text label `authoritative` on `incident.journal`; avoid implying authority for `incident.state`.
- Derived-state markers: lighter border and label `derived/rebuildable` on materialized state.
- Evidence badges: `measured`, `configured`, `modeled`, `analytic`, `missing from repo`, `not evaluated`.
- Terms to avoid in captions unless carefully qualified: production deployment claims, field-evaluation claims, broad security claims, full implementation proof claims, autonomous failover claims, physical radio-performance claims, absolute data-loss guarantees, and Byzantine-fault-tolerance claims.

## 8. Claim-Safety Notes

- Do not imply a real field deployment was evaluated. The reported evaluation uses Docker Compose emulation (`paper/sections/06_evaluation.tex`, lines 8-19).
- Do not imply Rajant radio behavior was measured. Rajant appears as target deployment/design notes (`infra/rajant/README.md`, lines 1-21).
- Do not imply WireGuard or mTLS overhead was measured. These are target/scaffolded controls in `paper/sections/05_implementation.tex`, lines 23-31, and Nginx/WireGuard templates.
- Do not imply the Android tablet path was evaluated. The paper says the Python stub was used and Android was scaffold-only (`paper/sections/05_implementation.tex`, lines 23-24).
- Do not imply promotion latency was measured by the main harness. It records skipped promotion rows (`scripts/evaluate-pilot.py`, lines 333-346).
- Do not imply durable epoch fencing exists in evaluated services. The paper says `command_epoch` is not stored and stale-epoch rejection is not implemented (`paper/sections/04_synchronization_protocol.tex`, lines 52-57).
- Do not imply crash safety at every durable boundary. Duplicate replay and smoke tests exist, but crash injection remains incomplete (`paper/sections/06_evaluation.tex`, lines 125-141 and 258-285).
- Do not imply Raft is a workflow-equivalent implementation. It is a selected contextual comparison (`paper/sections/06_evaluation.tex`, lines 184-206).
- Do not imply offline revocation is instantaneous. ADR-0005 states revocation propagation requires WAN connectivity (`docs/adr/0005-revocation-under-partition.md`, lines 7-21).
- Do not imply Byzantine tolerance or compromised-command safety. Discussion excludes Byzantine command behavior and compromised CA scenarios (`paper/sections/07_discussion.tex`, lines 9-13).

## 9. Recommended Diagram Priority

1. Candidate H - Evaluation Coverage Map. Highest value for review defensibility; directly prevents overclaiming.
2. Candidate C - Responder Outbox Sequence Diagram. High value for understanding ACK/idempotency semantics.
3. Candidate A - System Boundary and Deployment Layers. Replaces/splits existing topology figure and clarifies target vs evaluation.
4. Candidate F - Promotion, Epochs, and Fencing. Essential for safety claims and for avoiding automatic-failover interpretations.
5. Candidate B - State Taxonomy and Consistency Contract. Compresses a dense table and clarifies consistency boundaries.
6. Candidate E - Partition and Recovery Timeline. Helps connect the WAN recovery result to the mechanism.
7. Candidate J - Formal Model Scope. Important guardrail, especially near model-checking claims.
8. Candidate G - Raft Comparison Scope. Useful if space permits near the baseline table.
9. Candidate I - Threat Model and Trust Boundaries. Useful for discussion, but should not crowd the main protocol figures.
10. Candidate D - Command Journal and Materialized View Pipeline. Valuable, but parts overlap with Candidate C and B; include if the paper has room or merge into C.

## 10. Open Questions for Author

1. Should the paper replace `fig:topology` with a combined target/evaluation boundary figure, or keep `fig:topology` and add a separate evaluation coverage map?
2. Is the future design for durable `command_epoch` intended to live in `incident.journal`, a separate authority table, or an external signed promotion record?
3. Should ADR-0004's promotion token model be treated as target design in the paper, or remain out of scope because it is only `Proposed`?
4. Can the author provide host CPU, RAM, OS, Docker version, and TLS/VPN-disabled metadata for the evaluation environment?
5. Should Candidate B replace `tab:state-taxonomy`, or should the table remain for precision and the diagram only support it?
6. Is there a preferred notation for target-only security controls so reviewers do not read lock icons as measured security?
7. Should the Raft comparison diagram include only the quorum-loss case, or also the lower propagation latency result to make the trade-off balanced?
8. Are there generated logs for the TLC runs that can be cited directly, or should the paper continue citing `formal/tla/README.md` and configs?
9. Should duplicate-replay results appear in a diagram, or remain prose/table-only because they are binary safety checks?
10. Are mesh partitions between responder and command planned for a future evaluation pass, and if so should Candidate E leave a placeholder lane for them?
