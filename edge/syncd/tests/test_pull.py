from src import pull


def test_pull_run_callable() -> None:
    coro = pull.run()
    assert hasattr(coro, "__await__")
    coro.close()
