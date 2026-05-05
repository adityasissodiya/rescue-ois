"""Push device_outbox entries to the command vehicle (responder role).

Polls outbox.device_outbox, batches unforwarded entries, posts them to the
command K430 syncd /accept/event-batch endpoint, marks rows forwarded once
acked. Runs as an asyncio task started by main.py only when EDGE_ROLE=responder.
"""

from __future__ import annotations

import asyncio
import logging
import time

import httpx

from src.config import settings
from src.db import get_pool
from src.outbox import fetch_unforwarded, mark_forwarded

logger = logging.getLogger("syncd.push")

POLL_INTERVAL_S = 0.25
BATCH_SIZE = 50


async def _push_once(client: httpx.AsyncClient) -> int:
    pool = await get_pool(settings.database_url)
    async with pool.acquire() as conn:
        rows = await fetch_unforwarded(conn, BATCH_SIZE)
        if not rows:
            return 0

        body = {"events": rows}
        url = f"{settings.command_peer_url}/accept/event-batch"
        t0 = time.perf_counter_ns()
        resp = await client.post(url, json=body, timeout=10.0)
        t1 = time.perf_counter_ns()

        if resp.status_code != 200:
            logger.warning("accept rejected: status=%s body=%s", resp.status_code, resp.text)
            return 0

        ack = resp.json()
        ids = [r["id"] for r in rows]
        await mark_forwarded(conn, ids, int(ack.get("last_acked_seq", 0)))

        logger.info(
            "push_batch ok rows=%d latency_ns=%d last_acked_seq=%s",
            len(rows),
            t1 - t0,
            ack.get("last_acked_seq"),
        )
        return len(rows)


async def run() -> None:
    if settings.edge_role != "responder":
        logger.info("push: not a responder, exiting")
        return
    if not settings.command_peer_url:
        logger.error("push: COMMAND_PEER_URL is empty; cannot push")
        return
    async with httpx.AsyncClient() as client:
        while True:
            try:
                pushed = await _push_once(client)
            except Exception as e:
                logger.exception("push: error during _push_once: %s", e)
                pushed = 0
            await asyncio.sleep(POLL_INTERVAL_S if pushed else POLL_INTERVAL_S * 4)
