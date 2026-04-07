"""Push device_outbox entries to the command vehicle (responder role).

Sync flow 4: Responder → Command vehicle. Reads unforwarded entries from
`outbox.device_outbox`, batches them, posts to the command K430's syncd accept
endpoint, and marks rows forwarded once acked.
"""


async def run() -> None:
    """Continuously push outbox entries to the command vehicle."""
    # TODO: SELECT FROM outbox.device_outbox WHERE forwarded_at IS NULL ORDER BY id
    # POST to {command_peer_url}/syncd/accept with idempotency keys
    # On 200, UPDATE forwarded_at and ack_seq
    raise NotImplementedError
