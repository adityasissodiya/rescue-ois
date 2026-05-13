"""Push device_outbox entries to the command vehicle (responder role).

Polls outbox.device_outbox, batches unforwarded entries, posts them to the
command K430 syncd /accept/event-batch endpoint, marks rows forwarded once
acked. Runs as an asyncio task started by main.py only when EDGE_ROLE=responder.

Command-epoch tracking (migration 005_command_epoch.sql): every push carries
X-Command-Epoch with the responder's last-known command epoch. The first
push starts from 1 (the seed epoch from the migration). The command syncd
returns current_epoch in the ack body; on 409 stale/future, the local cache
is updated and the next iteration retries with the new value.
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

# Responder-side cache of the last command-epoch we have seen acknowledged
# by the current command vehicle. Starts at 1, the seed epoch installed by
# migration 005_command_epoch.sql; updated from ack bodies and 409 responses.
_known_command_epoch: int = 1


def _get_known_epoch() -> int:
    return _known_command_epoch


def _set_known_epoch(value: int) -> None:
    global _known_command_epoch
    _known_command_epoch = value


_TIMEOUT = httpx.Timeout(10.0, connect=5.0, read=10.0, write=5.0, pool=5.0)


async def _push_once(client: httpx.AsyncClient | None = None) -> int:
    pool = await get_pool(settings.database_url)
    async with pool.acquire() as conn:
        rows = await fetch_unforwarded(conn, BATCH_SIZE)
        if not rows:
            return 0

        body = {"events": rows}
        url = f"{settings.command_peer_url}/accept/event-batch"
        headers = {"X-Command-Epoch": str(_known_command_epoch)}
        t0 = time.perf_counter_ns()
        async with httpx.AsyncClient(timeout=_TIMEOUT) as fresh:
            try:
                resp = await asyncio.wait_for(
                    fresh.post(url, json=body, headers=headers),
                    timeout=12.0,
                )
            except asyncio.TimeoutError as e:
                raise httpx.ReadTimeout("asyncio wait_for fired") from e
        t1 = time.perf_counter_ns()

        if resp.status_code == 409:
            # Command's cached epoch differs. Body carries {"detail": {"current_epoch": N, ...}}.
            try:
                payload = resp.json()
                detail = payload.get("detail") if isinstance(payload, dict) else None
                new_epoch = int(detail["current_epoch"]) if isinstance(detail, dict) else None
            except (ValueError, KeyError, TypeError):
                new_epoch = None
            if new_epoch is not None and new_epoch != _known_command_epoch:
                logger.warning(
                    "accept 409 epoch mismatch: was=%d now=%d; updating cache and retrying next iteration",
                    _known_command_epoch,
                    new_epoch,
                )
                _set_known_epoch(new_epoch)
            else:
                logger.warning("accept rejected 409: %s", resp.text)
            return 0

        if resp.status_code != 200:
            logger.warning("accept rejected: status=%s body=%s", resp.status_code, resp.text)
            return 0

        ack = resp.json()
        ids = [r["id"] for r in rows]
        await mark_forwarded(conn, ids, int(ack.get("last_acked_seq", 0)))

        ack_epoch = ack.get("current_epoch")
        if isinstance(ack_epoch, int) and ack_epoch != _known_command_epoch:
            _set_known_epoch(ack_epoch)

        logger.info(
            "push_batch ok rows=%d latency_ns=%d last_acked_seq=%s epoch=%s",
            len(rows),
            t1 - t0,
            ack.get("last_acked_seq"),
            ack.get("current_epoch"),
        )
        return len(rows)


_ITERATION_DEADLINE_S = 18.0


async def run() -> None:
    if settings.edge_role != "responder":
        logger.info("push: not a responder, exiting")
        return
    if not settings.command_peer_url:
        logger.error("push: COMMAND_PEER_URL is empty; cannot push")
        return
    while True:
        try:
            pushed = await asyncio.wait_for(
                _push_once(), timeout=_ITERATION_DEADLINE_S
            )
        except (asyncio.TimeoutError, TimeoutError):
            logger.warning("push: iteration deadline exceeded, retrying")
            pushed = 0
        except httpx.RequestError as e:
            logger.warning("push: transport error: %s", e)
            pushed = 0
        except Exception as e:
            logger.exception("push: error during _push_once: %s", e)
            pushed = 0
        await asyncio.sleep(POLL_INTERVAL_S if pushed else POLL_INTERVAL_S * 4)
