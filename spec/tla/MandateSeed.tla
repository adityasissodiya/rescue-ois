---------------------------- MODULE MandateSeed ----------------------------
(***************************************************************************)
(* Bounded model of the seed-v0 rules (spec/protocol.md, s. 6 and 8).      *)
(*                                                                         *)
(* Abstractions (all deliberate; see spec/tla/README.md):                  *)
(*  - Exact clocks (eps = 0); integer time 0..MaxTime; gamma = G.          *)
(*  - The Byzantine officers' signatures are on every message, so a        *)
(*    certificate is valid with Q - NumByz honest signatures. This is the  *)
(*    worst case for safety, not for progress.                             *)
(*  - An honest renewal signature at time t is on R(k, t + H) only.        *)
(*  - The network delivers any valid certificate to the verifier at once;  *)
(*    the verifier evaluates D1 at the end of every time step. This is the *)
(*    largest set of acceptances, so it is the worst case for safety.      *)
(*  - One scope, fixed membership, F = 0, no crash or restart.             *)
(***************************************************************************)
EXTENDS Integers, FiniteSets, TLC

CONSTANTS Honest, NumByz, Holders, Genesis, MaxEpoch, MaxTime, H, G, Q,
          BrokenStartGuard

N == Cardinality(Honest) + NumByz
ASSUME /\ N >= 3 * NumByz + 1
       /\ 2 * Q >= N + NumByz + 1 /\ 2 * (Q - 1) < N + NumByz + 1  \* Q = ceil((N+f+1)/2)
       /\ Genesis \in Holders /\ H >= 1 /\ G >= 1 /\ MaxEpoch >= 2

Epochs == 1..MaxEpoch
Starts == 0..(MaxTime + H + G)
GrantMsgs == [ep : 2..MaxEpoch, h : Holders, s : Starts]
NoVote == [ep |-> 0, h |-> Genesis, s |-> 0]
NONE == -1

VARIABLES now,    \* real time = every clock
          E,      \* E[u]: epoch of honest signer u
          M,      \* M[u]: largest end time u signed
          X,      \* X[u]: epochs u withdrew from
          cur,    \* cur[k]: honest signers of R(k, now + H) in this time step
          mve,    \* mve[k]: largest end of a valid renewal of epoch k
          vote,   \* vote[u][j]: the grant of epoch j that u signed, or NoVote
          knows,  \* knows[u]: epochs whose valid grant u holds
          first,  \* first[k][h], last[k][h]: first and last time the verifier
          last,   \*   accepted holder h in epoch k (NONE if never)
          tw      \* tw[k]: time n - q + 1 honest signers had left epoch k

vars == <<now, E, M, X, cur, mve, vote, knows, first, last, tw>>

Perms == Permutations(Honest)

ValidG(g) == Cardinality({u \in Honest : vote[u][g.ep] = g}) + NumByz >= Q
HasGrant(k, h, t) ==
  IF k = 1 THEN h = Genesis
  ELSE \E g \in GrantMsgs : g.ep = k /\ g.h = h /\ g.s <= t /\ ValidG(g)
Acceptable(k, h, t) == HasGrant(k, h, t) /\ mve[k] >= t

Left(k, E2, X2) == {u \in Honest : k \in X2[u] \/ E2[u] > k}
NewTW(E2, X2) ==
  [k \in Epochs |-> IF tw[k] = NONE /\ Cardinality(Left(k, E2, X2)) >= N - Q + 1
                    THEN now ELSE tw[k]]

TypeOK ==
  /\ now \in 0..(MaxTime + 1)
  /\ E \in [Honest -> Epochs]
  /\ M \in [Honest -> 0..(MaxTime + H)]
  /\ X \in [Honest -> SUBSET Epochs]
  /\ mve \in [Epochs -> {NONE} \cup 0..(MaxTime + H)]
  /\ vote \in [Honest -> [Epochs -> GrantMsgs \cup {NoVote}]]
  /\ tw \in [Epochs -> {NONE} \cup 0..MaxTime]

Init ==
  /\ now = 0
  /\ E = [u \in Honest |-> 1]
  /\ M = [u \in Honest |-> 0]
  /\ X = [u \in Honest |-> {}]
  /\ cur = [k \in Epochs |-> {}]
  /\ mve = [k \in Epochs |-> NONE]
  /\ vote = [u \in Honest |-> [j \in Epochs |-> NoVote]]
  /\ knows = [u \in Honest |-> {1}]
  /\ first = [k \in Epochs |-> [h \in Holders |-> NONE]]
  /\ last = [k \in Epochs |-> [h \in Holders |-> NONE]]
  /\ tw = [k \in Epochs |-> NONE]

(* O1: renew the current epoch, if its valid grant is held and u has not withdrawn. *)
SignRenewal(u) ==
  LET k == E[u] IN
  /\ now <= MaxTime
  /\ k \in knows[u] /\ k \notin X[u] /\ u \notin cur[k]
  /\ cur' = [cur EXCEPT ![k] = @ \cup {u}]
  /\ M' = [M EXCEPT ![u] = IF now + H > @ THEN now + H ELSE @]
  /\ mve' = [mve EXCEPT ![k] =
              IF Cardinality(cur'[k]) + NumByz >= Q /\ now + H > @ THEN now + H ELSE @]
  /\ UNCHANGED <<now, E, X, vote, knows, first, last, tw>>

(* O2: vote for one grant of a higher epoch; the person may consent to any holder. *)
SignGrant(u, g) ==
  /\ now <= MaxTime
  /\ g.ep > E[u]
  /\ BrokenStartGuard \/ g.s >= M[u] + G
  /\ vote' = [vote EXCEPT ![u][g.ep] = g]
  /\ E' = [E EXCEPT ![u] = g.ep]
  /\ tw' = NewTW(E', X)
  /\ UNCHANGED <<now, M, X, cur, mve, knows, first, last>>

(* O3: withdraw from the current epoch. *)
Withdraw(u) ==
  /\ now <= MaxTime
  /\ E[u] \notin X[u]
  /\ X' = [X EXCEPT ![u] = @ \cup {E[u]}]
  /\ tw' = NewTW(E, X')
  /\ UNCHANGED <<now, E, M, cur, mve, vote, knows, first, last>>

(* Receipt of a valid grant. *)
Learn(u, g) ==
  /\ now <= MaxTime
  /\ ValidG(g) /\ g.ep \notin knows[u]
  /\ knows' = [knows EXCEPT ![u] = @ \cup {g.ep}]
  /\ E' = [E EXCEPT ![u] = IF g.ep > @ THEN g.ep ELSE @]
  /\ tw' = NewTW(E', X)
  /\ UNCHANGED <<now, M, X, cur, mve, vote, first, last>>

(* End of a time step: the verifier accepts every acceptable (epoch, holder). *)
Tick ==
  /\ now <= MaxTime
  /\ first' = [k \in Epochs |-> [h \in Holders |->
                 IF first[k][h] = NONE /\ Acceptable(k, h, now) THEN now ELSE first[k][h]]]
  /\ last' = [k \in Epochs |-> [h \in Holders |->
                 IF Acceptable(k, h, now) THEN now ELSE last[k][h]]]
  /\ now' = now + 1
  /\ cur' = [k \in Epochs |-> {}]
  /\ UNCHANGED <<E, M, X, mve, vote, knows, tw>>

Next ==
  \/ Tick
  \/ \E u \in Honest : SignRenewal(u) \/ Withdraw(u)
  \/ \E u \in Honest, g \in GrantMsgs : SignGrant(u, g) \/ Learn(u, g)

Spec == Init /\ [][Next]_vars

----------------------------------------------------------------------------
(* Safety properties (spec/protocol.md, s. 10). *)

GrantUnique ==
  \A g1, g2 \in GrantMsgs : (ValidG(g1) /\ ValidG(g2) /\ g1.ep = g2.ep) => g1 = g2

\* Every acceptance of epoch k is at least G before every acceptance of j > k.
EpochOrder ==
  \A k, j \in Epochs, h1, h2 \in Holders :
    (k < j /\ last[k][h1] # NONE /\ first[j][h2] # NONE) => first[j][h2] >= last[k][h1] + G

SameEpochOneHolder ==
  \A k \in Epochs, h1, h2 \in Holders :
    (h1 # h2) => (first[k][h1] = NONE \/ first[k][h2] = NONE)

\* No acceptance of epoch k later than tw[k] + H (eps = 0).
WithdrawalExpiry ==
  \A k \in Epochs, h \in Holders :
    (tw[k] # NONE /\ last[k][h] # NONE) => last[k][h] <= tw[k] + H

(* Non-vacuity: each invariant below is EXPECTED to be violated. *)

\* A handover from epoch 1 to epoch 2 is reachable.
NoHandover == ~(\E h1, h2 \in Holders : last[1][h1] # NONE /\ first[2][h2] # NONE)

\* The split-vote stall of s. 9.3 is reachable: every honest signer has voted in
\* epoch 2, no epoch-2 grant is valid, and epoch 1 has expired.
NoSplitStall ==
  ~( /\ \A u \in Honest : E[u] = 2 /\ vote[u][2] # NoVote
     /\ \A g \in GrantMsgs : g.ep = 2 => ~ValidG(g)
     /\ last[1][Genesis] # NONE /\ mve[1] < now )
=============================================================================
