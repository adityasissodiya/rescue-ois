import pytest

from src import push


@pytest.mark.asyncio
async def test_push_run_not_implemented() -> None:
    with pytest.raises(NotImplementedError):
        await push.run()
