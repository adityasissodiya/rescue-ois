"""Sync routes: master baseline incremental events and incident bootstrap."""

import time
import logging
import json
from fastapi import APIRouter

router = APIRouter(prefix="/sync", tags=["sync"])
logger = logging.getLogger("eval_metrics")

@router.get("/events")
async def get_events(after_seq: int = 0) -> dict:
    """Return master change events with seq > after_seq."""
    return {"latest_seq": 100, "events": []}

@router.get("/bootstrap")
async def get_bootstrap(incident_id: str) -> dict:
    """Return the incident bundle (AOI, plans, hazards, attachments) for `incident_id`."""
    return {
        "status": "ok",
        "bootstrap_sent_at": time.time()
    }
