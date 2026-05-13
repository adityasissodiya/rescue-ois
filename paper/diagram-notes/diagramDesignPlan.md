# Diagram Design Plan for Paper Revision

Use this file after `diagram_facts.yaml` and `diagram_extraction_report.md` have been generated. The goal is to turn hard-to-parse protocol, evaluation-scope, and safety text into a small set of precise diagrams that make the paper easier to read without overstating the evidence.

The paper is currently 11 pages, so do not add every possible figure. Prefer 5-6 high-value figures, and merge related concepts where possible. The diagrams should help reviewers understand the architecture, the data contracts, the outbox protocol, the promotion/fencing trade-off, and the evaluation boundary.

## Non-negotiable claim-safety rules

Do not draw any figure that implies evidence the repository does not support.

Specifically:

- Do not imply a real field deployment was evaluated.
- Do not imply Rajant physical-mesh behavior was measured.
- Do not imply WireGuard or mTLS overhead was measured.
- Do not imply the Android tablet path was evaluated; the reported evaluation uses a Python stub.
- Do not imply crash safety was fully validated at every durable boundary.
- Do not imply durable `command_epoch` storage or stale-epoch rejection exists in the evaluated services.
- Do not imply promotion latency was measured by the main evaluation harness.
- Do not imply the Raft comparison is workflow-equivalent.
- Do not imply offline revocation is instantaneous.
- Do not imply Byzantine tolerance or compromised-command safety.

Every diagram that contains target-only elements must visibly distinguish them from measured/emulated elements.

## Recommended figure set

Implement the following figures in this order of priority:

1. **Evaluation Coverage Map** — highest value for reviewer defensibility.
2. **Evidence-Aware Topology** — replace or split the current topology figure.
3. **Responder Outbox Sequence Diagram** — clarify ACK, retry, and idempotency semantics.
4. **Promotion/Fencing Decision Diagram** — clarify the single-writer safety trade-off.
5. **State Taxonomy and Consistency Contract** — compress the dense state-class table.
6. **Partition and Recovery Timeline** — clarify what the WAN recovery experiment actually measures.

Optional figures, only if space permits:

7. **Raft Comparison Scope Diagram** — useful near the baseline table.
8. **Formal Model Scope Diagram** — useful if promotion/fencing text remains dense.
9. **Threat Model and Trust Boundary Diagram** — useful in discussion, but should not crowd the core protocol figures.
10. **Command Journal Pipeline** — merge into the outbox sequence diagram unless more detail is needed.

## Visual vocabulary

Use the same visual grammar everywhere.

### Evidence styles

- **Solid line**: evaluated/emulated path in the reported Docker/Python experiments.
- **Dashed line**: target deployment path not exercised in the reported evaluation.
- **Dotted line**: scaffolded/future integration.
- **Double border or labeled boundary**: formal/model-only evidence.
- **Badge labels**: `measured`, `emulated`, `implemented`, `scaffold`, `target only`, `model only`, `not evaluated`.

Do not rely on color alone. The paper should remain readable in grayscale.

### Authority and state styles

- Mark `incident.journal` as **authoritative**.
- Mark `incident.state` as **derived/rebuildable**.
- Mark `outbox.device_outbox` as **locally durable**.
- Mark core backhaul as **idempotent/cursor-based**.
- Mark promotion/fencing as **model/protocol design**, not evaluated service behavior.

### Terms to avoid in figure captions unless tightly qualified

Avoid: production deployment claims, field-evaluation claims, broad security claims, full implementation proof claims, autonomous failover claims, physical radio-performance claims, absolute data-loss guarantees, and Byzantine-fault-tolerance claims.

Prefer: `target deployment`, `emulated path`, `bounded model`, `contextual comparison`, `under stated assumptions`, `not exercised in this evaluation`.

## Implementation guidance

Prefer TikZ/PGF figures checked into `paper/figures/` as `.tex` files and included with `\input{...}`. If the existing paper already uses generated PDFs for figures, generate PDFs from the TikZ source and keep the source file in the repository.

General formatting:

- Use `\footnotesize` or `\scriptsize` inside figures.
- Keep each figure readable at single-column width unless the paper template supports double-column floats.
- Use short labels inside boxes; move caveats to the caption.
- Use `\resizebox{\linewidth}{!}{...}` only as a last resort; prefer diagrams that fit naturally.
- Avoid decorative icons. Use labeled boxes, arrows, lanes, boundaries, and badges.
- Captions should state both what the diagram shows and what it does not claim.

After each figure is added, shorten the corresponding prose. The purpose is not to add illustrations on top of dense text; it is to replace some of the dense text with clearer visual structure.

---

# Figure 1: Evaluation Coverage Map

## Priority

Highest.

## Placement

Place in `paper/sections/05_implementation.tex` after the implementation-status table, or in `paper/sections/06_evaluation.tex` immediately after the evaluation-environment paragraph.

If space is tight, this figure can replace part of the implementation-status prose but should not remove the precise implementation table unless the table becomes redundant.

## Reader problem solved

Reviewers need to see, at a glance, what is target design, what is implemented, what is actually measured, what is model-only, and what is not evaluated. This prevents the paper from being accused of hiding behind architecture prose.

## Recommended layout

Use a matrix with rows for components/evidence areas and columns for evidence status.

Columns:

1. Target design
2. Implemented/scaffolded
3. Evaluated in Docker/Python
4. Model-only
5. Not evaluated in this paper

Rows:

- Regional core services
- Command edge services
- Responder outbox/push path
- Command accept/journal path
- Command-to-core forwarder
- Python tablet stub
- Android tablet app
- Rajant mesh
- WireGuard overlay
- Nginx TLS/mTLS identity propagation
- Promotion/fencing
- Duplicate replay/idempotency
- Full crash injection
- Raft baseline
- TLA+/Hypothesis model

Use text badges rather than checkmarks if the LaTeX font/template makes symbols unreliable.

Example cell labels:

- `measured`
- `implemented`
- `scaffold`
- `target only`
- `model only`
- `not measured`
- `partial`

## Specific evidence to include

From the extraction:

- Evaluation uses Docker Compose with one core, one command edge, three responder edges, a shared Docker bridge, and a Python stub.
- Evaluation records: 390 primary records, 160 Raft records, 30 skipped promotion records.
- Physical Rajant, WireGuard, mTLS, Android tablet path, and full crash injection are outside the reported measurements.

## Suggested caption

> Coverage map for the prototype and evaluation. Solidly marked cells indicate behavior exercised by the reported Docker/Python experiments; target-only and scaffolded components are part of the deployment design but are not measured here.

## Text to shorten after adding

Shorten repetitive implementation-status and evaluation-scope prose in:

- `paper/sections/05_implementation.tex`
- `paper/sections/06_evaluation.tex`

Keep the exact caveat that traffic in the reported evaluation uses plain HTTP on the Docker bridge with synthetic device/user identifiers.

---

# Figure 2: Evidence-Aware Topology

## Priority

High.

## Placement

Replace or split the existing `fig:topology` in `paper/sections/03_system_architecture.tex`.

The current topology figure should not be merely beautified. It should be made evidence-aware: target deployment and evaluated emulation must be visually separated.

## Reader problem solved

The paper discusses regional core, command edge, responder edges, tablets, mesh, WAN, WireGuard, mTLS, and Docker emulation. Without a clear figure, readers can easily assume the paper measured the full target deployment.

## Recommended layout

Use two nested views:

### Outer target-deployment boundary

Show:

- Regional core
- Command K430 / command edge
- Responder K430s / responder edges
- Field tablets as leaf clients
- Rajant mesh as transit between vehicles
- WireGuard/HTTPS path to the regional core
- Nginx TLS/mTLS termination as target control

### Inner evaluated-emulation inset

Inside or beside the target view, show:

- Docker bridge
- Python tablet stub
- Responder `ops-api`
- Responder `syncd.push`
- Command `syncd.accept`
- Command `incident.journal`
- Core `sync-api`

Use solid arrows only for this measured/emulated path.

## Arrow semantics

Solid arrows:

- Python stub -> responder `ops-api`
- responder `syncd.push` -> command `syncd.accept`
- command `syncd.forward` -> core `sync-api`

Dashed arrows:

- Android tablet -> local K430 over HTTPS/mTLS
- vehicle-to-vehicle Rajant transit
- vehicle-to-core WireGuard overlay
- Nginx certificate identity propagation

## Required labels

Include visible labels:

- `target deployment`
- `reported emulation`
- `solid = measured Docker/Python path`
- `dashed = target path not measured`
- `tablet is a leaf client`
- `mesh is transit, not tablet participation`

## Suggested caption

> Target deployment layers and the narrower path exercised in the reported emulation. The Docker/Python path evaluates the outbox, command journal, and core-forwarding behavior; physical mesh, VPN, mTLS, and Android client behavior are target-deployment elements not measured here.

## Text to shorten after adding

Shorten role/topology explanation in `paper/sections/03_system_architecture.tex`, especially repeated caveats about target network segmentation versus emulation.

---

# Figure 3: Responder Outbox Sequence Diagram

## Priority

High.

## Placement

Place in `paper/sections/04_synchronization_protocol.tex`, replacing or supporting the dense field-edit protocol prose.

## Reader problem solved

The paper relies on a subtle distinction: the tablet/responder gets local durability before command commit, and command acknowledgement happens later. Reviewers must not confuse local ACK with authoritative command commit.

## Recommended layout

Use a swimlane sequence diagram with the following lanes:

1. Tablet or Python stub
2. Responder `ops-api`
3. Responder Postgres `outbox.device_outbox`
4. Responder `syncd.push`
5. Command `syncd.accept`
6. Command Postgres `incident.journal` / `incident.state`

## Sequence

1. Tablet/Python stub submits `POST /api/events` with `client_event_id`.
2. Responder `ops-api` inserts into `outbox.device_outbox`.
3. Responder returns **local accepted** after durable local insert.
4. `syncd.push` polls rows where `forwarded_at IS NULL`.
5. `syncd.push` sends batch to command `POST /accept/event-batch`.
6. Command rejects request if receiver is not command role.
7. Command checks `client_event_id` for duplicate.
8. Command locks incident state with `FOR UPDATE`.
9. Command allocates `event_seq` and appends to `incident.journal`.
10. Command updates derived `incident.state`.
11. Command returns accepted/duplicate result and `last_acked_seq`.
12. Responder marks `forwarded_at` and stores `ack_seq`.
13. On failure before command ACK, responder retries because `forwarded_at` remains null.

## Required labels

- `local ACK != command ACK`
- `client_event_id`
- `forwarded_at`
- `event_seq`
- `ack_seq`
- `at-least-once forwarding`
- `idempotent accept`
- `incident.journal is authoritative`
- `incident.state is derived`

## Data/config labels to include only if space permits

- `POLL_INTERVAL_S = 0.25`
- `BATCH_SIZE = 50`

Do not clutter the main sequence if these labels make the figure unreadable.

## Suggested caption

> Responder outbox protocol. A tablet submission is acknowledged locally only after durable outbox insertion; the command journal later assigns the authoritative sequence number, and duplicate delivery is handled by `client_event_id`.

## Text to shorten after adding

Shorten the step-by-step prose in `paper/sections/04_synchronization_protocol.tex`. Keep the explicit caveat that crash injection at every durable boundary is not yet validated.

---

# Figure 4: Promotion/Fencing Decision Diagram

## Priority

High.

## Placement

Place in `paper/sections/04_synchronization_protocol.tex` near the promotion subsection, or in `paper/sections/06_evaluation.tex` near formal safety validation.

If only one promotion-related figure is possible, prefer this over a separate formal-model-scope diagram.

## Reader problem solved

The paper’s strongest safety claim depends on strict promotion/fencing. A diagram should make the safety/availability trade-off obvious without implying autonomous failover.

## Recommended layout

Use a decision tree with two branches.

Start state:

- `Current command owns epoch e`
- `Candidate responder may be promoted`

Decision:

- `Can operator/candidate fence all current command authorities?`

Strict branch:

- `Yes -> signed/manual promotion record -> new command epoch e+1 -> stale command must rejoin as responder or be rejected`
- Badges: `SingleAuthority preserved`, `NoForkedJournal preserved`, `model/protocol rule`

Weak branch:

- `No -> promotion without revocation/fencing -> two command authorities can append -> split-brain counterexample`
- Badges: `unsafe`, `SingleAuthority counterexample depth 3`, `NoForkedJournal counterexample depth 5`

## Required labels

- `StrictPromotion = TRUE`
- `StrictPromotion = FALSE`
- `SingleAuthority`
- `NoForkedJournal`
- `weak promotion is unsafe`
- `durable epoch and stale-epoch rejection not implemented in evaluated services`

## Suggested caption

> Promotion preserves the single-writer invariant only under strict fencing. The evaluated services do not implement durable epoch rejection; the figure summarizes the protocol/model requirement and the weak-promotion counterexample.

## Text to shorten after adding

Shorten repeated discussion of strict versus weak promotion in:

- `paper/sections/04_synchronization_protocol.tex`
- `paper/sections/06_evaluation.tex`

Do not remove the explicit limitation that durable epoch storage and stale-epoch rejection are absent from the evaluated services.

---

# Figure 5: State Taxonomy and Consistency Contract

## Priority

High.

## Placement

Place in `paper/sections/03_system_architecture.tex` near the state taxonomy subsection.

This can replace `tab:state-taxonomy` if the diagram remains precise. If precision would be lost, keep the table and make the figure smaller.

## Reader problem solved

Readers may think the architecture applies one consistency rule to all state. The paper needs to show that different state classes use different contracts.

## Recommended layout

Use a left-to-right contract diagram or matrix.

Rows/state classes:

1. Master/reference data
2. Immutable artifacts
3. Field observations
4. Command decisions
5. Materialized state
6. Audit events

Columns:

- Authority/source
- Sync contract
- Example
- Validation caveat, if any

## Required content

- Master/reference data -> regional core -> one-way core-to-edge replication.
- Immutable artifacts -> publisher/core -> manifest/package/hash validation.
- Field observations -> local responder first -> durable outbox and at-least-once forwarding.
- Command decisions -> command edge -> single-writer journal and total order.
- Materialized state -> derived from journal -> rebuildable, not authoritative.
- Audit events -> local append/core archive target -> eventual forwarding; forwarding validation incomplete.

## Required labels

- `single-writer applies only here` on command decisions.
- `derived/rebuildable` on materialized state.
- `locally durable first` on field observations.
- `eventual` on audit forwarding.

## Suggested caption

> State classes use different synchronization contracts. The single command writer applies to authority-bearing journal entries, not to every object in the system.

## Text to shorten after adding

Shorten explanatory lead-in around the state taxonomy. Keep the warning that the command-writer rule is scoped to authority-bearing incident-journal entries.

---

# Figure 6: Partition and Recovery Timeline

## Priority

Medium-high.

## Placement

Place in `paper/sections/06_evaluation.tex` near the WAN recovery result.

The recovery plot was removed from the submitted manuscript for page budget.
This figure should support the WAN recovery prose and table, not replace them.

## Reader problem solved

The evaluation measures command-core WAN isolation, not all possible mesh partitions. The figure should show what continues during the partition and what resumes after reconnect.

## Recommended layout

Use a horizontal timeline with three lanes:

1. Responder -> command submission path
2. Command local journal
3. Command -> core backhaul

Timeline phases:

- Before partition
- WAN partition begins
- During partition
- WAN heals
- Replay/catch-up completes

## Required behavior

During command-core WAN partition:

- Command-local journal can continue if command node and storage are available.
- Command-to-core forwarding pauses.
- `sync.state` cursor does not advance until core ACK.
- On heal, `syncd.forward` replays journal rows above cursor.

Clearly label this as **command-core WAN recovery**, not mesh-wide recovery.

## Required caveat label

- `responder-command mesh partitions not measured here`

## Suggested caption

> WAN recovery experiment scope. The reported partition delays command-to-core backhaul while command-local journaling remains available under the stated assumptions; responder-command mesh partitions are not measured in this experiment.

## Text to shorten after adding

Shorten repeated recovery-scope prose in `paper/sections/06_evaluation.tex`. Keep the exact assumptions: command node alive, local storage available, and partition limited to the evaluated command-core path.

---

# Optional Figure 7: Raft Comparison Scope Diagram

## Priority

Medium.

## Placement

Place near `tab:baseline` in `paper/sections/06_evaluation.tex` only if space permits.

## Reader problem solved

The Raft comparison can be misread as a strawman. This diagram should make clear that it isolates quorum-progress behavior and is not a workflow-equivalent replacement benchmark.

## Recommended layout

Use a side-by-side diagram.

Left side: 3-node Raft cluster.

- Leader
- Two followers/voters
- Majority requirement: `floor(n/2)+1 reachable voters`
- Losing at least `ceil(n/2)` voters prevents progress
- For `n = 3`, losing 2 voters prevents writes

Right side: Rescue OIS command-local writer.

- Command edge owns journal
- Responder isolation does not require quorum for command-local commits
- Command failure or unfenced promotion remains a separate failure mode

## Data labels to include only if readable

- Rescue OIS q10 field-edit median/p95: `946.3 / 1018.5 ms`
- Raft q10 direct write median/p95: `10.5 / 18.1 ms`
- Raft follower catch-up median/p95: `4109 / 5109 ms`
- Raft quorum-loss writes: `0%`

If these numbers clutter the figure, leave them in the table and keep the diagram conceptual.

## Required labels

- `contextual comparison`
- `not workflow-equivalent`
- `majority required`
- `single command authority`
- `both designs have authority/leader failure modes`

## Suggested caption

> Scope of the Raft baseline. The comparison illustrates quorum-dependent progress versus command-local authority; it is not an end-to-end replacement benchmark for the incident workflow.

---

# Optional Figure 8: Formal Model Scope Diagram

## Priority

Medium.

## Placement

Place in `paper/sections/06_evaluation.tex` near TLA+/Hypothesis validation, especially if the text remains hard to parse after adding the promotion diagram.

## Reader problem solved

Bounded model checking can be overread as implementation verification. This diagram should show what the model includes and excludes.

## Recommended layout

Use a boundary diagram.

Inside the model boundary:

- Vehicles
- Roles
- Authority
- Partitions/heals
- Commit events
- Promotion actions
- `client_event_id`
- Abstract journals
- Invariants: `SingleAuthority`, `NoForkedJournal`, `LocalIdempotency`, `SingleCommand`

Outside the model boundary:

- fsync/disk failure
- process crashes at transaction boundaries
- certificate revocation
- mTLS/WireGuard transport
- Android implementation
- physical mesh behavior
- operator mistakes beyond modeled promotion choice

## Suggested caption

> Scope of the formal checks. The TLA+/Hypothesis artifacts exercise bounded abstract authority and promotion invariants; they do not verify storage, transport, credential, or crash behavior of the production stack.

---

# Optional Figure 9: Threat Model and Trust Boundary Diagram

## Priority

Medium-low.

## Placement

Place in `paper/sections/07_discussion.tex` if the discussion section has room.

## Reader problem solved

The current security discussion can look like a technology list. A trust-boundary diagram can clarify assumptions and limitations.

## Recommended layout

Use a boundary diagram with three labeled perimeters:

1. Tablet-to-local-K430 boundary
2. Vehicle-to-vehicle/mesh-transit boundary
3. Vehicle-to-core boundary

Entities:

- Organizational CA/IdP
- Field tablet
- Responder edge
- Command edge
- Regional core
- Nginx reverse proxy
- WireGuard overlay
- Rajant transit
- Audit/core archive

## Required labels

- `target deployment only`
- `backend trusts reverse-proxy identity`
- `offline revocation delay`
- `not Byzantine-fault-tolerant`
- `emulation uses plain HTTP + synthetic IDs`

## Suggested caption

> Target trust boundaries and identity assumptions. These controls describe the intended deployment model; the reported emulation uses plain HTTP on the Docker bridge and synthetic identities.

---

# Optional Figure 10: Command Journal Pipeline

## Priority

Medium-low as a standalone figure; high if merged into Figure 3.

## Placement

Merge into Figure 3 as a right-hand command-side detail if possible. Only add as a standalone figure if the journal/state/backhaul path remains confusing.

## Reader problem solved

Clarifies that `incident.journal` is authoritative, `incident.state` is derived, and core backhaul is idempotent/cursor-based.

## Recommended layout

Use a data-flow diagram:

`accepted event batch` -> `command transaction` -> `incident.journal` -> `incident.state` -> `syncd.forward` -> `core sync-api` -> `master.incident_events`

Annotate:

- `FOR UPDATE` around state lock / sequence allocation.
- `UNIQUE (incident_id, event_seq)`.
- `UNIQUE client_event_id`.
- `last_acked_seq_to_core` cursor.
- `incident.state = derived/rebuildable`.

## Suggested caption

> Command-side journal pipeline. The command transaction appends the authoritative journal and updates derived state; core backhaul is idempotent and cursor-based.

---

# Text replacement plan

Use the diagrams to reduce text, not just decorate it.

## Replace or compress these text blocks

### Deployment layers and emulation boundary

Files/areas:

- `paper/sections/03_system_architecture.tex`
- Current topology figure area

Use Figure 2. Keep one paragraph of prose and move details into figure labels/caption.

### State taxonomy

Files/areas:

- `paper/sections/03_system_architecture.tex`
- State taxonomy subsection/table

Use Figure 5. Keep the table only if needed for exact contract wording.

### Outbox ACK semantics

Files/areas:

- `paper/sections/04_synchronization_protocol.tex`
- Protocol contract and field-edit flow

Use Figure 3. Delete or compress the ordered step list if redundant.

### Partition behavior and recovery

Files/areas:

- `paper/sections/04_synchronization_protocol.tex`
- `paper/sections/06_evaluation.tex`

Use Figure 6. Keep the limitation that responder-command mesh partitions were not measured.

### Promotion safety

Files/areas:

- `paper/sections/04_synchronization_protocol.tex`
- `paper/sections/06_evaluation.tex`

Use Figure 4. Keep the limitation that durable epoch/stale-epoch rejection is not implemented in evaluated services.

### Implementation/evaluation coverage

Files/areas:

- `paper/sections/05_implementation.tex`
- `paper/sections/06_evaluation.tex`

Use Figure 1. This is the best place to prevent reviewer misunderstanding.

### Raft comparison

Files/areas:

- `paper/sections/06_evaluation.tex`

Use Optional Figure 7 only if the Raft prose remains long or defensive.

### Threat model

Files/areas:

- `paper/sections/07_discussion.tex`

Use Optional Figure 9 only if the paper has space.

---

# Caption style guide

Every caption should follow this pattern:

1. First sentence: what the figure shows.
2. Second sentence: what is measured/evaluated versus target-only/model-only.
3. Third sentence, if needed: the key caveat.

Good examples:

> Responder outbox protocol. A tablet submission is acknowledged locally after durable outbox insertion; the command journal later assigns the authoritative sequence number. Duplicate delivery is handled by `client_event_id`, but full crash injection at every durable boundary is outside this evaluation.

> Coverage map for the prototype and evaluation. Solidly marked cells indicate behavior exercised by the reported Docker/Python experiments; target-only and scaffolded components are deployment design elements not measured here.

> Promotion safety model. Strict fencing preserves the single-writer invariant in the abstract model, while weak promotion admits split-brain counterexamples. Durable epoch rejection is a protocol requirement and is not implemented in the evaluated services.

Bad examples:

> Full rescue-service deployment architecture.

This implies field deployment.

> Verified failover protocol.

This overstates the formal evidence and implementation status.

> Secure mTLS/WireGuard mesh design.

This implies measured security behavior.

---

# Recommended LaTeX workflow for Codex

1. Inspect existing figure/table conventions in `paper/main.tex`, `paper/sections/*.tex`, and `paper/figures/`.
2. Add TikZ source files under `paper/figures/`, for example:
   - `fig_coverage_map.tex`
   - `fig_topology_scope.tex`
   - `fig_outbox_sequence.tex`
   - `fig_promotion_fencing.tex`
   - `fig_state_contracts.tex`
   - `fig_partition_timeline.tex`
3. Include them with normal LaTeX figure environments and labels:
   - `fig:coverage-map`
   - `fig:topology-scope`
   - `fig:outbox-sequence`
   - `fig:promotion-fencing`
   - `fig:state-contracts`
   - `fig:partition-timeline`
4. Remove or compress redundant prose near each figure.
5. Build with `latexmk -pdf main.tex` from the paper directory.
6. Check for:
   - overfull boxes,
   - unreadable figure text,
   - captions that overclaim,
   - stale references to removed tables/figures,
   - page-count increase.
7. Report changed files, added figures, removed text, build status, and any remaining warnings.

## Figure selection rule if page count becomes a problem

If adding all six recommended figures makes the paper too long, keep these four first:

1. Evaluation Coverage Map
2. Responder Outbox Sequence Diagram
3. Evidence-Aware Topology
4. Promotion/Fencing Decision Diagram

Then choose either State Taxonomy or Partition Timeline based on which section currently has the densest text.

Do not include optional Raft, formal-model, threat-boundary, or command-pipeline figures unless they replace enough prose to justify their space.

---

# Final quality checklist

Before considering the diagram pass complete, verify:

- At least one figure explicitly separates target deployment from evaluated emulation.
- At least one figure explicitly distinguishes local ACK from command ACK.
- At least one figure explicitly shows that `incident.journal` is authoritative and `incident.state` is derived.
- Promotion/fencing is shown as strict/manual/model-level, not autonomous failover.
- The evaluation coverage figure does not hide limitations.
- The Raft comparison, if diagrammed, says `contextual` and `not workflow-equivalent`.
- Security diagrams, if included, avoid decorative lock icons that imply measured security.
- No caption claims real mesh, real VPN/TLS overhead, Android evaluation, full crash validation, or production readiness.
- The paper still reads positively: diagrams should clarify the scoped contribution, not make the work look unfinished.
