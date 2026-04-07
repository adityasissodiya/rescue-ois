import pytest

from src import pull


@pytest.mark.asyncio
async def test_pull_run_not_implemented() -> None:
    with pytest.raises(NotImplementedError):
        await pull.run()
