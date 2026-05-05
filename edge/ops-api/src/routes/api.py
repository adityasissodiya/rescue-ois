"""Tablet-facing API: bootstrap, search, field-edit submission."""

import json
from uuid import uuid4

from fastapi import APIRouter, Request

from src.db import get_pool
from src.models import FieldEdit

router = APIRouter(prefix="/api", tags=["api"])


@router.get("/bootstrap")
async def get_bootstrap() -> dict:
    """Return the initial bundle for a freshly-connected tablet.

    On responder vehicles this is a thin wrapper that the harness drives
    through the responder's syncd if a real bootstrap has been pulled.
    """
    return {
        "master_version": "v1.0",
        "incident_id": None,
        "last_event_seq": 0,
    }


@router.get("/search")
async def search(q: str) -> dict:
    """Local search across cached sites/plans/hazards."""
    return {"results": []}


@router.post("/events")
async def post_event(edit: FieldEdit, request: Request) -> dict:
    """Persist a field edit into outbox.device_outbox. Idempotent on client_event_id."""
    settings = request.app.state.settings
    pool = await get_pool(settings.database_url)
    async with pool.acquire() as conn:
        result = await conn.execute(
            """
            INSERT INTO outbox.device_outbox
                (id, incident_id, client_event_id, device_id, user_id,
                 event_type, payload, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            ON CONFLICT (client_event_id) DO NOTHING
            """,
            uuid4(),
            edit.incident_id,
            edit.client_event_id,
            edit.device_id,
            edit.user_id,
            edit.event_type,
            json.dumps(edit.payload),
            edit.occurred_at,
        )
    inserted = result.endswith(" 1")
    return {
        "status": "accepted" if inserted else "duplicate",
        "client_event_id": str(edit.client_event_id),
    }
