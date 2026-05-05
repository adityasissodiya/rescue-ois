"""HTTP accept endpoint for command-role syncd.

Receives event batches from responder syncd processes, allocates the next
incident-scoped event_seq inside a single transaction, persists into
incident.journal, and acknowledges with the highest accepted seq.

Idempotency: on collision against the journal_client_event_id unique index,
the event is treated as a duplicate and not re-sequenced.
"""

from __future__ import annotations

import logging
import json
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.config import settings
from src.db import get_pool

router = APIRouter(prefix="/accept", tags=["accept"])
logger = logging.getLogger("syncd.accept")


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


@router.post("/event-batch", response_model=AcceptAck)
async def accept_event_batch(batch: AcceptBatch) -> AcceptAck:
    if settings.edge_role != "command":
        raise HTTPException(status_code=409, detail="not a command-role node")

    if not batch.events:
        return AcceptAck(accepted=0, duplicates=0, last_acked_seq=0)

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
                             device_id, user_id, created_at, client_event_id)
                        VALUES (gen_random_uuid(), $1, $2, $3, $4, $5, $6, $7, $8)
                        """,
                        incident_id,
                        seq,
                        ev.event_type,
                        json.dumps(ev.payload),
                        ev.device_id,
                        ev.user_id,
                        ev.created_at,
                        ev.client_event_id,
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

    return AcceptAck(accepted=accepted, duplicates=duplicates, last_acked_seq=highest_seq)
