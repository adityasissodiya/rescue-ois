from src import push


def test_push_run_callable() -> None:
    coro = push.run()
    assert hasattr(coro, "__await__")
    coro.close()
