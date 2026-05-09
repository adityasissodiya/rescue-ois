# diagramGuidance.md

## Purpose

Use this file to perform a diagram-discovery pass over the paper and repository. The goal is **not** to edit the paper yet. The goal is to extract the concepts, mechanisms, claims, data, and section references needed to design diagrams that can replace or compress hard-to-understand prose.

Produce a structured extraction report that can be handed back to ChatGPT so it can propose concrete figures, captions, and replacement locations.

The final diagrams should help readers understand the system faster, especially the authority-aware synchronization protocol, failure behavior, promotion/fencing assumptions, evaluation scope, and what was actually measured.

---

## Ground rules

1. **Do not invent evidence.** Extract only what exists in the paper, LaTeX files, repo, evaluation artifacts, configs, formal models, scripts, or generated tables.
2. **Do not silently upgrade claims.** If a component is target-deployment-only, scaffolded, partially implemented, or not evaluated, preserve that status explicitly.
3. **Do not draw final diagrams yet** unless separately instructed. First produce an extraction report and candidate diagram inventory.
4. **Prefer clarity over visual complexity.** The eventual diagrams should reduce cognitive load, not become decorative architecture art.
5. **Distinguish three categories everywhere:**
   - target deployment design;
   - implemented prototype path;
   - evaluated/emulated path.
6. **Every extracted fact must include a source reference** such as file path, section name, LaTeX label, table label, figure label, line number when feasible, or evaluation artifact path.
7. **Keep the paper defensible.** Diagrams must not imply real field deployment, real Rajant mesh measurement, WireGuard/mTLS overhead measurement, Android tablet evaluation, complete crash validation, or production completeness unless the repo contains evidence.

---

## Inputs to inspect

Inspect as many of these as exist in the repository:

- `paper/main.tex`
- `paper/sections/*.tex`
- existing figures under `paper/figures/`, `figures/`, `assets/`, or similar
- generated tables such as `tab_baseline.tex`, `tab_evaluation.tex`, or equivalent
- evaluation scripts, JSON/CSV/JSONL outputs, notebooks, logs, and README files
- Docker Compose files and service configs
- protocol or synchronization code, especially outbox, `syncd`, journal, idempotency, and replay logic
- TLA+ specifications and model-checking configs
- Hypothesis/property tests
- Raft comparison scripts/configs/results
- security, deployment, Ansible, WireGuard, mTLS, Rajant, Android, or MDM-related files
- any build scripts used to regenerate the paper tables or figures

If file names differ, discover the equivalent paths and report them.

---

## Output files to create

Create the following files in the repo, preferably under `paper/diagram-notes/` or another clearly named directory:

1. `diagram_extraction_report.md`
2. `diagram_facts.yaml`

If YAML is inconvenient, use JSON instead, but keep it machine-readable.

Do not modify the paper unless separately instructed.

---

## `diagram_extraction_report.md` structure

Use this exact top-level structure.

```md
# Diagram Extraction Report

## 1. Paper Map

## 2. Existing Figures and Tables

## 3. Hard-to-Understand Concepts

## 4. Candidate Diagrams

## 5. Evidence and Data Inventory

## 6. Text Replacement Opportunities

## 7. Visual Vocabulary

## 8. Claim-Safety Notes

## 9. Recommended Diagram Priority

## 10. Open Questions for Author
```

Each section is described below.

---

## 1. Paper Map

Create a concise map of the paper:

- section number and title;
- file path;
- main claim/purpose of the section;
- dense concepts introduced there;
- existing labels for sections, figures, tables, equations, algorithms, and listings;
- paragraphs that are visually or conceptually overloaded.

Example format:

```md
### Section IV - Synchronization Protocol
- File: `paper/sections/04_synchronization_protocol.tex`
- Purpose: defines durable outbox, command journal, sequence assignment, replay/idempotency, promotion/fencing assumptions.
- Dense concepts: responder enqueue/ack boundary, command commit boundary, duplicate suppression, strict promotion.
- Existing labels: `sec:sync`, `fig:...`, `tab:...`
- Candidate replacement paragraphs: lines 31-87, 112-146.
```

---

## 2. Existing Figures and Tables

Inventory every existing figure and table:

- label;
- caption;
- source file;
- what it currently explains;
- whether it is clear, cramped, redundant, or misleading;
- whether it should be replaced, split, simplified, or kept;
- whether it contains measured data, analytic claims, or implementation-status claims.

Pay special attention to architecture diagrams, evaluation tables, implementation-status tables, and Raft comparison tables.

---

## 3. Hard-to-Understand Concepts

Identify concepts that a reviewer or first-time reader may struggle with. Prioritize concepts that currently require several paragraphs to understand.

For each concept, include:

- concept name;
- section/file/line references;
- why it is hard to understand;
- what misunderstanding a reviewer might have;
- whether a diagram could replace prose, support prose, or prevent overclaiming;
- exact source text fragments or short summaries, with references;
- related tables, results, scripts, or formal models.

Look specifically for these likely hard concepts:

1. **Three-tier deployment model**: core, command edge, responder edge/tablet.
2. **Target deployment vs evaluated emulation**: Rajant/WireGuard/mTLS/Android vs Docker/Python stub.
3. **State taxonomy**: master/reference data, immutable artifacts, field observations, command decisions, materialized state, audit events.
4. **Consistency contracts by state type**: one-way replication, append-only outbox, single-writer journal, rebuildable derived state, eventual audit forwarding.
5. **Responder outbox lifecycle**: local enqueue, retry, command accept, ack, forwarded marking, duplicate handling.
6. **Command journal sequencing**: single command writer, sequence numbers, idempotency, materialized views.
7. **Partition and recovery behavior**: what works while disconnected, what waits, how replay catches up.
8. **Promotion/fencing/epochs**: strict promotion, weak-promotion counterexample, stale command rejoin behavior, safety vs availability trade-off.
9. **Raft comparison scope**: quorum-progress comparison, not workflow-equivalent end-to-end replacement.
10. **Formal model boundaries**: what the TLA+/Hypothesis checks cover and do not cover.
11. **Security/trust boundaries**: organizational CA, mTLS-derived identity, edge trust, offline revocation limits, stolen/compromised device assumptions.
12. **Evaluation coverage**: measured, emulated, scaffolded, target-only, and not evaluated.
13. **Crash-consistency gaps**: which durable boundaries are validated and which remain future work.

---

## 4. Candidate Diagrams

Produce a candidate inventory of diagrams that would make the paper easier to understand.

For each candidate, use this template:

```md
### Dn. <Short descriptive title>

- Priority: High / Medium / Low
- Proposed type: architecture diagram / sequence diagram / state machine / timeline / matrix / decision tree / flowchart / swimlane / layered diagram / comparison diagram
- Target section: <section name and file path>
- Replace or support: replace prose / support prose / replace existing figure / split existing figure
- Reader problem solved: <what this makes obvious>
- Entities to show: <nodes, actors, services, stores>
- Flows or relationships to show: <arrows, sequence, ownership, trust boundary, replication direction>
- Required labels: <exact technical labels to use>
- Data/results to include: <numbers, if any, and source paths>
- Assumptions/caveats to show visually: <e.g., "emulated only", "strict promotion required", "command storage available">
- Source references: <files, sections, line ranges, table/figure labels, scripts>
- Risk if drawn badly: <possible overclaim or reviewer misunderstanding>
- Suggested caption idea: <one-sentence caption>
```

At minimum, evaluate these diagram candidates:

### Candidate A - System Boundary and Deployment Layers

A clean architecture diagram showing:

- core services;
- command edge;
- responder edge;
- tablet/client;
- target network components such as Rajant/WireGuard/mTLS only if properly labeled as target deployment;
- evaluated Docker/Python path separately or with dashed boundaries.

Purpose: prevent confusion between the real target deployment and what was evaluated.

### Candidate B - State Taxonomy and Consistency Contract

A matrix or layered diagram showing each state class and its synchronization rule:

- master/reference data -> core-to-edge replication;
- immutable artifacts -> manifest/package/hash validation;
- field observations -> durable outbox and at-least-once forwarding;
- command decisions -> single command writer and total order;
- materialized state -> derived/rebuildable;
- audit events -> append-only/eventually forwarded.

Purpose: avoid the impression that the paper applies one consistency model to all data.

### Candidate C - Responder Outbox Sequence Diagram

A swimlane sequence from tablet/responder edge to command edge:

1. tablet creates event;
2. responder stores local durable outbox entry;
3. command receives event;
4. command checks idempotency;
5. command assigns sequence number;
6. command commits journal row;
7. command returns ack;
8. responder marks event forwarded;
9. reconnect/retry behavior handles duplicates.

Purpose: make ACK semantics and durable transaction boundaries obvious.

### Candidate D - Command Journal and Materialized View Pipeline

A data-flow diagram showing:

- accepted events;
- sequence assignment;
- append-only journal;
- materialized incident state;
- replay/rebuild path;
- audit/backhaul path.

Purpose: explain why the journal is authoritative and materialized state is derived.

### Candidate E - Partition and Recovery Timeline

A timeline showing:

- normal connected operation;
- WAN/mesh partition;
- responder continues local enqueue;
- command continues command-local journal commits if command is alive;
- reconnect;
- replay/idempotent catch-up.

Purpose: clarify what continues during a partition and what does not.

### Candidate F - Promotion, Epochs, and Fencing

A decision tree or state machine showing:

- current command epoch;
- strict promotion requirement;
- signed/manual promotion record if defined;
- stale command returns;
- stale epoch rejected or old command rejoins as non-command;
- weak-promotion path marked unsafe/counterexample.

Purpose: make the safety/availability trade-off explicit.

### Candidate G - Raft Comparison Scope

A side-by-side comparison diagram showing:

- Raft cluster needs reachable majority;
- Rescue OIS command writer does not require responder quorum for command-local commits;
- comparison is contextual, not workflow-equivalent;
- both have failure modes when their authority/leader/command node is unavailable.

Purpose: prevent accusations of strawman comparison.

### Candidate H - Evaluation Coverage Map

A coverage diagram or matrix showing:

- target deployment components;
- implemented prototype components;
- components exercised in Docker evaluation;
- components not measured.

Purpose: make the evaluation honest and easy to parse.

### Candidate I - Threat Model and Trust Boundaries

A trust-boundary diagram showing:

- organizational CA/IdP;
- enrolled devices;
- command edge;
- responder edge;
- tablet;
- backend services trusting mTLS-derived identity;
- offline revocation limitation;
- stolen/compromised device boundary.

Purpose: turn a technology list into a scoped security model.

### Candidate J - Formal Model Scope

A small diagram showing:

- abstract variables checked by TLA+/Hypothesis;
- safety invariant: one active command writer / no split brain under strict promotion;
- weak-promotion counterexample;
- explicitly excluded implementation concerns such as fsync, certificates, crash injection, and transport authentication.

Purpose: prevent readers from overreading bounded model checking as full implementation verification.

---

## 5. Evidence and Data Inventory

Extract all evidence that could appear in diagrams or captions:

- evaluation scenario names;
- measured metrics;
- table values;
- benchmark parameters;
- queue depths;
- event payload sizes;
- number of clients;
- partition durations;
- warm-up/exclusion rules;
- polling intervals;
- retry intervals;
- hardware/environment metadata;
- durability settings if available;
- Raft cluster size and quorum-loss setup;
- TLA+ model bounds;
- Hypothesis test parameters;
- source files for each generated table.

For every value, include:

- value;
- unit;
- source file;
- whether measured, configured, modeled, or assumed;
- whether it belongs in a diagram.

If a value is missing, write `missing from repo` rather than guessing.

---

## 6. Text Replacement Opportunities

Find paragraphs that can be shortened if replaced by a diagram.

For each opportunity:

- file and line range;
- current topic;
- approximate current word count;
- proposed diagram candidate ID;
- what prose can be deleted, shortened, or moved to caption;
- what caveat must remain in text;
- whether the replacement reduces overclaiming risk.

Example:

```md
### TRO-3 - Outbox ACK semantics
- File: `paper/sections/04_synchronization_protocol.tex`, lines 45-92
- Current issue: multi-step protocol explained in dense prose.
- Proposed diagram: D3 Responder Outbox Sequence Diagram
- Text that can be shortened: retry/ACK/idempotency explanation.
- Caveat that must remain: crash injection at all durable boundaries is not yet validated.
```

---

## 7. Visual Vocabulary

Propose a consistent visual vocabulary for eventual diagrams.

Include:

- canonical names for system actors and services;
- preferred labels for arrows;
- line styles for target-only vs evaluated paths;
- how to mark trust boundaries;
- how to mark authoritative state;
- how to mark derived/rebuildable state;
- how to mark measured vs analytic vs modeled claims;
- terms to avoid because they overclaim.

Suggested conventions:

- solid line = evaluated/emulated path;
- dashed line = target deployment path not measured in current evaluation;
- dotted line = future/scaffolded integration;
- thick border = authoritative state;
- rounded box = service/process;
- cylinder = durable store/database;
- lock icon or label = authenticated/trusted boundary, but only where evidence exists;
- warning callout = explicit limitation or unsafe path;
- use grayscale-friendly styling and avoid relying only on color.

Use the actual terms from the paper and repo. Do not rename components unless recommending a terminology cleanup.

---

## 8. Claim-Safety Notes

Create a list of things diagrams must not imply.

At minimum, verify whether the paper currently has evidence for the following. If not, mark as unsafe:

- real Rajant mesh performance measurement;
- WireGuard overhead measurement;
- mTLS overhead measurement;
- real Android tablet evaluation;
- complete crash-injection validation;
- automatic failover;
- production-ready promotion/fencing;
- instantaneous offline certificate revocation;
- field deployment;
- general proof of correctness beyond the bounded model;
- workflow-equivalent superiority over Raft;
- all state types requiring single-writer semantics.

Also identify phrases or labels that could create these mistaken impressions in figures or captions.

---

## 9. Recommended Diagram Priority

Rank candidate diagrams by expected reviewer impact.

Use this scoring table:

| Candidate | Clarity gain (1-5) | Reviewer-risk reduction (1-5) | Evidence available (1-5) | Space cost (1-5, lower is better) | Priority |
|---|---:|---:|---:|---:|---|
| D1 | | | | | |

Explain the top 3 recommendations.

Prioritize diagrams that:

- replace dense protocol prose;
- prevent overclaiming about evaluation scope;
- make the single-writer/promotion trade-off precise;
- clarify the Raft comparison;
- distinguish target design from evaluated prototype.

---

## 10. Open Questions for Author

List only questions that block good diagram design.

Examples:

- What exact names should be used for the command edge and responder edge?
- Is the intended final figure style TikZ/PGF, Mermaid-to-SVG, draw.io, or another pipeline?
- Can the paper afford one full-width figure, or must all figures fit one column?
- Should deployment-only components appear in the main architecture diagram or a separate coverage diagram?
- Which diagram should replace the current Figure 1 if space is tight?

Do not ask questions whose answers can be found in the repo.

---

## `diagram_facts.yaml` required schema

Create a machine-readable file using this schema. Include as many entries as the repository supports.

```yaml
paper:
  title: ""
  main_tex: "paper/main.tex"
  sections:
    - id: "sec:introduction"
      title: ""
      file: ""
      line_start: null
      line_end: null
      key_claims: []
      hard_concepts: []

components:
  - name: ""
    type: "service|store|device|network|identity|process|external"
    role: ""
    status: "target-only|implemented|evaluated|scaffolded|not-evaluated|unknown"
    source_refs: []

state_types:
  - name: ""
    examples: []
    authoritative_location: ""
    consistency_contract: ""
    sync_direction: ""
    durable_boundary: ""
    evaluated: false
    source_refs: []

protocol_steps:
  - id: ""
    name: ""
    actors: []
    preconditions: []
    actions: []
    commit_or_ack_boundary: ""
    duplicate_behavior: ""
    failure_behavior: ""
    source_refs: []

promotion:
  variables: []
  safe_path_steps: []
  unsafe_path_steps: []
  assumptions: []
  evaluated: false
  modeled: false
  source_refs: []

security:
  trust_boundaries: []
  identities: []
  in_scope_threats: []
  partial_or_limited_handling: []
  out_of_scope_threats: []
  source_refs: []

evaluation:
  scenarios:
    - name: ""
      measured: true
      metrics: []
      setup: []
      limitations: []
      source_refs: []
  coverage:
    target_deployment: []
    implemented_prototype: []
    evaluated_in_emulation: []
    not_evaluated: []

formal_model:
  files: []
  checked_properties: []
  bounds: []
  counterexamples: []
  exclusions: []
  source_refs: []

diagram_candidates:
  - id: "D1"
    title: ""
    type: ""
    priority: "High|Medium|Low"
    target_sections: []
    replace_or_support: ""
    entities: []
    flows: []
    labels: []
    data_values: []
    caveats: []
    source_refs: []
    risk_if_drawn_badly: ""
```

---

## Suggested final response from Codex

After generating the two files, report:

- paths to the generated files;
- top 5 diagram candidates;
- which existing figure/table should be replaced first;
- any missing repo evidence that blocks accurate diagrams;
- whether the paper builds unchanged after this analysis pass, if a build was run.

Do not make paper edits during this pass.
