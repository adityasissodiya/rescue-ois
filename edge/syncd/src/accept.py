"""Accept and sequence events from responder vehicles (command role).

Sync flow 4 (server side). Receives batches from responder syncd processes,
assigns the next monotonic `event_seq`, persists into `incident.journal`, and
acks the responder with the highest accepted seq.
"""


async def run() -> None:
    """Run the accept endpoint loop on the command K430."""
    # TODO: HTTPS endpoint /syncd/accept; on POST, take advisory lock,
    # assign next event_seq, INSERT into incident.journal, COMMIT, ack.
    raise NotImplementedError
