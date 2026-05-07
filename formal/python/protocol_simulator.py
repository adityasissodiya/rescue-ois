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
