# Mandate seed protocol, version `seed-v0` (normative)

Status, 2026-11-24: an executable specification for a research seed. Written with AI
assistance (Claude); **no person has reviewed the rules or the arguments in this file.**
It is not a deployment design. The arguments in section 10 are candidate arguments
(see `research/claims.csv` for the status of each).

The key words MUST, MUST NOT and MAY are normative. Everything else is explanation.

## 1. Question and scope

> When an old authority holder can still present valid credentials to disconnected
> devices, under what conditions can authority expire and pass to a successor without
> overlapping acceptance of commands from different holders, and what interruption of
> legitimate service is unavoidable?

`seed-v0` covers one authority scope (one set of verifiers that obey one holder at a
time), a **fixed** set of officers and keys, and **no autonomous deputy fallback**
(`F = 0`). Membership change, deputies, several scopes and key revocation are out of
scope (section 11).

## 2. Principals and trust boundaries

| Principal | What it is | Trusted for |
|---|---|---|
| Officer `u` (a person) | One of `n` people entitled to grant or withdraw consent | Nothing in the protocol; a person's decision is an input |
| Signing agent `S_u` | A service that holds `u`'s private key and applies `u`'s decisions | Following the rules of section 6 if `u` is honest |
| Holder | The officer named in the grant of the current epoch; issues commands | Nothing: a holder may be hostile |
| Verifier `v` | The enforcement module at a device; decides acceptance | Always correct (trusted enforcement), see 2.3 |
| Network | All links between all parties | Nothing: adversarial |

### 2.1 Decisions and automation

An officer's **consent decision** (grant consent to holder `h` for epoch `k`, or withdraw
it) is a human event. **Renewal** is automated: while `u` consents to the holder of
epoch `k`, `S_u` signs renewal requests that satisfy rule O1 without asking `u`.
A **withdrawal is applied** when `S_u` records that it will sign no further renewal of
epoch `k`. The protocol measures time from applied withdrawals only (section 10.3).
Detection of a hostile holder, the human decision and coordination between officers
happen before that instant and are not bounded by this protocol.

### 2.2 Fault budget

At most `f` officers are **compromised** in a run: the adversary holds their keys from
some instant on and can sign anything with them. A compromised officer's agent follows
no rule. The holder can be one of the `f`. All other officers and their agents are
**honest**. An honest agent that loses its durable state (section 6.4) counts as
compromised.

### 2.3 Trusted enforcement

The verifier is part of the device's trusted computing base. The adversary cannot
change its code, its durable state or its clock beyond the bound of section 3, and
cannot make the device act on a command that the verifier did not accept. **A hostile
holder cannot bypass the verifier.** Where enforcement sits in a real device (protection
relay, RTU, gateway) is an open domain question (section 13).

### 2.4 Network

The adversary controls every link: it can delay without bound, drop, reorder, replay
and inject any message it can construct. It cannot forge a signature of an honest
officer. Safety properties (10.2, 10.3) assume nothing about delivery.

## 3. Time

Real time `t` is a number no party can read. Each honest agent and each verifier `p`
has a clock `C_p` with `|C_p(t) - t| <= eps` for all `t`, and verifier clocks never go
backwards, including across restarts. `eps` must cover clock holdover for the longest
outage the deployment accepts. Clock attacks that break this bound are out of scope.

The executable seed uses integer time units and constant per-party offsets
(`C_p(t) = t + off_p`, `|off_p| <= eps`). Events with equal real time are applied in an
explicit order that each scenario declares (its `seq`); traces record that order.

## 4. Parameters

| Symbol | Meaning | Constraint |
|---|---|---|
| `n`, `f` | officers, maximum compromised | `n >= 3f + 1` |
| `q` | quorum | `q = ceil((n + f + 1) / 2)`, so `2q - n >= f + 1` and `q <= n - f` |
| `H` | horizon: maximum time from a signature to the end time it signs | `H > 0` |
| `g` | guard between epochs | `g > 2 eps` |
| `eps` | clock bound | `eps >= 0` |
| `F` | deputy fallback period | `F = 0` in `seed-v0` |
| `Delta`, `delta` | renewal interval, collection time | availability only (10.4) |

All parameter values used by the executable seed are synthetic.

## 5. Messages and validity

* `Grant(scope, k, h, s)`: epoch `k` belongs to holder `h` from start time `s`.
* `Renewal(scope, k, e)`: epoch `k` is extended to end time `e`.
* `Command(scope, k, h, cid, payload)`: signed by `h` alone; `cid` is unique per
  `(scope, k, h)`.

Each signed message is the canonical encoding of its fields prefixed by a domain tag
(protocol version, message type, scope), so a signature on one type or scope is never
valid for another. A **certificate** is a grant or renewal with signatures. It is
**valid** if it carries valid signatures of at least `q` **distinct** officers of the
configured set on identical contents; duplicate or unknown signers do not count. The
genesis grant `Grant(scope, 1, h_1, s_1)` is valid by configuration.

## 6. Signer rules (honest agent `S_u`)

State, all durable: epoch `E_u` (initially 1), maximum signed end time `M_u`
(initially the largest end time `u` signed before the run), and the set `X_u` of epochs
from which `u` has withdrawn.

* **O1 Renewal.** Sign `Renewal(k, e)` only if `S_u` holds the valid grant of epoch
  `k`, `k = E_u`, `k` is not in `X_u`, `u` consents to the holder of epoch `k`, and
  `e <= C_u + H`. Then set `M_u := max(M_u, e)`.
* **O2 Grant.** Sign `Grant(j, h, s)` only if `j > E_u`, `s >= M_u + g`, and `u`
  consents to `h` as holder. Then set `E_u := j`.
* **O3 Withdrawal.** To withdraw from epoch `k`, add `k` to `X_u`. Never remove it.
* On receipt of a valid grant of epoch `j > E_u`, set `E_u := j`.

O2 advances `E_u` when `u` *signs* a proposal, before any grant of epoch `j` is valid.
Section 9.3 describes the consequence. `seed-v0` keeps this rule unchanged: it is the
anti-double-voting rule on which grant uniqueness rests.

### 6.4 Persistence

`S_u` MUST make the new state durable **before** it releases a signature. After a
restart it MUST reload that state; if the state is lost it MUST NOT sign again (it is
then faulty).

## 7. Holder procedure

The holder of epoch `k` requests renewals every `Delta`, each with
`e = C_holder + H - 2 eps`, and attaches the grant and its newest valid renewal to each
command. A hostile holder may do anything with messages it can construct.

## 8. Verifier rule

A verifier `v` keeps every valid certificate it receives and a durable set of accepted
`(k, h, cid)`. When a command `Command(k, h, cid, payload)` with a valid signature of
`h` arrives at local time `tau = C_v(t)`:

* **D1.** Accept only if `v` holds a valid `Grant(k, h, s)` and a valid
  `Renewal(k, e)` with `s <= tau <= e`, and `(k, h, cid)` was not accepted before.

**Acceptance** is the verifier event `accept(v, t, tau, command)`: `v` durably appends the
command to its acceptance log and only then releases it to the actuator. Acceptance is
not the completion of a physical action, which this protocol does not observe. Every
other outcome is a rejection with a reason (`no-grant`, `not-started`, `expired`,
`replay`, `bad-signature`). The certificate store MAY be volatile: losing certificates
only removes acceptances.

## 9. Procedures

These are procedures that use the rules; they add no rule.

### 9.1 Prepared handover at time `T`

From `T - H` on, the holder requests only end times `<= T`. Then `M_u <= T` for every
honest signer, and a grant of epoch `k + 1` can start at `T + g`.

### 9.2 Removal

Officers withdraw (O3). A proposer `p` then proposes `Grant(j, h', s)` with
`j = E_p + 1` and `s = C_p + H + g + 2 eps`; every honest signer that withdrew before the
proposal satisfies `s >= M_u + g`.

### 9.3 Split vote and recovery

If honest signers sign *different* proposals for the same epoch `j` and no proposal
reaches `q` signatures, epoch `j` can never get a valid grant (each honest signer votes
once per epoch), and every signer that voted has `E_u = j` and can no longer renew epoch
`j - 1`. Service stops when the newest renewal of `j - 1` expires. This is a progress
gap, not a safety violation. Recovery needs a proposal for an epoch `j' > j` under the
assumptions of 10.5. `seed-v0` gives no mechanism that achieves those assumptions.

## 10. Properties

### 10.1 Terms

For epoch `k`, an acceptance of epoch `k` is an acceptance of a command with epoch `k`.
`gamma = g - 2 eps`.

### 10.2 Separation (exclusive succession)

For any acceptances `a` of epoch `k` at real time `t` and `a'` of epoch `j > k` at real
time `t'` (at the same or different verifiers): `t' - t >= gamma`. Because each epoch
has at most one valid grant, acceptances of different holders are at least `gamma` apart.

### 10.3 Withdrawal-to-expiry

Let `W` be a set of `n - q + 1` honest agents, each of which has applied withdrawal from
epoch `k` or advanced past it, and let `t_W(k)` be the instant the last of them did so
(signatures made at that same instant before it count as earlier). Then no verifier
accepts a command of epoch `k` at real time `t > t_W(k) + H + 2 eps`.

The bound starts at `t_W(k)`, not at compromise. Detection delay and human decision
delay come before `t_W(k)` and are reported separately.

### 10.4 Fresh-command availability (conditional, universal)

Let the officers be honest and consent to the holder `c` of epoch `k`. Assume: (i)
communication and eligibility: every renewal request that `c` starts at real time `t_r`
reaches at least `q` honest agents with `E_u = k` that hold the grant of epoch `k`, and
their signatures reach `c` by `t_r + delta`; (ii) the newest request completed before
the outage started at `t_r >= t_0 - Delta - delta`; (iii) `t_0 >= s + eps`. If from `t_0`
only `c` and verifier `v` exchange messages, then `v` accepts every fresh command that
`c` creates and delivers to `v` at a real time in
`[t_0, t_0 + H - Delta - delta - 4 eps]`.

### 10.5 Conditional recovery

A grant proposal `Grant(j, h, s)` made at `t_R` becomes valid if: (D) delivery: it
reaches at least `q` honest agents and their signatures return to the proposer;
(Q) quorum-readiness: those agents consent to `h`, have `E_u < j` and `M_u + g <= s` when
they receive it; and (C) coordination: none of them signed another proposal of epoch
`j` before. Commands of `h` are then accepted from `s` at verifiers that receive the
grant and a renewal of epoch `j`. Under permanent adversarial blocking no protocol makes
progress, so no unconditional recovery statement exists.

### 10.6 Lower-bound witness (existential)

**Isolation reach** `P` at `v`: *some* run in which all officers are honest and, from
`t_0`, only the holder `c` and `v` exchange messages, contains an acceptance at `v` of a
command **created** by `c` at or after `t_0 + P`. (A command created before `t_0` and
delivered late does not count.) If a protocol has isolation reach `P`, there is a run in
which `c` is compromised at `t_0`, all other officers apply withdrawal at `t_0`, and `v`
accepts the same commands at the same times: `v` receives the same messages in both
runs. This says that *some* run has hostile tenure `P`; it does not say that service
continues in *every* run. 10.4 is the universal statement.

## 11. What is not guaranteed

* **Semantic safety.** A holder may issue wrong, contradictory or dangerous commands
  while authorized. Exclusivity says nothing about content.
* **Anti-equivocation within a term.** A holder may send different commands to
  different verifiers.
* **Damage bounds.** The bound of 10.3 is in time, not in physical effect.
* **Key revocation.** Expiry ends an epoch; it does not revoke a person's key. A
  compromised officer stays compromised for the life of the configuration.
* **Unconditional progress** (10.5), **verifier compromise**, **clock attacks** beyond
  `eps`, **membership change**, **deputy fallback**.

## 12. Communication during an outage

The outage model keeps one local path: the holder can reach the verifiers on its side
(for example a control-centre console and the devices it reaches by a surviving link).
No path to a quorum of agents exists. If a quorum of agents is on the holder's side,
renewals continue and no expiry occurs. A person at the device (a local control switch)
is an input outside this model; it is the only input that 10.6 does not cover.

## 13. Open domain questions (power-grid example)

No utility, operator or power engineer has been consulted. Open: which operations must
continue when a control room is isolated from the other officers; where enforcement
would sit; who may authorize removal of an operator; how long a substation clock holds
`eps` without satellite time; how local control interacts with remote authority.

## 14. Rule sets in the executable seed

| Identifier | Meaning |
|---|---|
| `seed-v0` | This file: O1 to O3, persistence, D1 with replay protection, `F = 0` |
| `orig-2026-11-11` | The rules of the 11 November 2026 draft as written, including the deputy rule D2 with an anchor (`F > 0`). Kept to reproduce its witnesses |
| `tc` | Baseline: threshold-issued expiring credentials with no exclusive-succession rule (a mechanism abstraction, not URSA or HRCred) |
| `xl` | Comparator: exclusive quorum leases with signed, windowed certificates; our adaptation of Nerio's crash-fault grant rule to Byzantine quorums (not evaluated by Nerio's authors) |
| `qo-w` | Comparator: a quorum signs each command, with a validity window `W` and no verifier challenge |

Deliberately broken variants for negative controls are listed in `tests/README.md`.

## 15. Changes from the 11 November 2026 draft

* `F = 0` only; the deputy rule D2 and deputy exposure leave the core claims.
* The tenure bound is anchored at `t_W(k)` for a particular epoch, not at compromise.
* Isolation reach (existential) and fresh-command availability (universal) are separate.
* Availability requires communication and same-epoch eligibility, not only consent.
* Replay protection is part of D1; persistence-before-release is required.
* The split-vote stall of O2 is documented (9.3) and kept as a regression fixture.
