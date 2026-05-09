"""Forward incident journal slices to the regional core (command role).

Reads journal rows past the locally-tracked last_acked_seq_to_core, posts
batches to core sync-api /sync/journal-batch, advances the cursor on success.
Idempotent end-to-end via client_event_id.
"""

from __future__ import annotations

import json
import asyncio
import logging
import time

import httpx

from src.config import settings
from src.db import get_kv, get_pool, set_kv

logger = logging.getLogger("syncd.forward")

POLL_INTERVAL_S = 1.0
BATCH_SIZE = 200
KV_KEY = "last_acked_seq_to_core"


_TIMEOUT = httpx.Timeout(15.0, connect=5.0, read=15.0, write=5.0, pool=5.0)


async def _forward_once(client: httpx.AsyncClient | None = None) -> int:
    pool = await get_pool(settings.database_url)
    async with pool.acquire() as conn:
        last_acked = await get_kv(conn, KV_KEY, 0)
        rows = await conn.fetch(
            """
            SELECT incident_id, event_seq, event_type, payload,
                   device_id, user_id, created_at, client_event_id
            FROM incident.journal
            WHERE event_seq > $1
            ORDER BY event_seq ASC
            LIMIT $2
            """,
            last_acked,
            BATCH_SIZE,
        )
        if not rows:
            return 0

        events = [
            {
                "incident_id": str(r["incident_id"]),
                "event_seq": int(r["event_seq"]),
                "event_type": r["event_type"],
                "payload": r["payload"] if isinstance(r["payload"], dict) else json.loads(r["payload"]),
                "device_id": r["device_id"],
                "user_id": r["user_id"],
                "client_event_id": str(r["client_event_id"]),
                "created_at": r["created_at"].isoformat(),
            }
            for r in rows
        ]

        url = f"{settings.core_base_url}/sync/journal-batch"
        t0 = time.perf_counter_ns()
        async with httpx.AsyncClient(timeout=_TIMEOUT) as fresh:
            try:
                resp = await asyncio.wait_for(
                    fresh.post(url, json={"events": events}),
                    timeout=17.0,
                )
            except asyncio.TimeoutError as e:
                raise httpx.ReadTimeout("asyncio wait_for fired") from e
        t1 = time.perf_counter_ns()

        if resp.status_code != 200:
            logger.warning("forward: core rejected status=%s body=%s", resp.status_code, resp.text)
            return 0

        new_last_acked = max(int(r["event_seq"]) for r in rows)
        await set_kv(conn, KV_KEY, new_last_acked)
        logger.info(
            "forward ok rows=%d new_last_acked=%d latency_ns=%d",
            len(rows),
            new_last_acked,
            t1 - t0,
        )
        return len(rows)


_ITERATION_DEADLINE_S = 25.0


async def run() -> None:
    if settings.edge_role != "command":
        logger.info("forward: not a command, exiting")
        return
    while True:
        try:
            forwarded = await asyncio.wait_for(
                _forward_once(), timeout=_ITERATION_DEADLINE_S
            )
        except (asyncio.TimeoutError, TimeoutError):
            logger.warning("forward: iteration deadline exceeded, retrying")
            forwarded = 0
        except httpx.RequestError as e:
            logger.warning("forward: transport error: %s", e)
            forwarded = 0
        except Exception as e:
            logger.exception("forward: error: %s", e)
            forwarded = 0
        await asyncio.sleep(POLL_INTERVAL_S if forwarded else POLL_INTERVAL_S * 2)
