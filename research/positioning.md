# Positioning record

Written 2026-11-24 with AI assistance (Claude). No person has reviewed this comparison.
Downloaded copies are in `research/cache/` (ignored by Git, never exported).

## 1. The question

> When an old authority holder can still present valid credentials to disconnected
> devices, under what conditions can authority expire and pass to a successor without
> overlapping acceptance of commands from different holders, and what interruption of
> legitimate service is unavoidable?

Setting of the seed (`spec/protocol.md`): n officers (people with signing agents),
at most f of them compromised, n >= 3f + 1; a holder (possibly hostile) issues commands;
verifiers at devices are trusted, have bounded clock error eps and accept or reject each
command locally; the network is adversarial. Authority is a quorum-signed grant of an
epoch plus quorum-signed renewals with end times. One scope, fixed membership, no
deputy fallback (F = 0).

## 2. Summary of the finding

The individual mechanisms are not new, and their composition looks close to known
designs:

1. **Removal by expiry, with no message to the device, already exists.** URSA renews
   tickets collectively by k neighbours, stamps them with an expiration time, and
   misbehaving nodes are "denied of [their] own ticket renewal" (URSA, s. IV, pp. 1052-1053).
   The 11 November 2026 draft's claim G4 (no prior removal mechanism tolerates hostile
   officers without a message to the device) is therefore false and is removed.
2. **Exclusive succession is the grantor-side lease rule.** Nerio's grantors never change
   their assignee before their own finish time (Nerio, s. 3, p. 6). With signatures,
   windows checked at the device and Byzantine quorums, the same rule gives a mechanism
   (`xl`, our construction) that in our directed runs matches Mandate's separation and
   withdrawal-to-expiry behaviour and avoids one of Mandate's progress gaps.
3. **The lower bound is an indistinguishability argument of the CAP and lease kind**
   (Gilbert and Lynch 2002; Gray and Cheriton 1989 for the lease trade-off). We do not
   claim it as new. What may be specific is its statement for hostile authority holders
   (isolation reach versus hostile tenure); priority is unchecked.

Consequence: the seed should not claim a new mechanism. Remaining options are in
`research/roadmap.md`, section "Decision memo".

## 3. Nearest approaches

Status key: **full text** = we read the relevant sections of the paper itself;
**metadata only** = title, authors, venue and abstract from Crossref; nothing about the
content beyond the abstract may be claimed.

### 3.1 Threshold-issued expiring credentials (URSA; HRCred unread)

* Source: H. Luo, J. Kong, P. Zerfos, S. Lu, L. Zhang, "URSA: Ubiquitous and Robust Access
  Control for Mobile Ad Hoc Networks", IEEE/ACM Trans. Networking 12(6):1049-1063, 2004,
  doi:10.1109/TNET.2004.838598. https://web.cs.ucla.edu/~lixia/papers/04TON_URSA.pdf.
  **Full text** (s. III system models, s. IV design: tickets, renewal, revocation;
  PDF pp. 3-6).
* What it provides: a ticket is valid if "certified and unexpired"; "StartTime and
  ExpirationTime define the ticket validity period" (p. 1052). A node near expiry asks its
  one-hop neighbours; each returns a partial ticket only if its monitoring record shows
  good behaviour; k partial tickets combine (threshold signature). A node detected as
  misbehaving "will be denied of its own ticket renewal" (p. 1053). URSA adds an explicit
  revocation service against "intermittent moving attacks" (p. 1054).
* Assumptions: mobile ad hoc network; a threshold k of the system key; neighbours monitor
  behaviour. No notion of a single authorised holder, of exclusive succession, or of a
  device that must obey exactly one holder.
* Difference claimed by the seed: exclusive succession between holders (no overlap of two
  holders' acceptance windows) under Byzantine signers. URSA does not aim for it.
* Falsifier: a threshold-credential system that also prevents overlapping validity of
  credentials of different holders (a signer-side exclusivity rule). HRCred's "revocation
  epochs" (title and abstract) might be one; its s. 4.7 (a pointer from the task brief,
  not checked by us) is unread.
* Our executable abstraction `tc` (`sim/baselines.py`) shows that without an
  exclusivity rule a naive handover overlaps (`CMP-HANDOVER-TC-NAIVE`), while officers who
  wait for expiry by procedure do not (`CMP-HANDOVER-TC-WAIT`). Withdrawal-to-expiry holds
  for `tc` exactly as for Mandate (`CMP-REMOVAL-TC`): it comes from quorum renewal and
  expiry, not from anything specific to Mandate.
* HRCred: H. Zhou, H. Lei, M. Yang, "HRCred: Revocation-Consistent Hardware-Rooted
  Credentials for Cross-Domain Industrial Cyber-Physical Systems", Electronics 15(17):4004,
  2026, doi:10.3390/electronics15174004. **Metadata only**: the publisher refused automated
  download (HTTP 403) on 2026-11-24. Open: threshold issuance, revocation epochs and
  lifetime bounds, s. 4.7 under partition.

### 3.2 Exclusive quorum leases (Nerio; Gray-Cheriton leases)

* Source: R. van Renesse, F. B. Schneider, J. Gehrke, "Nerio: Leader Election and Edict
  Ordering", arXiv:1109.5111v2, 2011 (Cornell eCommons hdl:1813/23631).
  https://arxiv.org/abs/1109.5111. **Full text** (s. 1-3, 6-7; PDF pp. 1-6, 10-12).
* What it provides: each process keeps an assignee A_p, a finish time F_p and an
  expiration E_p; "a process p never changes A_p if C_p < F_p" (p. 6); a grantor ignores a
  request from another process while it still grants to A_q, otherwise sets
  A_q := p, F_q := max(F_q, T_q + (1 + rho) delta) (algorithm OQwBD, p. 6). A process is
  leader iff a quorum grants it a lease (p. 4), giving Leader Uniqueness. Edict Validity is
  enforced by the leader itself: before sending an edict it checks C_p < E_p (s. 7, p. 11).
  Recipients order edicts by quorum timestamps.
* Assumptions: crash failures only; bounded drift (s. 3) or bounded skew (s. 4); no
  signatures; recipients do not check validity themselves.
* What changes under our assumptions: a hostile holder ignores its own expiry, so validity
  must be checked at the device from signed evidence, and Byzantine grantors require
  quorum intersection in an honest signer (q = ceil((n + f + 1)/2)). A signed lease also
  carries a start time, so the grantor needs a floor (S_u) for later leases of the same
  holder; without it a renewal with an early start could overlap another holder's window.
* Composition `xl` (ours, `sim/baselines.py`): sign Lease(h, s, e) only if consent,
  s <= e <= C_u + H, and either h = A_u and s >= S_u, or h != A_u and s >= F_u + g.
  Candidate argument (unreviewed, claim C-XL-1): any two valid leases of different holders
  share an honest signer; its first change of holder after signing the earlier lease
  requires s >= F_u + g >= e + g, and every later signature has start >= that bound; so
  acceptance windows of different holders are at least g - 2 eps apart. Directed runs:
  `CMP-HANDOVER-XL`, `CMP-REMOVAL-XL`, `CMP-ISOLATION-XL` give the same values as Mandate;
  `CMP-SPLIT-SAME-HOLDER-XL` continues where Mandate stalls; `CMP-SPLIT-TWO-HOLDERS-XL`
  stalls like Mandate.
* Falsifier of any Mandate advantage over `xl`: a scenario or proof in which `xl`
  violates separation or withdrawal-to-expiry, or in which Mandate's epochs give a
  property that `xl` lacks (candidates: an explicit epoch name for audit and ordering
  of commands; re-appointment of the same holder as a distinct term). None is shown.
* C. G. Gray, D. R. Cheriton, "Leases: An Efficient Fault-Tolerant Mechanism for
  Distributed File Cache Consistency", SOSP 1989, doi:10.1145/74850.74870: the lease
  trade-off between term length and the effect of failures. **Not re-read** in this pass;
  cited only for the general idea.

### 3.3 Quorum per command and intrusion-tolerant SCADA (Spire)

* Source: A. Babay, T. Tantillo, T. Aron, M. Platania, Y. Amir, "Network-Attack-Resilient
  Intrusion-Tolerant SCADA for the Power Grid", DSN 2018, doi:10.1109/DSN.2018.00036.
  https://sites.pitt.edu/~babay/pubs/scada_DSN_2018.pdf. **Full text** (s. I-III; s. IV
  configuration analysis skimmed).
* What it provides: a SCADA master replicated with intrusion-tolerant replication over
  3f + 2k + 1 replicas in several sites; it tolerates f compromised replicas, one
  disconnected site and one replica in proactive recovery.
* Explicit exclusion (s. III, PDF p. 3): "our threat model does not cover a compromised
  HMI or a rogue operator. Such a compromise can have direct system-wide effects and will
  need to be handled through other mechanisms." It also excludes compromised RTUs and PLCs.
* Difference: the seed's problem is exactly the excluded case (a hostile operator with
  valid credentials). That a paper excludes a case does not show that nobody solved it.
* Related comparator `qo-w` (ours): every command needs q officer signatures with a
  validity window W. Directed runs: in-flight approved commands can be accepted until
  about t_W + W + 2 eps (`CMP-REMOVAL-QO-W`: 19 time units after t_W with W = 20, eps = 1);
  an isolated holder gets no fresh command accepted (`CMP-ISOLATION-QO-W`). So "zero
  hostile tenure" holds only for commands created after withdrawal and only with a
  window or nonce; the fresh variant with a verifier challenge (`qo-n`) is specified in
  the roadmap, not implemented.

### 3.4 Bounded effect after removing a Byzantine client (Liskov and Rodrigues)

* Source: B. Liskov, R. Rodrigues, "Byzantine Clients Rendered Harmless", MIT CSAIL
  Technical Report MIT-CSAIL-TR-2005-047, July 2005 (later ICDCS 2006 as "Tolerating
  Byzantine Faulty Clients in a Quorum System"; the ICDCS version is not re-read).
  https://publications.csail.mit.edu/tmp/MIT-CSAIL-TR-2005-047.pdf. **Full text** of the
  abstract, s. 1-2 and the correctness conditions.
* What it provides: a quorum storage protocol in which a bad client "that has been removed
  from operation" can leave behind at most a bounded number of "lurking writes" (a count,
  not a time), with removal done by an administrator.
* Difference: the replicas enforce the bound and are reachable; the seed's verifiers are
  disconnected devices that must decide alone, and the bound is in time from withdrawal.
* Falsifier: none needed; it is a precedent for bounding a removed principal's residual
  effect, to be cited as such.

### 3.5 Refresh instead of revoke (Shakarami and Sandhu)

* Source: M. Shakarami, R. Sandhu, "Refresh Instead of Revoke Enhances Safety and
  Availability: A Formal Analysis", DBSec 2019, LNCS 11559, pp. 301-313,
  doi:10.1007/978-3-030-22479-0_16 (Crossref, checked 2026-11-24).
  https://profsandhu.com/~profsand/confrnc/misconf/dbsec19-ms.pdf. **Full text** of the
  abstract and s. 1-2.
* What it provides: in multi-authority attribute-based access control, a decision point
  with stale attribute values can grant access that should be denied (a safety violation)
  or deny access that should be granted (an availability violation); refreshing values
  improves both.
* Relation: the same safety/availability tension at a decision point, for attribute
  freshness rather than holder exclusivity. Cite as background for the trade-off.

### 3.6 Also inaccessible

* V. Stantchev, "Authorization That Survives Disconnection: Capability-Based Security and
  Portable Evidence for the Cloud-Fog-Edge Continuum", Future Internet 18(11):598, 2026,
  doi:10.3390/fi18110598. **Metadata only** (HTTP 403 on 2026-11-24). Open: which offline
  verification and availability-exposure claims overlap with the seed.

## 4. SRDS calibration (claim and evidence scale only)

Read to judge what an SRDS paper supports, not to borrow claims:

* L. Lawniczak, T. Distler, "Hard Shell, Reliable Core: Improving Resilience in Replicated
  Systems with Selective Hybridization", SRDS 2025 (full text).
* A. Alyahya, D. Tipper, A. Babay, "Availability Analysis of Network-Attack-Resilient
  Byzantine Fault Tolerant Systems", SRDS 2024 (full text).
* S. Bommareddy et al., "Real-Time Byzantine Resilience for Power Grid Substations",
  SRDS 2022 (full text). Its relay timing requirements are not timing requirements for
  human authorization.
* S. Bommareddy et al., "Tolerating Compound Threats in Critical Infrastructure Control
  Systems", SRDS 2024 (only s. I-II extracted; out-of-band reconfiguration not checked).

Observation: these papers pair a precise model with either proofs or a substantial
implementation and measurement. The seed has neither a reviewed proof nor a system
measurement; it is not submission-ready.

## 5. Venue facts (checked 2026-11-24)

The official site still describes SRDS 2026 (https://srds-conference.org/). Its call:
10 pages excluding references, IEEE two-column, double-blind, optional clearly marked
appendix read at the reviewers' discretion. No 2027 call or deadline was published; none
is assumed here.

## 6. Citation chaining

Done in this pass: only the prioritized sources above and their metadata. Not done
(open, see roadmap R3): backward and forward citations of URSA and Nerio;
Byzantine lease and Byzantine leader-lease literature; capability systems with expiry and
epoch-based revocation in industrial control (including IEC 62351-8 role-based access
control, unread); HRCred s. 4.7 and Stantchev 2026 in full text.
