# Rescue OIS

Research on command succession in rescue-service incident response over intermittent
links. When the incident commander is cut off, who may give orders? How do devices that
cannot reach each other enforce that? And what happens to the orders given meanwhile
once the links return? Authority belongs to people, through signed grants and succession
rules the organization fixes in advance. Vehicles and handhelds only enforce it.

On `main`, [`paper/`](paper/README.md) holds a journal manuscript for ACM Transactions on
Cyber-Physical Systems (TCPS), next to the code and data behind it. On the branch
`srds-2027-seed`, `paper/` holds a working seed for a conference paper instead: how
command authority can end, and pass to a successor, at disconnected devices when the
holder may be hostile. The seed has its own specification, code and evidence; see
[The SRDS Seed](#the-srds-seed).

## Start Here

| You want to | Read | Then run |
| --- | --- | --- |
| Read or reproduce the SRDS seed (a holder who may be hostile) | [The SRDS Seed](#the-srds-seed), then [`paper/README.md`](paper/README.md) | `make venv && make seed` |
| Understand the problem and the current results | The manuscript in [`paper/`](paper/README.md) (introduction and evaluation), then [`testbed/FINDINGS.md`](testbed/FINDINGS.md) | — |
| Run or change the policy experiments | [`testbed/README.md`](testbed/README.md) | `cd testbed && python -m aas_testbed list` |
| Work on the manuscript | [`paper/README.md`](paper/README.md) and [`paper/TCPS_PLAN.md`](paper/TCPS_PLAN.md) | [Working on the manuscript](#working-on-the-manuscript) |
| Run the prototype, or reproduce the WONS draft's numbers | [`docs/prototype.md`](docs/prototype.md) | `RESPONDERS=3 ./scripts/dev-up.sh` |
| Read the prototype's design, or check whether a doc is current | [`docs/README.md`](docs/README.md) | — |

## What Is Here

The repository holds four bodies of evidence. They are easy to confuse, and they differ in
what they can show.

| Part | What it is | What it can show |
| --- | --- | --- |
| **Testbed** ([`testbed/`](testbed/README.md)) | A discrete-event model of a forest-fire incident: succession policies S0 to S5 (and S3 with a lease), three partition cases, a truth oracle and a randomized search for invariant violations. Pure Python, no dependencies; the committed results cover 8,950 simulated incidents. | The evaluation in the TCPS manuscript: policy semantics, counterexamples and the fixes for them. Latencies are parameters, not measurements. |
| **Prototype** ([`core/`](core/), [`edge/`](edge/), [`scripts/`](scripts/)) | An incident information system run as a Docker Compose emulation: a regional core, a command vehicle edge and responder edges, with a CRDT baseline ([`baseline/`](baseline/)) and a Raft baseline ([`baseline-raft/`](baseline-raft/)). | The evaluation in the WONS draft. Implements one policy, S1, and has no notion of a person ([what it does not do](docs/prototype.md#what-the-prototype-does-not-do)). |
| **Formal models** ([`formal/`](formal/)) | A TLA+ model of the prototype's single-writer rule, mirrored by Hypothesis state-machine tests. | Safety of the prototype's rule. No persons, no lease, no relaying yet; the manuscript's two propositions are still to be model-checked. Not a model of the SRDS seed. |
| **SRDS seed** ([`spec/`](spec/protocol.md), `src/mandate/`, `sim/`, `experiments/`, `tests/`) | Rules for ending and passing authority when the holder may be hostile, a rule kernel, a deterministic simulator, directed scenarios with an independent trace checker, and a bounded TLA+ model ([`spec/tla/`](spec/tla/README.md)). | Whether the candidate rules behave as stated in the directed runs and in a small bounded model. Times are synthetic integers: no measurements, and no person has reviewed the arguments. |

## The SRDS Seed

A working seed for a conference paper, on the branch `srds-2027-seed` (November 2026, not
merged into `main`). SRDS 2027 is the candidate venue;
[`research/positioning.md`](research/positioning.md) records what we checked about the
venue and the prior work. The question is when command authority held by a possibly
hostile holder can expire, and pass to a successor, at verifiers that nobody can reach,
without accepting commands of two holders at overlapping times, and what interruption of
loyal service no protocol can avoid.

It is not a submission. The specification, code, paper and arguments were drafted with
an AI assistant (Claude), and no person has reviewed them yet: every lemma and
proposition is a candidate. Every time in the experiments is a synthetic integer.
Nothing measures a real system, and no utility or operator was consulted. The
positioning found that the mechanism is probably not new: it composes threshold-issued
expiring credentials with exclusive leases. [`research/roadmap.md`](research/roadmap.md)
sets out the options and the next experiments, and
[`research/claims.csv`](research/claims.csv) lists every claim with its status and
evidence.

| Path | Contents |
| --- | --- |
| [`spec/protocol.md`](spec/protocol.md) | Normative rules of `seed-v0` (signer rules O1 to O3, verifier rule D1), the candidate properties, and what is not guaranteed |
| `src/mandate/` | Rule kernel, canonical encoding, symbolic and Ed25519 signatures (fixture keys, for tests only), durable store |
| `sim/` | Deterministic simulator and the comparison mechanisms `tc`, `xl` and `qo-w` |
| `experiments/` | Directed scenarios, an independent trace checker, the runner, and the generated `results/` |
| [`tests/`](tests/README.md) | Tests, including the deliberately broken variants that the checker must detect |
| [`spec/tla/`](spec/tla/README.md) | Bounded TLA+ model of `seed-v0`, its configurations and the logs of our run |
| `research/` | Positioning, claim ledger, roadmap, an exploratory note, and the record of this pass (`migration.md`) |
| [`paper/`](paper/README.md) | The seed paper (IEEE conference format), with an anonymous review build |
| `artifact/` | Review export (allowlist and anonymity check) and the diff against the pre-pass baseline |

From the repository root, with Python 3.12 (the paper also needs TeX Live with
`IEEEtran`, and the model check needs Java):

```bash
make venv          # .venv from requirements/seed.lock, hash-checked
make seed          # lint, tests and all directed scenarios; nonzero exit on any failure
make tla-tools     # pinned tla2tools.jar, SHA-256 checked (needs network)
make tla           # optional: bounded model check, 9 to 14 minutes with 4 workers
make paper         # paper/build/main.pdf and its main-text page count
make paper-anon    # paper/build/main-anon.pdf, the anonymous review build
make export        # artifact/out/review/ and review.tar.gz: allowlisted, anonymized, checked
make review-diff   # every change of the pass against the local baseline ref
```

None of these runs Docker or the legacy harnesses. The 11 November 2026 draft of this
paper is kept unchanged, with a list of its known problems, in
[`paper/history/2026-11-11-hostile-commander/`](paper/history/2026-11-11-hostile-commander/README.md).

## One Branch

> November 2026: the SRDS seed is on a second branch, `srds-2027-seed`, made from
> `3ebd585` and not merged into `main`. The rest of this section records the October 2026
> merge.

Everything is on `main`, and new work goes there; CI runs on every push to it. Until
October 2026 the manuscript (`tcps`), the WONS conference draft (`paper`) and AI-assisted
changes (`claude/*`) had branches of their own. They were merged into `main` with their
history, then deleted:

- The manuscript is in [`paper/`](paper/README.md), with the scenario and system model
  document in `paper/model/` and the prototype's datasets in `paper/data/`.
- The WONS draft, as it was left, is commit
  [`d1b1eca`](https://github.com/adityasissodiya/rescue-ois/tree/d1b1ecae7d57aaf98d8348928c3e6f2704a954e1)
  (`git worktree add ../wons-draft d1b1eca` checks it out next to this repository).
- Commit hashes from the old branches still resolve: every one of those commits is in
  `main`'s history.

## Names You Will Meet

The work has been renamed as its framing changed, and older files keep older names.

| Name | Meaning |
| --- | --- |
| AAS, Authority-Aligned Sequencing | The approach, as named in the WONS draft. The TCPS manuscript describes it without the acronym. |
| AAL, Authority-Aligned Linearization; authority-aligned synchronization | Earlier names for AAS, in older documents and commits. |
| Tiered Sync | The first name of the prototype's architecture. It survives in the design mock-ups in `preview/` and `ui_kits/`. |
| WONS | The conference draft for WONS 2027, kept as commit `d1b1eca`. |
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
| [`paper/`](paper/README.md) | On `main`: the TCPS manuscript (`acmart`), the system model document (`model/`), the prototype's datasets and the scripts that turn them into tables. On `srds-2027-seed`: the seed paper (`IEEEtran`) and its generated numbers, the 11 November 2026 draft in `history/`, and the TCPS files other than its sources | Seed: working draft. TCPS: see `main` |
| [`spec/`](spec/protocol.md), `src/mandate/`, `sim/`, `experiments/`, [`tests/`](tests/README.md) | The SRDS seed's specification, kernel, simulator, scenarios, checker, results and tests | Seed (new in November 2026) |
| [`spec/tla/`](spec/tla/README.md) | Bounded TLA+ model of the seed's rules | Seed; bounded, see its README |
| `research/` | The seed's positioning, claim ledger and roadmap | Seed |
| `artifact/`, `Makefile`, `requirements/seed.*`, `ruff-seed.toml` | The seed's review export and checks, commands, pinned dependencies and lint settings | Seed |
| [`testbed/`](testbed/) | Succession testbed: model, simulator, experiments, results, findings | Current; CI runs its tests |
| [`core/`](core/) | Regional core services and database migrations | Prototype; measured in Docker |
| [`edge/`](edge/) | Vehicle-edge services (`ops-api`, `syncd`, local Postgres with outbox and journal) and WireGuard, Nginx and nftables configuration | Prototype; measured in Docker |
| [`scripts/`](scripts/) | Docker stack helpers, promotion script, evaluation harnesses | Prototype |
| [`baseline/`](baseline/) | CRDT-LWW baseline service and its harness | Prototype baseline |
| [`baseline-raft/`](baseline-raft/) | Three-voter Raft baseline (Go `raftd`) | Prototype baseline |
| [`formal/`](formal/) | TLA+ model (`tla/`) and Hypothesis mirrors (`python/`) | Covers the prototype's rule, not the seed |
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

On `srds-2027-seed`, `paper/` is the seed paper. Build it with `make paper` and
`make paper-anon`; [`paper/BUILDING.md`](paper/BUILDING.md) has the details. The rest of
this section is about the TCPS manuscript, whose sources are at `3ebd585`.

`paper/BUILDING.md` as of `3ebd585` says how to build the TCPS manuscript with MiKTeX or
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
