"""Outbox table helpers used by both push (responder) and accept (command).

Encapsulates inserts/queries against `outbox.device_outbox` so the rest of
syncd does not embed SQL strings.
"""


async def enqueue(event: dict) -> str:
    """Insert an event into outbox.device_outbox; return the row id."""
    # TODO: INSERT into outbox.device_outbox, return id.
    raise NotImplementedError


async def fetch_unforwarded(limit: int = 100) -> list[dict]:
    """Return up to `limit` rows where forwarded_at IS NULL ordered by id."""
    # TODO: SELECT FROM outbox.device_outbox WHERE forwarded_at IS NULL.
    raise NotImplementedError


async def mark_forwarded(row_ids: list[str], ack_seq: int) -> None:
    """Mark the given outbox rows as forwarded with the supplied ack_seq."""
    # TODO: UPDATE outbox.device_outbox SET forwarded_at = now(), ack_seq = $2
    raise NotImplementedError
