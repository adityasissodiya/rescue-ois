"""Outbox helpers used by the responder push flow."""

from __future__ import annotations

import json
from uuid import UUID

import asyncpg


async def fetch_unforwarded(conn: asyncpg.Connection, limit: int = 100) -> list[dict]:
    rows = await conn.fetch(
        """
        SELECT id, incident_id, client_event_id, device_id, user_id,
               event_type, payload, created_at
        FROM outbox.device_outbox
        WHERE forwarded_at IS NULL
        ORDER BY created_at, id
        LIMIT $1
        """,
        limit,
    )
    return [
        {
            "id": str(r["id"]),
            "incident_id": str(r["incident_id"]),
            "client_event_id": str(r["client_event_id"]),
            "device_id": r["device_id"],
            "user_id": r["user_id"],
            "event_type": r["event_type"],
            "payload": r["payload"] if isinstance(r["payload"], dict) else json.loads(r["payload"]),
            "created_at": r["created_at"].isoformat(),
        }
        for r in rows
    ]


async def mark_forwarded(conn: asyncpg.Connection, ids: list[str], ack_seq: int) -> None:
    if not ids:
        return
    await conn.execute(
        """
        UPDATE outbox.device_outbox
        SET forwarded_at = now(), ack_seq = $2
        WHERE id = ANY($1::uuid[])
        """,
        [UUID(x) for x in ids],
        ack_seq,
    )
