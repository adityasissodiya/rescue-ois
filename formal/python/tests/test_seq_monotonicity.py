"""Property: under a single authority, event_seq is strictly monotonic with no gaps."""

from hypothesis import given, settings, strategies as st

from protocol_simulator import ProtocolState


VEHICLES = ("v1", "v2", "v3")


@given(cids=st.lists(st.sampled_from(["c1", "c2", "c3", "c4", "c5"]), min_size=0, max_size=5))
@settings(max_examples=500)
def test_event_seq_dense(cids: list[str]) -> None:
    state = ProtocolState.init(VEHICLES, "v1", strict_promotion=True)
    accepted = []
    for cid in cids:
        if state.commit_event("v1", cid):
            accepted.append(cid)
    seqs = [e.seq for e in state.journal]
    assert seqs == list(range(1, len(accepted) + 1))
