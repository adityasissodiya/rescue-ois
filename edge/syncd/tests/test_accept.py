import pytest

from src import accept


@pytest.mark.asyncio
async def test_accept_run_not_implemented() -> None:
    with pytest.raises(NotImplementedError):
        await accept.run()
