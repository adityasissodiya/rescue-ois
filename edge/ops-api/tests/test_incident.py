import pytest

from src import incident


@pytest.mark.asyncio
async def test_append_event_not_implemented() -> None:
    with pytest.raises(NotImplementedError):
        await incident.append_event({"event_type": "test"})


@pytest.mark.asyncio
async def test_current_state_not_implemented() -> None:
    with pytest.raises(NotImplementedError):
        await incident.current_state("incident-123")
