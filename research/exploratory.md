# Exploratory material: the deputy rule of the 11 November 2026 draft

Status, 2026-11-24: historical and exploratory. The deputy rule D2 (fallback to a deputy
for a period F > 0 after the last renewal expires at a device) is **not** part of the
seed-v0 claims. This note keeps its unresolved analysis so it is not lost.

## The draft's claims

The draft (preserved in `paper/history/2026-11-11-hostile-commander/sections/07_analysis.tex`,
Proposition "Fallback") stated for F > 0: (1) at one clock time, one device accepts orders
of at most one officer; (2) per epoch, a device accepts the deputy only in one interval
of length F; (3) acceptances of different epochs are at least g - 2 eps apart. It also
stated a deputy exposure of at most F + 2 eps per epoch and device, and a matching lower
bound ("timeout takeover").

## Same-clock-reading witness (part 1 is false as stated)

Fixture `ORIG-DEPUTY-SAME-READING` (`experiments/scenarios.py`, rules `orig-2026-11-11`,
n = 4, f = 1, H = 100, g = 1, eps = 0, F = 20):

1. The device holds the genesis grant (holder A, deputy B) and renewal R(1, 100).
   R(1, 130) exists but the adversary holds it back.
2. At reading 110 the deputy's order arrives. D2 holds: no renewal ends at or after 110,
   the anchor is 100, and 100 < 110 <= 120. The device accepts B and fixes the anchor.
3. At the same reading the adversary delivers R(1, 130).
4. At the same reading the commander's order arrives. D1 holds (0 <= 110 <= 130). The
   device accepts A.

The checker reports `SAME-READING-TWO-ISSUERS` (and `SEPARATION`). The draft's proof
evaluated D1 and D2 in one device state; between the two acceptances the state changed.
A check of simultaneous predicates in one state misses the intervening delivery.

## What remains unresolved

* Whether a repaired D2 (for example: after a deputy acceptance in epoch k, reject the
  commander of epoch k for 2 eps + g, or require the deputy's orders to carry the anchor
  renewal) gives part 1, and at what cost.
* The draft's per-device exposure bound counted one interval per device and epoch; across
  devices, deputy and commander can be accepted at the same real time at different
  devices (the draft says so). The relation between the per-device statement and a
  system-wide exposure statement was not settled.
* The deputy lower bound used the same substitution argument as the holder bound; it was
  not re-examined in this pass.

None of this affects seed-v0, which has F = 0 and no D2.
