# Rescue OIS

Research on command succession in rescue-service incident response over intermittent
links. When the incident commander is cut off, who may give orders? How do devices that
cannot reach each other enforce that? And what happens to the orders given meanwhile
once the links return? Authority belongs to people, through signed grants and succession
rules the organization fixes in advance. Vehicles and handhelds only enforce it.

The current paper is a journal manuscript for ACM Transactions on Cyber-Physical Systems
(TCPS), on branch [`tcps`](https://github.com/adityasissodiya/rescue-ois/tree/tcps). This
branch, `main`, holds the code behind it.

## Start Here

| You want to | Read | Then run |
| --- | --- | --- |
| Understand the problem and the current results | The manuscript on `tcps` (introduction and evaluation), then [`testbed/FINDINGS.md`](testbed/FINDINGS.md) | — |
| Run or change the policy experiments | [`testbed/README.md`](testbed/README.md) | `cd testbed && python -m aas_testbed list` |
| Work on the manuscript | `README.md` and `TCPS_PLAN.md` on `tcps` | [Working on the manuscript](#working-on-the-manuscript) |
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

## Branches

| Branch | Contents | Status |
| --- | --- | --- |
| `main` | All code: testbed, prototype, baselines, formal models, documentation | Default branch; CI runs on every push and pull request to it. |
| [`tcps`](https://github.com/adityasissodiya/rescue-ois/tree/tcps) | The TCPS manuscript (`acmart`), the scenario and system model document (`model/`), and the prototype's datasets | The paper under active work. |
| [`paper`](https://github.com/adityasissodiya/rescue-ois/tree/paper) | The WONS 2027 conference draft (IEEEtran), with the same `model/` and datasets | Kept as it is while the supervisors review the system model; new paper work goes to `tcps`. |
| `claude/*` | Working branches for AI-assisted changes | Temporary. Do not base work on them. |

The manuscript branches hold the LaTeX sources, the datasets and the scripts that turn
them into tables; the code that produced the data is on `main`. To work on code and
paper side by side, check the manuscript out next to this repository:

```bash
git worktree add ../rescue-ois-tcps tcps
```

## Names You Will Meet

The work has been renamed as its framing changed, and older files keep older names.

| Name | Meaning |
| --- | --- |
| AAS, Authority-Aligned Sequencing | The approach, as named in the WONS draft. The TCPS manuscript describes it without the acronym. |
| AAL, Authority-Aligned Linearization; authority-aligned synchronization | Earlier names for AAS, in older documents and commits. |
| Tiered Sync | The first name of the prototype's architecture. It survives in the design mock-ups in `preview/` and `ui_kits/`. |
| WONS | The conference draft on branch `paper` (WONS 2027). |
| NCA | The venue of an earlier, double-blind version of the prototype paper (2026); the name appears in old commits. The Android namespace `org.review.rescueois` is left over from anonymizing the code for double-blind review. |
| TCPS | ACM Transactions on Cyber-Physical Systems, the journal the manuscript on `tcps` targets. |
| Command edge, responder edge | The prototype's vehicle roles: the vehicle that accepts the incident's decisions, and the vehicles that queue field submissions and forward them to it. |
| A, B, S, C, OP | The scenario's people: incident commander, deputy (sector North), sector South leader, duty chief at the regional centre, operator. |
| S0 to S5, S3L | Succession policies, from no succession (S0) to pre-authorized deputy activation (S4, S5); S3L is S3 with a lease. S1 is the prototype's policy. [`testbed/README.md`](testbed/README.md#policies) defines each. |
| P-A, P-B, P-C | Partition cases: the commander's handheld cut off; all cellular down while the vehicle mesh stays up; P-B plus the mesh split between commander and deputy. |
| Authoritative, provisional, residual, in doubt | The four statuses of an order, as the people who act on it see them. |

## Repository Map

| Path | Contents | Status |
| --- | --- | --- |
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
  byte), commit the new `results/`, and refresh the manuscript's numbers (below). `FINDINGS.md` interprets the
  committed results; re-read it when they change.
- **Prototype services:** each of the eight Python services under `core/` and `edge/` is
  a package with its own tests; CI runs `ruff check .` and `pytest` in each. The
  end-to-end harnesses need the Docker stack ([`docs/prototype.md`](docs/prototype.md)).
- Pre-commit hooks (`.pre-commit-config.yaml`) run ruff and reject files over 500 KB.

## Working on the Manuscript

The manuscript is on `tcps`; `BUILDING.md` there says how to build it with MiKTeX or TeX
Live. Every testbed number in it is a macro generated from the committed results on
`main`, never typed by hand. With the worktree above, refresh them from `testbed/`:

```bash
python -m aas_testbed latex --out ../../rescue-ois-tcps/data
mv ../../rescue-ois-tcps/data/tab_*.tex ../../rescue-ois-tcps/tables/
```

`data/TESTBED_TRACE.md` on `tcps` traces each number to its CSV, filter and statistic.
The prototype's numbers are traced in `TRACEABILITY.md` on the same branch.

## License

Apache License 2.0. See [`LICENSE`](LICENSE).
