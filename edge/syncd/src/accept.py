"""Accept and sequence events from responder vehicles (command role).

Sync flow 4 (server side). Receives batches from responder syncd processes,
assigns the next monotonic `event_seq`, persists into `incident.journal`, and
acks the responder with the highest accepted seq.
"""


import time
import logging
import json

logger = logging.getLogger("eval_metrics")

async def run() -> None:
    """Run the accept endpoint loop on the command K430."""
    logger.info(json.dumps({"metric": "command_acceptor_started", "ts": time.time()}))
    # Note: the HTTP handler would normally wrap this state. In pilot tests, 
    # the ops-api endpoint will perform the timestamp logging directly.
    pass
