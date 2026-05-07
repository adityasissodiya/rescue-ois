"""Property: replaying a cid never adds to the journal beyond the first commit."""

from hypothesis import given, settings, strategies as st

from protocol_simulator import ProtocolState


VEHICLES = ("v1", "v2", "v3")


@given(
    cid=st.sampled_from(["c1", "c2", "c3"]),
    n=st.integers(min_value=1, max_value=20),
)
@settings(max_examples=200)
def test_cid_replayed_exactly_once(cid: str, n: int) -> None:
    state = ProtocolState.init(VEHICLES, "v1", strict_promotion=True)
    for _ in range(n):
        state.commit_event("v1", cid)
    assert state.journal_cids() == {cid}
    assert len(state.journal) == 1
