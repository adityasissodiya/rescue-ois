from src import accept


def test_accept_router_exists() -> None:
    assert accept.router is not None
    assert any(r.path == "/accept/event-batch" for r in accept.router.routes)
