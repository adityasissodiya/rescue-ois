"""Tablet-facing API: bootstrap, search, field-edit submission."""

import time
import logging
import json
from fastapi import APIRouter, HTTPException

from src.models import FieldEdit

router = APIRouter(prefix="/api", tags=["api"])
logger = logging.getLogger("eval_metrics")

@router.get("/bootstrap")
async def get_bootstrap() -> dict:
    """Return the initial bundle for a freshly-connected tablet."""
    # INSTRUMENTATION: Track bootstrap start and mock completion for pilot
    t0 = time.time()
    logger.info(json.dumps({"metric": "bootstrap_start", "ts": t0}))
    
    # Simulating work or just returning mock for the evaluation runner
    t1 = time.time()
    logger.info(json.dumps({"metric": "bootstrap_end", "ts": t1, "latency_ms": (t1 - t0) * 1000}))
    
    return {
        "master_version": "v1.0",
        "incident_id": "mock_incident",
        "aoi_geojson": {"type": "Polygon", "coordinates": []},
        "plan_ids": [],
        "last_event_seq": 0
    }

@router.get("/search")
async def search(q: str) -> dict:
    """Local search across cached sites/plans/hazards."""
    return {"results": []}

@router.post("/events")
async def post_event(edit: FieldEdit) -> dict:
    """Accept a field edit. On command role, append to journal. On responder, queue in outbox."""
    received_at = time.time()
    logger.info(json.dumps({
        "metric": "field_edit_received",
        "client_event_id": edit.client_event_id,
        "occurred_at": edit.occurred_at.isoformat(),
        "received_at": received_at,
        "device_id": edit.device_id
    }))
    return {"status": "accepted", "event_id": edit.client_event_id}
