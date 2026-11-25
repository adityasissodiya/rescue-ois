# Bounded TLA+ model of seed-v0

`MandateSeed.tla` models the signer rules O1 to O3 and the verifier rule D1 of
`spec/protocol.md` at very small bounds. It is optional evidence: it complements the
directed scenarios and does not replace a reviewed proof. Written 2026-11-24 with AI
assistance; no person has reviewed the model.

## How to run

```bash
make tla-tools          # downloads tla2tools.jar v1.7.4 into .tools/ and checks its SHA-256
make tla                # spec/tla/run_tlc.sh, then spec/tla/summarize.py
```

`run_tlc.sh` runs four configurations and exits nonzero unless each gives its expected
outcome. Logs are saved in `logs/` with absolute paths replaced by `<repo>`.
`summarize.py` turns the logs into `paper/generated/tla_macros.tex`; it also fails if a
log is missing or shows another outcome.

| Configuration | Checks | Expected outcome |
|---|---|---|
| `MandateSeed.cfg` | `TypeOK`, `GrantUnique`, `EpochOrder`, `SameEpochOneHolder`, `WithdrawalExpiry` | no violation within the bounds |
| `MandateSeed_handover.cfg` | `NoHandover` | violated: a handover from epoch 1 to 2 is reachable (non-vacuity) |
| `MandateSeed_stall.cfg` | `NoSplitStall` | violated: the split-vote stall of `spec/protocol.md` s. 9.3 is reachable |
| `MandateSeed_broken.cfg` | `EpochOrder` with `BrokenStartGuard = TRUE` (O2 without `s >= M_u + g`) | violated (negative control) |

## Tool and bounds

* TLC2 version 2.19 of 8 August 2024 (rev. 5a47802), from the `tla2tools.jar` of TLA+
  tools v1.7.4, SHA-256
  `936a262061c914694dfd669a543be24573c45d5aa0ff20a8b96b23d01e050e88`; run with OpenJDK
  21.0.13 (other Java versions untested).
* Bounds in all four configurations: 3 honest signers and 1 Byzantine signer (n = 4,
  f = 1, q = 3), 2 holders, epochs 1 and 2, time 0 to 2, H = 1, G = 1. Symmetry over the
  honest signers. With 4 workers on the 12-core machine we used, the safety run took
  8 minutes 4 seconds in one run and 12 minutes 26 seconds in another, with the same state
  counts. The log is from the second run; the first run's log was overwritten, so its
  time is a note, not a result. The other three took 33 seconds or less. All
  four together took 9 to 14 minutes.
* Larger bounds did not finish: a run with time 0 to 3 and H = 2 grew past 24 million
  distinct states in 25 minutes and was stopped. Its log was not kept, so treat these two
  numbers as a note, not as a result. The state counts of the final run are in
  `logs/MandateSeed.log`.

## Abstractions (each one makes the model smaller; none is proven harmless)

* Exact clocks (`eps = 0`), integer time, so `gamma = G`. The clock-error terms of the
  arguments are not exercised.
* The Byzantine signer's signature is on every message, so a certificate is valid with
  `Q - NumByz` honest signatures. This is the worst case for safety, not for progress.
* An honest renewal signature at time `t` is on `R(k, t + H)` only. Smaller end times,
  which O1 allows, are not modelled, so combinations of signatures from different time
  steps on one smaller end are missing.
* One verifier that receives every valid certificate at once and evaluates D1 at the end
  of every time step. This gives the largest set of acceptances for a given certificate
  history; it does not model delayed delivery to several verifiers (the directed
  scenarios do).
* Grants are only of epoch 2; there is no epoch 3, so recovery after a split vote is not
  in the model.
* No crash, restart or persistence; no replay (D1's replay check is not modelled); one
  scope; fixed membership; `F = 0`.

## What a pass means

Within these bounds and abstractions, every reachable state satisfies the invariants.
It says nothing about larger bounds, about `eps > 0`, or about the abstractions above.
Widening the bounds is open question R4 in `research/roadmap.md`.
