# Rescue OIS

Research on command succession in rescue-service incident response over intermittent
links. When the incident commander is cut off, who may give orders? How do devices that
cannot reach each other enforce that? And what happens to the orders given meanwhile
once the links return? Authority belongs to people, through signed grants and succession
rules the organization fixes in advance. Vehicles and handhelds only enforce it.

The current paper is a journal manuscript for ACM Transactions on Cyber-Physical Systems
(TCPS), in [`paper/`](paper/README.md). It sits next to the code and data behind it, on
this repository's only branch, `main`.

## Start Here

| You want to | Read | Then run |
| --- | --- | --- |
| Understand the problem and the current results | The manuscript in [`paper/`](paper/README.md) (introduction and evaluation), then [`testbed/FINDINGS.md`](testbed/FINDINGS.md) | — |
| Run or change the policy experiments | [`testbed/README.md`](testbed/README.md) | `cd testbed && python -m aas_testbed list` |
| Work on the manuscript | [`paper/README.md`](paper/README.md) and [`paper/TCPS_PLAN.md`](paper/TCPS_PLAN.md) | [Working on the manuscript](#working-on-the-manuscript) |
| Run the prototype, or reproduce the WONS draft's numbers | [`docs/prototype.md`](docs/prototype.md) | `RESPONDERS=3 ./scripts/dev-up.sh` |
| Read the prototype's design, or check whether a doc is current | [`docs/README.md`](docs/README.md) | — |

## What Is Here

The repository holds three bodies of evidence. They are easy to confuse, and they differ in
what they can show.

| Part | What it is | What it can show |
| --- | --- | --- |
| **Testbed** ([`testbed/`](testbed/README.md)) | A discrete-event model of a forest-fire incident: succession policies S0 to S5 (and S3 with a lease), three partition cases, a truth oracle and a randomized search for invariant violations. Pure Python, no dependencies; the committed results cover 8,950 simulated incidents. | The evaluation in the TCPS manuscript: policy semantics, counterexamples and the fixes for them. Latencies are parameters, not measurements. |
| **Prototype** ([`core/`](core/), [`edge/`](edge/), [`scripts/`](scripts/)) | An incident information system run as a Docker Compose emulation: a regional core, a command vehicle edge and responder edges, with a CRDT baseline ([`baseline/`](baseline/)) and a Raft baseline ([`baseline-raft/`](baseline-raft/)). | The evaluation in the WONS draft. Implements one policy, S1, and has no notion of a person ([what it does not do](docs/prototype.md#what-the-prototype-does-not-do)). |
| **Formal models** ([`formal/`](formal/)) | A TLA+ model of the prototype's single-writer rule, mirrored by Hypothesis state-machine tests. | Safety of the prototype's rule. No persons, no lease, no relaying yet; the manuscript's two propositions are still to be model-checked. |

## One Branch

Everything is on `main`, and new work goes there; CI runs on every push to it. Until
October 2026 the manuscript (`tcps`), the WONS conference draft (`paper`) and AI-assisted
changes (`claude/*`) had branches of their own. They were merged into `main` with their
history, then deleted:

- The manuscript is in [`paper/`](paper/README.md), with the scenario and system model
  document in `paper/model/` and the prototype's datasets in `paper/data/`.
- The WONS draft, as it was left, is the tag
  [`wons-draft`](https://github.com/adityasissodiya/rescue-ois/tree/wons-draft).
- Commit hashes from the old branches still resolve: every one of those commits is in
  `main`'s history.

## Names You Will Meet

The work has been renamed as its framing changed, and older files keep older names.

| Name | Meaning |
| --- | --- |
| AAS, Authority-Aligned Sequencing | The approach, as named in the WONS draft. The TCPS manuscript describes it without the acronym. |
| AAL, Authority-Aligned Linearization; authority-aligned synchronization | Earlier names for AAS, in older documents and commits. |
| Tiered Sync | The first name of the prototype's architecture. It survives in the design mock-ups in `preview/` and `ui_kits/`. |
| WONS | The conference draft for WONS 2027, kept as the tag `wons-draft`. |
| NCA | The venue of an earlier, double-blind version of the prototype paper (2026); the name appears in old commits. The Android namespace `org.review.rescueois` is left over from anonymizing the code for double-blind review. |
| TCPS | ACM Transactions on Cyber-Physical Systems, the journal the manuscript in `paper/` targets. |
| Command edge, responder edge | The prototype's vehicle roles: the vehicle that accepts the incident's decisions, and the vehicles that queue field submissions and forward them to it. |
| A, B, S, C, OP | The scenario's people: incident commander, deputy (sector North), sector South leader, duty chief at the regional centre, operator. |
| S0 to S5, S3L | Succession policies, from no succession (S0) to pre-authorized deputy activation (S4, S5); S3L is S3 with a lease. S1 is the prototype's policy. [`testbed/README.md`](testbed/README.md#policies) defines each. |
| P-A, P-B, P-C | Partition cases: the commander's handheld cut off; all cellular down while the vehicle mesh stays up; P-B plus the mesh split between commander and deputy. |
| Authoritative, provisional, residual, in doubt | The four statuses of an order, as the people who act on it see them. |

## Repository Map

| Path | Contents | Status |
| --- | --- | --- |
| [`paper/`](paper/README.md) | The TCPS manuscript (`acmart`), the system model document (`model/`), the prototype's datasets and the scripts that turn them into tables | Current; the paper under active work |
| [`testbed/`](testbed/) | Succession testbed: model, simulator, experiments, results, findings | Current; CI runs its tests |
| [`core/`](core/) | Regional core services and database migrations | Prototype; measured in Docker |
| [`edge/`](edge/) | Vehicle-edge services (`ops-api`, `syncd`, local Postgres with outbox and journal) and WireGuard, Nginx and nftables configuration | Prototype; measured in Docker |
| [`scripts/`](scripts/) | Docker stack helpers, promotion script, evaluation harnesses | Prototype |
| [`baseline/`](baseline/) | CRDT-LWW baseline service and its harness | Prototype baseline |
| [`baseline-raft/`](baseline-raft/) | Three-voter Raft baseline (Go `raftd`) | Prototype baseline |
| [`formal/`](formal/) | TLA+ model (`tla/`) and Hypothesis mirrors (`python/`) | Covers the prototype's rule |
| [`docs/`](docs/README.md) | Architecture, ADRs, runbooks, deployment notes, prototype guide | Mixed; the index marks each |
| [`infra/`](infra/) | Ansible, router and mesh-radio templates for the target hardware | Never deployed or measured |
| [`tablet/`](tablet/) | Android tablet app scaffold | Scaffold; not built in CI or evaluated |
| [`ui_kits/`](ui_kits/tablet/README.md), [`preview/`](preview/README.md) | Click-through tablet UI mock-up and static design previews | Design mock-ups from the first framing; not maintained |

## Working on the Code

- **Testbed:** Python 3.12, no runtime dependencies. From `testbed/`, `python -m pytest`
  runs the tests and `ruff check .` the lint that CI runs. After a change to the model or
  the simulator, re-run the experiments (`python -m aas_testbed all`, about 10 minutes on
  four cores; runs are deterministic, so unchanged code reproduces `results/` byte for
  byte), commit the new `results/`, and refresh the manuscript's numbers (below).
  `FINDINGS.md` interprets the committed results; re-read it when they change.
- **Prototype services:** each of the eight Python services under `core/` and `edge/` is
  a package with its own tests; CI runs `ruff check .` and `pytest` in each. The
  end-to-end harnesses need the Docker stack ([`docs/prototype.md`](docs/prototype.md)).
- Pre-commit hooks (`.pre-commit-config.yaml`) run ruff and reject new files over 500 KB.

## Working on the Manuscript

[`paper/BUILDING.md`](paper/BUILDING.md) says how to build the manuscript with MiKTeX or
TeX Live. Every testbed number in it is a macro generated from the committed results in
`testbed/results/`, never typed by hand. To refresh them, from `testbed/`:

```bash
python -m aas_testbed latex --out ../paper/data
mv ../paper/data/tab_*.tex ../paper/tables/
```

`paper/data/TESTBED_TRACE.md` traces each of those numbers to its CSV, filter and
statistic; `paper/TRACEABILITY.md` traces the prototype's numbers to their datasets.

## License

Apache License 2.0. See [`LICENSE`](LICENSE).
