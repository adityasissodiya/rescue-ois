"""Pure-Python mirror of formal/tla/RescueOIS.tla.

The simulator implements the same state space and the same operations
as the TLA+ model. Hypothesis state-machine tests in ./tests/ generate
schedules and verify that the simulator preserves SingleAuthority,
NoForkedJournal, and LocalIdempotency under arbitrary interleavings.

Two promotion variants are supported (strict / weak), matching the TLA+
StrictPromotion constant. Tests run both; the strict variant must hold,
the weak variant is expected to admit counterexamples (and we assert
that Hypothesis finds at least one).

Single-journal model: there is one incident journal whose write
authority is held by at most one vehicle at a time. Each vehicle has a
local cursor representing its belief of the next event_seq. Strict
promotion atomically transfers authority and refreshes the new
authority's cursor. Weak promotion does not revoke unreachable old
authorities, so two vehicles can simultaneously believe they hold
authority with cursors pointing at the same journal position.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


Role = Literal["command", "responder"]


@dataclass(frozen=True)
class Event:
    seq: int
    cid: str
    by: str


@dataclass
class ProtocolState:
    """Mutable protocol state. One instance per Hypothesis run."""

    vehicles: tuple[str, ...]
    role: dict[str, Role]
    journal: list[Event]
    cursor: dict[str, int]
    authority: set[str]
    partition: set[tuple[str, str]]  # symmetric, irreflexive
    strict_promotion: bool

    @classmethod
    def init(
        cls,
        vehicles: tuple[str, ...],
        initial_command: str,
        strict_promotion: bool,
    ) -> "ProtocolState":
        assert initial_command in vehicles
        return cls(
            vehicles=vehicles,
            role={v: ("command" if v == initial_command else "responder") for v in vehicles},
            journal=[],
            cursor={v: 1 for v in vehicles},
            authority={initial_command},
            partition=set(),
            strict_promotion=strict_promotion,
        )

    def connected(self, v: str, w: str) -> bool:
        return (v, w) not in self.partition

    def journal_cids(self) -> set[str]:
        return {e.cid for e in self.journal}

    def commands(self) -> set[str]:
        return {v for v in self.vehicles if self.role[v] == "command"}

    def commit_event(self, v: str, cid: str) -> bool:
        """Returns True if the action took place."""
        if v not in self.authority:
            return False
        if cid in self.journal_cids():
            return False
        self.journal.append(Event(seq=self.cursor[v], cid=cid, by=v))
        self.cursor[v] += 1
        return True

    def promote(self, v: str) -> bool:
        if self.role[v] != "responder":
            return False
        commands = self.commands()
        if self.strict_promotion:
            for w in commands:
                if not self.connected(v, w):
                    return False
            for w in commands:
                self.role[w] = "responder"
            self.role[v] = "command"
            self.authority = {v}
        else:
            for w in commands:
                if self.connected(v, w):
                    self.role[w] = "responder"
            self.role[v] = "command"
            self.authority = {w for w in self.authority if not self.connected(v, w)} | {v}
        self.cursor[v] = len(self.journal) + 1
        return True

    def partition_pair(self, v: str, w: str) -> bool:
        if v == w:
            return False
        if (v, w) in self.partition:
            return False
        self.partition.add((v, w))
        self.partition.add((w, v))
        return True

    def heal_pair(self, v: str, w: str) -> bool:
        if (v, w) not in self.partition:
            return False
        self.partition.discard((v, w))
        self.partition.discard((w, v))
        return True

    def check_single_authority(self) -> bool:
        return len(self.authority) <= 1

    def check_no_forked_journal(self) -> bool:
        seqs = [e.seq for e in self.journal]
        return len(set(seqs)) == len(seqs)

    def check_local_idempotency(self) -> bool:
        cids = [e.cid for e in self.journal]
        return len(set(cids)) == len(cids)

    def check_single_command(self) -> bool:
        return len(self.commands()) <= 1



@dataclass(frozen=True)
class HandoffEvent:
    seq: int
    cid: str
    by: str
    epoch: int


@dataclass
class JournalHandoffState:
    """Two-command-edge model for promotion with journal handoff.

    Each command-capable edge has its own local journal. The core stores the
    forwarded prefix from the current command. A strict promotion is allowed
    only after the candidate has bootstrapped that full prefix, then authority
    moves to the candidate under a fresh epoch. The old command keeps its stale
    epoch knowledge but loses authority, so stale writes are rejected before
    touching any local journal.
    """

    edges: tuple[str, str]
    authority: set[str]
    current_epoch: int
    known_epoch: dict[str, int]
    journals: dict[str, list[HandoffEvent]]
    core_journal: list[HandoffEvent]
    next_seq: dict[str, int]
    seen_cids: set[str]

    @classmethod
    def init(cls, command_edge: str = "edge-a", candidate_edge: str = "edge-b") -> "JournalHandoffState":
        edges = (command_edge, candidate_edge)
        return cls(
            edges=edges,
            authority={command_edge},
            current_epoch=1,
            known_epoch={command_edge: 1, candidate_edge: 0},
            journals={command_edge: [], candidate_edge: []},
            core_journal=[],
            next_seq={command_edge: 1, candidate_edge: 1},
            seen_cids=set(),
        )

    def current_command(self) -> str | None:
        if len(self.authority) != 1:
            return None
        return next(iter(self.authority))

    def try_commit(self, edge: str, cid: str, epoch_header: int | None = None) -> bool:
        """Attempt a write carrying an epoch header.

        Returns True only for the current authority and current epoch. All
        stale, future, duplicate, and non-authority attempts leave every
        journal unchanged, matching the service-path fencing contract.
        """
        if edge not in self.edges:
            return False
        header = self.known_epoch[edge] if epoch_header is None else epoch_header
        if edge not in self.authority:
            return False
        if header != self.current_epoch:
            return False
        if self.known_epoch[edge] != self.current_epoch:
            return False
        if cid in self.seen_cids:
            return False
        seq = self.next_seq[edge]
        event = HandoffEvent(seq=seq, cid=cid, by=edge, epoch=self.current_epoch)
        self.journals[edge].append(event)
        self.next_seq[edge] = seq + 1
        self.seen_cids.add(cid)
        return True

    def forward_to_core(self, edge: str) -> bool:
        """Copy the edge journal prefix to core in event_seq order."""
        if edge not in self.edges:
            return False
        changed = False
        by_seq = {event.seq: event for event in self.core_journal}
        for event in sorted(self.journals[edge], key=lambda item: item.seq):
            existing = by_seq.get(event.seq)
            if existing is None:
                if event.seq != len(self.core_journal) + 1:
                    return changed
                self.core_journal.append(event)
                by_seq[event.seq] = event
                changed = True
            elif existing.cid != event.cid:
                return changed
        return changed

    def bootstrap_from_core(self, edge: str) -> bool:
        """Install the core prefix on a candidate command edge."""
        if edge not in self.edges:
            return False
        local_by_seq = {event.seq: event for event in self.journals[edge]}
        changed = False
        for event in self.core_journal:
            existing = local_by_seq.get(event.seq)
            if existing is not None and existing.cid != event.cid:
                return changed
            if existing is None:
                self.journals[edge].append(event)
                local_by_seq[event.seq] = event
                changed = True
        self.journals[edge].sort(key=lambda item: item.seq)
        self.next_seq[edge] = max(self.next_seq[edge], len(self.journals[edge]) + 1)
        return changed

    def promote_after_handoff(self, candidate: str) -> bool:
        """Strict promotion: full forwarding, bootstrap, fresh epoch, old fence."""
        if candidate not in self.edges or candidate in self.authority:
            return False
        current = self.current_command()
        if current is None:
            return False
        if len(self.core_journal) != len(self.journals[current]):
            return False
        if self.journals[candidate][: len(self.core_journal)] != self.core_journal:
            return False
        self.current_epoch += 1
        self.authority = {candidate}
        self.known_epoch[candidate] = self.current_epoch
        self.next_seq[candidate] = len(self.journals[candidate]) + 1
        return True

    def weak_promote_without_handoff(self, candidate: str) -> bool:
        """Unsafe variant used as a negative control in tests."""
        if candidate not in self.edges:
            return False
        self.current_epoch += 1
        self.authority.add(candidate)
        self.known_epoch[candidate] = self.current_epoch
        return True

    def check_single_current_authority(self) -> bool:
        return len(self.authority) <= 1

    def check_no_forked_journal(self) -> bool:
        by_seq: dict[int, HandoffEvent] = {}
        for journal in self.journals.values():
            for event in journal:
                existing = by_seq.get(event.seq)
                if existing is None:
                    by_seq[event.seq] = event
                elif existing.cid != event.cid:
                    return False
        return True

    def check_candidate_suffix_extension(self) -> bool:
        """Every local journal must preserve the forwarded core prefix."""
        for journal in self.journals.values():
            for event in journal:
                if event.seq <= len(self.core_journal):
                    if self.core_journal[event.seq - 1].cid != event.cid:
                        return False
            seqs = [event.seq for event in journal]
            if seqs != list(range(1, len(seqs) + 1)):
                return False
        return True
