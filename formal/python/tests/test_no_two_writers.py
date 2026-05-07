"""Hypothesis state-machine test for the single-journal safety invariants.

Mirrors formal/tla/RescueOIS.tla. The strict machine must preserve
SingleAuthority, NoForkedJournal, and LocalIdempotency under any
interleaving of commit/promote/partition/heal. The weak variant admits
a hand-built counterexample showing that without atomic authority
revocation, two vehicles each commit at the same event_seq -- the
split-brain-on-cursor pattern.
"""

from __future__ import annotations

from hypothesis import settings, strategies as st
from hypothesis.stateful import RuleBasedStateMachine, invariant, rule

from protocol_simulator import ProtocolState


VEHICLES = ("v1", "v2", "v3")
CIDS = ("c1", "c2", "c3")
MAX_JOURNAL = 3


class StrictMachine(RuleBasedStateMachine):
    def __init__(self) -> None:
        super().__init__()
        self.state = ProtocolState.init(VEHICLES, initial_command="v1", strict_promotion=True)

    @rule(v=st.sampled_from(VEHICLES), cid=st.sampled_from(CIDS))
    def commit(self, v: str, cid: str) -> None:
        if len(self.state.journal) < MAX_JOURNAL:
            self.state.commit_event(v, cid)

    @rule(v=st.sampled_from(VEHICLES))
    def promote(self, v: str) -> None:
        self.state.promote(v)

    @rule(v=st.sampled_from(VEHICLES), w=st.sampled_from(VEHICLES))
    def partition(self, v: str, w: str) -> None:
        self.state.partition_pair(v, w)

    @rule(v=st.sampled_from(VEHICLES), w=st.sampled_from(VEHICLES))
    def heal(self, v: str, w: str) -> None:
        self.state.heal_pair(v, w)

    @invariant()
    def single_authority(self) -> None:
        assert self.state.check_single_authority(), (
            f"SingleAuthority violated: authority={self.state.authority} "
            f"role={self.state.role} partition={self.state.partition}"
        )

    @invariant()
    def no_forked_journal(self) -> None:
        assert self.state.check_no_forked_journal(), (
            f"NoForkedJournal violated: journal={self.state.journal} "
            f"authority={self.state.authority} partition={self.state.partition}"
        )

    @invariant()
    def local_idempotency(self) -> None:
        assert self.state.check_local_idempotency(), (
            f"LocalIdempotency violated: journal={self.state.journal}"
        )

    @invariant()
    def single_command(self) -> None:
        assert self.state.check_single_command(), (
            f"SingleCommand violated: role={self.state.role} "
            f"partition={self.state.partition}"
        )


TestStrict = StrictMachine.TestCase
TestStrict.settings = settings(max_examples=2000, stateful_step_count=50)


def test_weak_variant_admits_counterexample() -> None:
    """The weak variant must produce a forked-journal violation.

    The trace mirrors the canonical split-brain-on-cursor pattern: v1 is
    isolated from v2, v2 is promoted under weak rules without revoking
    v1's authority, and both then commit at the same seq because each
    reads its own local cursor pointing at Len(journal)+1 = 1.
    """
    state = ProtocolState.init(VEHICLES, "v1", strict_promotion=False)
    assert state.partition_pair("v1", "v2")
    assert state.promote("v2")
    # Both v1 and v2 now hold authority -- SingleAuthority already violated.
    assert not state.check_single_authority()
    assert state.commit_event("v1", "c1")
    assert state.commit_event("v2", "c2")
    # Two events at the same seq: forked journal.
    seqs = [e.seq for e in state.journal]
    assert seqs == [1, 1], f"expected forked seq=1, got {seqs}"
    assert not state.check_no_forked_journal()
