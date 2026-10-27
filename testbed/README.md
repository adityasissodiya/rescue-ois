# AAS succession testbed

An executable form of the scenario and system model (`model/scenario-and-model.tex` on
branch `tcps`; branch `paper` keeps the copy under review). It runs the policy comparison that the WONS
draft (branch `paper`) planned in its section VI-A and the TCPS manuscript (branch
`tcps`) reports: succession policies S0 to S5, partition cases P-A, P-B and P-C, and a
commander who is fit, fit but unreachable by voice, or incapacitated, with sweeps of L
and T. It measures the costs the WONS draft lists, tests every hypothesis cell of that
draft's Table II as a predicate, and searches random link schedules for runs that break
the model's invariants.

The testbed was built against the WONS draft, so section and table numbers here and in
`FINDINGS.md` are that draft's. `FINDINGS.md` says what the results mean for the paper;
`results/REPORT.md` has the numbers.

## Why a simulator, and not the Docker prototype

The prototype has no persons, grants, succession acts or policies (WONS draft, section
III-B), so it can run S1 only. The open questions are also about policy semantics
(who can record when, which decisions end up residual, what settles), not about service
latency. A deterministic discrete-event model answers them for thousands of incidents in
minutes and gives a reproducible trace for every counterexample. It does not replace
running the prototype on several hosts: it has no real network stack, no cryptography,
and its latencies are parameters. Its role is to decide which experiments the prototype must run, and with
which parameters.

## Quick start

Python 3.12 or newer; no runtime dependencies. `pytest` for the tests.

```bash
cd testbed
python -m aas_testbed list                              # the experiments and their questions
python -m aas_testbed run --policy S3 --case P-A --no-voice --decisions   # one incident, traced
python -m aas_testbed run --policy S4 --relay-fault          # the stale-heartbeat counterexample
python -m aas_testbed run --policy S4 --relay-fault --acked  # ... and the proposed fix
python -m aas_testbed all                               # every experiment, then the report (8,950 runs, ~10 min on 4 cores)
python -m aas_testbed all --quick                       # a fifth of the seeds
python -m aas_testbed matrix --seeds 50                 # one experiment
python -m aas_testbed report                            # results/REPORT.md from the CSVs
python -m aas_testbed latex --out <dir>                 # macros, table rows and their trace for the manuscript
python -m pytest
```

The experiments write to `results/` unless given `--out`. `REPORT.md` records the commit
it was generated from and whether `aas_testbed/` had uncommitted changes, so commit code
changes before a run whose results you will commit. For `latex`, "Working on the
Manuscript" in the root README says which directory to pass and where the table rows go.

Every run is deterministic in its seed. A row in any CSV can be replayed with `run` and
the same parameters. A row of `search.csv.gz` is replayed with
`aas_testbed.experiments.search_config(policy, seed, settlement)`, then
`dataclasses.replace(cfg, acked=True)` or `replace(cfg, effect="acceptance")` if the row's
`acked` or `effect` column says so.

## Layout

| File | Contents |
| --- | --- |
| `aas_testbed/model.py` | The journal rules as pure functions: who held command when, the four statuses, and whose records settlement needs |
| `aas_testbed/network.py` | The forest-fire topology, partition cases, link flapping |
| `aas_testbed/policies.py` | S0, S1, S2, S3, S3L, S4, S5 as configuration |
| `aas_testbed/sim.py` | The discrete-event simulation: devices, gossip, heartbeats, enforcement, succession triggers, settlement |
| `aas_testbed/metrics.py` | The truth oracle and the per-run metrics |
| `aas_testbed/experiments.py` | The experiments and a parallel runner |
| `aas_testbed/report.py` | `REPORT.md`, including the Table II hypothesis check |
| `aas_testbed/latex.py` | LaTeX macros and table rows the paper quotes, with a trace of each number to its CSV and filter |
| `FINDINGS.md` | What the results mean for the paper |
| `tests/` | Rule unit tests, the model document's storyboard replayed, invariants |
| `results/` | The CSVs (gzipped above 400 KB, for the pre-commit size check) and `REPORT.md` of the committed run |

## The model

**People and devices.** A (commander) signs on handheld `HA`; B (deputy, sector North) on
vehicle `V2`; S (sector South) on `V3`; C (duty chief) and the operator `OP` at the
regional server `SRV`. `V1` is the unmanned command vehicle; `K12`, `K34`, `K5` are crew
devices that only read. Links: cellular from every vehicle and A's handheld to the server,
Wi-Fi between `HA` and `V1`, and a mesh between the vehicles and crews. Against the model
document's figure we add one mesh link, `V1`-`V3`, so that a handover inside a P-C
partition is possible.

**Records.** Grants, rules, handovers, takeovers, activations, promotions, decisions and
confirmations: signed, immutable, with a per-person sequence number and the signer's GNSS
time. Devices exchange records by gossip on every link that is up (every 2 s by default),
so replication is a grow-only set, as the document specifies. Every device also sends a
heartbeat carrying its user's latest sequence number.

**Rules.** Each device computes who held command when from the authority records it
holds, and classifies every decision as authoritative, provisional, residual or in doubt
(`model.timeline`, `model.classify`). The regional server confirms a decision once it
holds every record that could still change its verdict (`model.required_signers`); a
device marks it authoritative once it holds that confirmation and the records it rests
on.

**Truth.** The oracle applies the same rule to every record ever signed, ordered by true
time. A device's verdict is *misclassified* if it disagrees with truth, other than by
saying "in doubt".

### Modelling choices the document leaves open

Each is marked `MODEL CHOICE` in the code. They are choices, not results, and several are
exactly the points the model document needs to settle.

1. **Silence is measured from heartbeats, by the receiving device, against the sender's
   GNSS timestamp, relayed over any path.** This is the document's "heard nothing from A's
   device, directly or through the regional server".
2. **Presence is the device's by default** (`presence="device"`). A commander who is
   unfit but whose device stays connected is not silent. `presence="person"` models a
   dead-man switch that beats only while the user is fit.
3. **A deputy's activation is valid if its own recorded measurement of silence meets T**
   (nodes are not Byzantine). Truth does not re-derive the silence in true time.
4. **Precedence at equal timestamps:** appointing authority, then handover, then
   activation. A handover by A inside a partition therefore overrules B's later
   activation.
5. **A decision under a grant that was never valid is residual**, with reason
   `no_valid_grant`. The document's residual covers only superseded grants.
6. **A handover passes through the same enforcement as a decision**, so a commander whose
   device has stopped cannot hand over either.
7. **S1 and S2: the operator acts on data silence at the core, or on a voice report that
   A is unfit; only while B reaches the core.** S2 also promotes while A's device is
   reachable (a coordinated promotion), not only after A's lease has run out.
8. **S3: C acts on data silence or a voice report, then calls A** (60 s). A fit commander
   answers (`a_answers_voice`, default true); then nobody acts for 10 minutes.
9. **Settlement.** `strict` reads the document literally: every person named in any
   authority record must be complete up to the decision. `closing` (the default) is our
   refinement: a grant, takeover or promotion overrides everything before it, so only the
   appointing authority, the holders since the latest such act, and their deputies count.
10. **`acked`** (off by default) is a proposed fix, not part of the document: a lease or T'
    runs from the last of the device's own heartbeats that the other side is known to
    have received, instead of from the last time it heard the other side.
11. **`effect="acceptance"`** (off by default) is a proposed fix: a takeover or promotion
    takes effect when the appointee's device accepts it, not when it is signed. The
    appointee accepts as soon as it holds the appointment; an appointment older than the
    one in force can no longer be accepted; and settlement also waits for anyone named in
    an appointment not yet accepted.
12. **Citing is causal.** An acceptance or activation is not checked against the
    timestamp of the appointment or rule it cites: a device can only cite a record it
    holds, and comparing two devices' clocks would misjudge the order by up to eps.

### Policies

| Policy | Device enforcement | Who moves command, on which trigger |
| --- | --- | --- |
| S0 | none | nobody (handovers only) |
| S1 | holder stops after L without the core | operator promotes B once A is silent at the core (or reported unfit) and B reaches the core |
| S2 | as S1 | as S1, but only once the core has not heard A for L + margin, or while A's device is reachable |
| S3 | none | C takes over, appointing B, if A does not answer a voice call |
| S3L | as S1 | as S3 |
| S4 | A stops after T' without B | B activates after A has been silent for T |
| S5 | none | B activates after A has been silent for T |

Defaults: L = 90 s (the prototype's), T = 300 s, T' = T - 60 s, the operator and C react
after 120 s of silence, a voice call takes 60 s, one decision per minute per commander,
outage 1200 s from t = 600 s, then 900 s with every link up.

### Cases and faults

`none`, `P-A` (A's handheld cut off), `P-B` (all cellular down, mesh up), `P-C` (P-B and
the mesh split between A and B), each with A fit (`alive`), fit but unreachable by voice
(`alive, no voice`), or `incapacitated` at the cut. Faults: A's device ignores T'; one-way
links (`mute`, `deaf`); a handover from A to S inside a P-C partition; a store-and-forward
relay that hands A a stale heartbeat of B's (`relay_fault`); A's device lost for good; A's
clock beyond the bound; random flapping on every link (`search`).

## Metrics

Mapped to the list in the WONS draft's section VI-A.

| Paper's metric | Column |
| --- | --- |
| How long A can keep recording | `a_window_s`, `a_capable_frac` |
| Takeover delay | `takeover_delay_s`, `successor`, `takeover_in_outage` |
| Overlap duration | `overlap_s` (whole run), `overlap_outage_s` |
| (its opposite, not in the paper) time with nobody able to record | `headless_outage_s`, `headless_s` |
| Number and status of residual decisions | `residual`, `residual_superseded`, `residual_no_valid_grant`, `in_doubt` |
| Journal completeness over time | `missing_at_heal`, `core_delay_max_s`, `successor_blind` |
| Dependence on core reachability | `used_core`, and the P-B rows |
| Decisions needing manual review | `manual_review` (residual + in doubt) |
| (not in the paper) valid decisions the device refused | `refused_legit` |
| (not in the paper) settlement | `settle_median_s`, `settle_p95_s`, `never_settled` |
| (not in the paper) what crews saw | `reader_flips_to_residual`, `conflicting_orders` |
| (not in the paper) needless takeovers | `needless_takeover` |

Invariants, checked in every run of `search` and in the tests: every device converges to
the same records; no accepted decision is lost; no device ever revokes an authoritative
verdict; final verdicts match truth while clocks stay within the bound; (a), (b) and (c)
never all hold over an outage.

## Limits

- Latencies, gossip and heartbeat periods, reaction times and decision rates are
  parameters, not measurements. Results that depend on them are reported as sweeps.
- Outages have fixed lengths. The rate of needless takeovers under S4 is a step function
  of outage length against T; turning it into an expected cost needs the distribution of
  real outage lengths, which only the rescue service can provide.
- One incident, one commander, one deputy. No mobility model, no radio model, no load.
- No cryptography: signatures are assumed, and so are the non-Byzantine assumptions.
- The search is random, not exhaustive. A clean search is evidence, not proof; TLA+ is
  still the tool for that.
