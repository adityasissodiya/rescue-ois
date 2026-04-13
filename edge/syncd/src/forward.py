"""Forward incident journal slices to the regional core (command role).

Sync flow 5: Command → Core. Streams incremental incident.journal rows over
the WG overlay to core sync-api. Tracks the last acked seq locally for resume.
"""


import time
import logging
import json
import asyncio

logger = logging.getLogger("eval_metrics")

async def run() -> None:
    """Continuously forward incident journal slices to core."""
    last_acked_seq = 0
    core_latest_seq = 100 # Mock out-of-sync max seq
    
    while True:
        # Measure local vs global staleness
        logger.info(json.dumps({
            "metric": "data_staleness",
            "local_seq": last_acked_seq,
            "core_seq": core_latest_seq,
            "drift_distance": core_latest_seq - last_acked_seq,
            "ts": time.time()
        }))
        
        # Simulate pushing slice
        last_acked_seq += 5
        if last_acked_seq > core_latest_seq:
            core_latest_seq += 10 # Core advances
            
        await asyncio.sleep(2)
