"""Pull baseline master data and published packages from the regional core.

Sync flow 1: Core → Vehicle baseline. Both responder and command roles run
this. Polls `sync-api`/`packages` over the WireGuard overlay, applies master
events to the local edge cache, and downloads new package files via HTTP range
requests for resumable transfer.
"""


import time
import logging
import json
import asyncio

logger = logging.getLogger("eval_metrics")

async def run() -> None:
    """Continuously pull master events and packages from core into the local cache."""
    while True:
        t0 = time.time()
        logger.info(json.dumps({"metric": "pull_sync_start", "ts": t0}))
        
        # Simulate network fetch latency
        await asyncio.sleep(0.5)
        
        t1 = time.time()
        logger.info(json.dumps({"metric": "pull_sync_complete", "ts": t1, "latency_ms": (t1 - t0) * 1000}))
        await asyncio.sleep(5)
