---------------------------- MODULE RescueOIS ----------------------------
(***************************************************************************)
(* Rescue OIS protocol abstraction.                                        *)
(*                                                                         *)
(* Models a single incident journal whose write authority is held by at    *)
(* most one vehicle at a time. The journal is a single global sequence;    *)
(* each vehicle keeps a local cursor representing its belief of the next   *)
(* event_seq to allocate. Strict promotion atomically revokes the prior    *)
(* authority and refreshes the new authority's cursor against the journal. *)
(* Weak promotion does not revoke unreachable prior authorities, so two    *)
(* vehicles can simultaneously hold authority with cursors pointing at the *)
(* same journal position -- producing a forked seq under partition.        *)
(*                                                                         *)
(* Companion: formal/python/protocol_simulator.py mirrors this model       *)
(* operationally for Hypothesis property tests.                            *)
(***************************************************************************)

EXTENDS Naturals, FiniteSets, Sequences, TLC

CONSTANTS
    Vehicles,           \* set of vehicle identifiers (model values)
    MaxJournal,         \* upper bound on incident journal length
    ClientIds,          \* set of client_event_id values (model values)
    StrictPromotion     \* TRUE for the safe protocol; FALSE for the broken
                        \* variant that we explicitly do not adopt

ASSUME
    /\ Vehicles # {}
    /\ MaxJournal \in Nat \ {0}
    /\ ClientIds # {}
    /\ StrictPromotion \in BOOLEAN

VARIABLES
    role,        \* [Vehicles -> {"command", "responder"}]
    journal,     \* Seq([seq: Nat, cid: ClientIds, by: Vehicles])
                 \*   single shared incident journal.
    cursor,      \* [Vehicles -> Nat]
                 \*   each vehicle's local belief of the next seq to allocate.
                 \*   Refreshed against Len(journal)+1 on promotion.
    authority,   \* SUBSET Vehicles
                 \*   set of vehicles currently holding write authority.
                 \*   Strict run keeps |authority| <= 1 globally.
    partition    \* SUBSET (Vehicles \X Vehicles); symmetric, irreflexive

vars == <<role, journal, cursor, authority, partition>>

Event == [seq: 1..(MaxJournal + 1), cid: ClientIds, by: Vehicles]

(***************************************************************************)
(*  Helpers                                                                *)
(***************************************************************************)

Connected(v, w) == <<v, w>> \notin partition

JournalCids == { journal[k].cid : k \in 1..Len(journal) }

(***************************************************************************)
(*  Type invariant                                                         *)
(***************************************************************************)

TypeOK ==
    /\ role \in [Vehicles -> {"command", "responder"}]
    /\ journal \in Seq(Event)
    /\ Len(journal) <= MaxJournal
    /\ cursor \in [Vehicles -> 1..(MaxJournal + 1)]
    /\ authority \subseteq Vehicles
    /\ partition \subseteq (Vehicles \X Vehicles)
    /\ \A v \in Vehicles: <<v, v>> \notin partition
    /\ \A v, w \in Vehicles: <<v, w>> \in partition <=> <<w, v>> \in partition

(***************************************************************************)
(*  Init: exactly one vehicle starts as command and holds authority,       *)
(*  full connectivity, empty journal, all cursors at 1.                    *)
(***************************************************************************)

Init ==
    /\ \E v \in Vehicles:
        /\ role = [w \in Vehicles |-> IF w = v THEN "command" ELSE "responder"]
        /\ authority = {v}
    /\ journal = << >>
    /\ cursor = [v \in Vehicles |-> 1]
    /\ partition = {}

(***************************************************************************)
(*  Action: an authority-holding vehicle commits a fresh event using its   *)
(*  local cursor.                                                          *)
(*                                                                         *)
(*  Idempotency on cid is enforced by the precondition that cid is not     *)
(*  already in the (single) journal.                                       *)
(***************************************************************************)

CommitEvent(v, cid) ==
    /\ v \in authority
    /\ Len(journal) < MaxJournal
    /\ cid \notin JournalCids
    /\ journal' = Append(journal, [seq |-> cursor[v], cid |-> cid, by |-> v])
    /\ cursor' = [cursor EXCEPT ![v] = @ + 1]
    /\ UNCHANGED <<role, authority, partition>>

(***************************************************************************)
(*  Action: operator promotes a responder to command.                      *)
(*                                                                         *)
(*  Strict: requires every current command be reachable from v. All        *)
(*  current commands are demoted; v becomes the sole authority; v's       *)
(*  cursor is refreshed to Len(journal)+1.                                 *)
(*                                                                         *)
(*  Weak: only reachable commands are demoted. v is added to authority.   *)
(*  Unreachable previous authorities retain their authority -- this is    *)
(*  the broken variant. v's cursor is refreshed; previous cursors are     *)
(*  untouched, so unreachable old authorities continue from their stale   *)
(*  view.                                                                  *)
(***************************************************************************)

PromoteWeak(v) ==
    /\ role[v] = "responder"
    /\ role' = [w \in Vehicles |->
        IF w = v
            THEN "command"
            ELSE IF role[w] = "command" /\ Connected(v, w)
                THEN "responder"
                ELSE role[w]]
    /\ authority' = { w \in authority : ~Connected(v, w) } \cup {v}
    /\ cursor' = [cursor EXCEPT ![v] = Len(journal) + 1]
    /\ UNCHANGED <<journal, partition>>

PromoteStrict(v) ==
    /\ role[v] = "responder"
    /\ \A w \in Vehicles: role[w] = "command" => Connected(v, w)
    /\ role' = [w \in Vehicles |->
        IF w = v
            THEN "command"
            ELSE IF role[w] = "command"
                THEN "responder"
                ELSE role[w]]
    /\ authority' = {v}
    /\ cursor' = [cursor EXCEPT ![v] = Len(journal) + 1]
    /\ UNCHANGED <<journal, partition>>

Promote(v) ==
    IF StrictPromotion THEN PromoteStrict(v) ELSE PromoteWeak(v)

(***************************************************************************)
(*  Action: partition or heal a single (unordered) pair.                   *)
(***************************************************************************)

PartitionPair(v, w) ==
    /\ v # w
    /\ <<v, w>> \notin partition
    /\ partition' = partition \cup {<<v, w>>, <<w, v>>}
    /\ UNCHANGED <<role, journal, cursor, authority>>

HealPair(v, w) ==
    /\ <<v, w>> \in partition
    /\ partition' = partition \ {<<v, w>>, <<w, v>>}
    /\ UNCHANGED <<role, journal, cursor, authority>>

(***************************************************************************)
(*  Next-state                                                             *)
(***************************************************************************)

Next ==
    \/ \E v \in Vehicles, cid \in ClientIds: CommitEvent(v, cid)
    \/ \E v \in Vehicles: Promote(v)
    \/ \E v, w \in Vehicles: PartitionPair(v, w)
    \/ \E v, w \in Vehicles: HealPair(v, w)

Spec == Init /\ [][Next]_vars

(***************************************************************************)
(*  Safety invariants.                                                     *)
(***************************************************************************)

\* Central authority property: at most one vehicle holds write authority at
\* any time. Under StrictPromotion = TRUE this holds; under
\* StrictPromotion = FALSE TLC will produce a counterexample at depth 3.
SingleAuthority == Cardinality(authority) <= 1

\* Journal-shape property: the incident journal is not forked. Distinct
\* positions in the journal carry distinct event_seq values. Under
\* StrictPromotion = TRUE this is automatic-by-construction (single cursor
\* in use at any time). Under StrictPromotion = FALSE TLC will produce a
\* counterexample where two authorities each commit at the same seq -- the
\* split-brain-on-cursor pattern.
NoForkedJournal ==
    \A i, j \in 1..Len(journal):
        i # j => journal[i].seq # journal[j].seq

\* Local idempotency: no cid appears twice in the journal. Trivially
\* preserved by CommitEvent's precondition; included as a model sanity
\* check.
LocalIdempotency ==
    \A i, j \in 1..Len(journal):
        i # j => journal[i].cid # journal[j].cid

\* Auxiliary: at most one vehicle in the command role. Under strict
\* promotion this holds globally; under weak promotion TLC exhibits a
\* counterexample (partitioned-and-promoted side keeps its command role).
SingleCommand ==
    Cardinality({ v \in Vehicles : role[v] = "command" }) <= 1

(***************************************************************************)
(*  Symmetry: vehicle identifiers are interchangeable. Used by the strict  *)
(*  config to collapse the state space; not used by the weak config so    *)
(*  the shortest counterexample trace is preserved.                        *)
(***************************************************************************)

VehicleSymmetry == Permutations(Vehicles)

============================================================================
