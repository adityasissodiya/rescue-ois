"""Model-level tests for two command-capable edges with journal handoff."""

from __future__ import annotations

from hypothesis import settings, strategies as st
from hypothesis.stateful import RuleBasedStateMachine, invariant, rule

from protocol_simulator import JournalHandoffState


EDGES = ("edge-a", "edge-b")
CIDS = tuple(f"c{i}" for i in range(1, 8))
MAX_JOURNAL = 5


class StrictJournalHandoffMachine(RuleBasedStateMachine):
    def __init__(self) -> None:
        super().__init__()
        self.state = JournalHandoffState.init("edge-a", "edge-b")

    @rule(cid=st.sampled_from(CIDS))
    def command_a_commit(self, cid: str) -> None:
        if len(self.state.journals["edge-a"]) < MAX_JOURNAL:
            self.state.try_commit("edge-a", cid)

    @rule(edge=st.sampled_from(EDGES))
    def forward_known_prefix(self, edge: str) -> None:
        self.state.forward_to_core(edge)

    @rule(edge=st.sampled_from(EDGES))
    def bootstrap_edge_from_core(self, edge: str) -> None:
        self.state.bootstrap_from_core(edge)

    @rule()
    def promote_b_after_handoff(self) -> None:
        self.state.promote_after_handoff("edge-b")

    @rule(cid=st.sampled_from(CIDS))
    def stale_a_attempt_after_promotion(self, cid: str) -> None:
        before = {edge: list(journal) for edge, journal in self.state.journals.items()}
        accepted = self.state.try_commit("edge-a", cid, epoch_header=1)
        if self.state.current_epoch > 1:
            assert not accepted
            assert before == self.state.journals

    @rule(cid=st.sampled_from(CIDS))
    def command_b_commit(self, cid: str) -> None:
        if len(self.state.journals["edge-b"]) < MAX_JOURNAL:
            self.state.try_commit("edge-b", cid)

    @invariant()
    def single_current_authority(self) -> None:
        assert self.state.check_single_current_authority(), self.state.authority

    @invariant()
    def no_forked_journal(self) -> None:
        assert self.state.check_no_forked_journal(), self.state.journals

    @invariant()
    def suffix_extension(self) -> None:
        assert self.state.check_candidate_suffix_extension(), self.state.journals


TestStrictJournalHandoff = StrictJournalHandoffMachine.TestCase
TestStrictJournalHandoff.settings = settings(max_examples=1000, stateful_step_count=40)


def test_handoff_rejects_stale_epoch_and_extends_prefix() -> None:
    state = JournalHandoffState.init("edge-a", "edge-b")
    for i in range(1, 4):
        assert state.try_commit("edge-a", f"a-{i}")
    assert state.forward_to_core("edge-a")
    assert state.bootstrap_from_core("edge-b")
    assert state.promote_after_handoff("edge-b")

    before = {edge: list(journal) for edge, journal in state.journals.items()}
    assert not state.try_commit("edge-a", "stale", epoch_header=1)
    assert state.journals == before

    assert state.try_commit("edge-b", "b-1")
    assert [event.seq for event in state.journals["edge-b"]] == [1, 2, 3, 4]
    assert state.check_no_forked_journal()
    assert state.check_candidate_suffix_extension()


def test_weak_promotion_without_handoff_forks_journal() -> None:
    state = JournalHandoffState.init("edge-a", "edge-b")
    assert state.try_commit("edge-a", "a-1")
    assert state.weak_promote_without_handoff("edge-b")
    assert state.try_commit("edge-b", "b-1")
    assert not state.check_single_current_authority()
    assert not state.check_no_forked_journal()
