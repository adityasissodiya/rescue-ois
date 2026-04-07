"""Sync routes: master baseline incremental events and incident bootstrap."""

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/sync", tags=["sync"])


@router.get("/events")
async def get_events(after_seq: int = 0) -> dict:
    """Return master change events with seq > after_seq."""
    raise HTTPException(status_code=501, detail="Not Implemented")


@router.get("/bootstrap")
async def get_bootstrap(incident_id: str) -> dict:
    """Return the incident bundle (AOI, plans, hazards, attachments) for `incident_id`."""
    raise HTTPException(status_code=501, detail="Not Implemented")
