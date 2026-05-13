"""HTTP accept endpoint for command-role syncd.

Receives event batches from responder syncd processes, allocates the next
incident-scoped event_seq inside a single transaction, persists into
incident.journal, and acknowledges with the highest accepted seq.

Idempotency: on collision against the journal_client_event_id unique index,
the event is treated as a duplicate and not re-sequenced.

Command-epoch fencing (migration 005_command_epoch.sql): every request must
carry X-Command-Epoch matching the running command's cached epoch_id. Stale
(less) and future (greater) values are rejected with HTTP 409. Each accepted
event is stamped with the current command_epoch in incident.journal.
"""

from __future__ import annotations

import logging
import json
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from src.config import settings
from src.db import get_pool

router = APIRouter(prefix="/accept", tags=["accept"])
logger = logging.getLogger("syncd.accept")


# Cached command epoch. Loaded by init_epoch_cache() from the
# incident.current_epoch view at startup; re-read after a promotion event
# via refresh_epoch_cache().
_current_epoch: int | None = None


async def init_epoch_cache() -> None:
    """Populate the in-process command-epoch cache from the database.

    Called by the FastAPI lifespan on startup for command-role nodes.
    """
    global _current_epoch
    if settings.edge_role != "command":
        return
    pool = await get_pool(settings.database_url)
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT epoch_id FROM incident.current_epoch")
    epoch = int(row["epoch_id"]) if row and row["epoch_id"] is not None else 0
    _current_epoch = epoch
    logger.info("epoch_cache: initialised current_epoch=%d", epoch)


async def refresh_epoch_cache() -> int:
    """Re-read incident.current_epoch and update the cache. Returns new value."""
    global _current_epoch
    pool = await get_pool(settings.database_url)
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT epoch_id FROM incident.current_epoch")
    epoch = int(row["epoch_id"]) if row and row["epoch_id"] is not None else 0
    _current_epoch = epoch
    return epoch


def get_current_epoch() -> int | None:
    """Test/observability hook."""
    return _current_epoch


def _set_current_epoch_for_tests(value: int | None) -> None:
    """Test-only setter. Production code uses init/refresh_epoch_cache."""
    global _current_epoch
    _current_epoch = value


def validate_request_epoch(client_epoch: int | None, current_epoch: int | None) -> None:
    """Compare the request's claimed command_epoch against the cached current.

    Raises HTTPException(409) on mismatch. A missing header (None) is treated
    as a stale request: the responder must send the header.
    """
    if current_epoch is None:
        raise HTTPException(
            status_code=503,
            detail="command epoch not initialised",
        )
    if client_epoch is None:
        raise HTTPException(
            status_code=409,
            detail={"reason": "missing_epoch", "current_epoch": current_epoch},
        )
    if client_epoch < current_epoch:
        raise HTTPException(
            status_code=409,
            detail={"reason": "stale_epoch", "current_epoch": current_epoch, "request_epoch": client_epoch},
        )
    if client_epoch > current_epoch:
        raise HTTPException(
            status_code=409,
            detail={"reason": "future_epoch", "current_epoch": current_epoch, "request_epoch": client_epoch},
        )


class IncomingEvent(BaseModel):
    id: str
    incident_id: UUID
    client_event_id: UUID
    device_id: str
    user_id: str
    event_type: str
    payload: dict
    created_at: datetime


class AcceptBatch(BaseModel):
    events: list[IncomingEvent]


class AcceptAck(BaseModel):
    accepted: int
    duplicates: int
    last_acked_seq: int
    current_epoch: int


@router.post("/event-batch", response_model=AcceptAck)
async def accept_event_batch(
    batch: AcceptBatch,
    x_command_epoch: Optional[str] = Header(default=None, alias="X-Command-Epoch"),
) -> AcceptAck:
    if settings.edge_role != "command":
        raise HTTPException(status_code=409, detail="not a command-role node")

    client_epoch: int | None
    if x_command_epoch is None:
        client_epoch = None
    else:
        try:
            client_epoch = int(x_command_epoch)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"X-Command-Epoch is not an integer: {x_command_epoch!r}",
            ) from None

    current_epoch = _current_epoch
    validate_request_epoch(client_epoch, current_epoch)
    # validate_request_epoch raises 503 if current_epoch is None; safe to use.
    assert current_epoch is not None

    if not batch.events:
        return AcceptAck(accepted=0, duplicates=0, last_acked_seq=0, current_epoch=current_epoch)

    pool = await get_pool(settings.database_url)
    accepted = 0
    duplicates = 0
    highest_seq = 0

    async with pool.acquire() as conn:
        async with conn.transaction():
            by_incident: dict[UUID, list[IncomingEvent]] = {}
            for ev in batch.events:
                by_incident.setdefault(ev.incident_id, []).append(ev)

            for incident_id, events in by_incident.items():
                await conn.execute(
                    """
                    INSERT INTO incident.state (incident_id, last_event_seq, state)
                    VALUES ($1, 0, '{}'::jsonb)
                    ON CONFLICT (incident_id) DO NOTHING
                    """,
                    incident_id,
                )
                row = await conn.fetchrow(
                    """
                    SELECT last_event_seq FROM incident.state
                    WHERE incident_id = $1
                    FOR UPDATE
                    """,
                    incident_id,
                )
                seq = int(row["last_event_seq"])

                for ev in events:
                    existing = await conn.fetchrow(
                        "SELECT event_seq FROM incident.journal WHERE client_event_id = $1",
                        ev.client_event_id,
                    )
                    if existing is not None:
                        duplicates += 1
                        if int(existing["event_seq"]) > highest_seq:
                            highest_seq = int(existing["event_seq"])
                        continue

                    seq += 1
                    await conn.execute(
                        """
                        INSERT INTO incident.journal
                            (id, incident_id, event_seq, event_type, payload,
                             device_id, user_id, created_at, client_event_id,
                             command_epoch)
                        VALUES (gen_random_uuid(), $1, $2, $3, $4, $5, $6, $7, $8, $9)
                        """,
                        incident_id,
                        seq,
                        ev.event_type,
                        json.dumps(ev.payload),
                        ev.device_id,
                        ev.user_id,
                        ev.created_at,
                        ev.client_event_id,
                        current_epoch,
                    )
                    accepted += 1
                    if seq > highest_seq:
                        highest_seq = seq

                await conn.execute(
                    """
                    UPDATE incident.state
                    SET last_event_seq = $2, updated_at = now()
                    WHERE incident_id = $1
                    """,
                    incident_id,
                    seq,
                )

    return AcceptAck(
        accepted=accepted,
        duplicates=duplicates,
        last_acked_seq=highest_seq,
        current_epoch=current_epoch,
    )
