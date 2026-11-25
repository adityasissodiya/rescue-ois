# Hostile-commander draft of 11 November 2026 (historical record)

Copied here on 2026-11-24, unchanged, at the start of the SRDS seed pass. It is **not
maintained and not built**: its `\input` paths point to files one and two levels up
(`data/testbed_macros.tex`, `sections/`). The same files are in the private ref
`refs/snapshots/pre-seed-2026-11-24` (see `research/migration.md`).

`model/mandate_sim.py` is the random-test script of that draft. It was moved here (not
copied) because `src/mandate/`, `sim/` and `experiments/` replace it.

Known problems found in the seed pass (details in `research/claims.csv`,
`research/positioning.md` and `research/exploratory.md`):

* Gap G4 ("no removal rule tolerates hostile officers without a message to the device")
  is false: URSA (2004) removes nodes by collective renewal and expiry.
* Definition "outage tolerance" counts a command created before the outage and delivered
  late; the seed's isolation reach counts only commands created after `t0 + P`.
* The tenure theorem starts at an informal "stop of renewals"; the seed anchors the bound
  at the withdrawal instant `t_W(k)`.
* The outage-tolerance theorem assumed that consent is enough; it also needs
  communication and same-epoch eligibility.
* Proposition "Fallback", part 1, is false as stated (same-clock-reading witness,
  fixture `ORIG-DEPUTY-SAME-READING`).
* Rule O2 can stall after a split vote (fixture `ORIG-SPLIT-STALL`); the draft did not
  say so.
* The "random tests" of section 8 had no coverage measurement.
* "Unity of command" is a pairwise condition; it is weaker than the order of epochs.
