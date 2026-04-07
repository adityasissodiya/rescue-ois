"""Audit event routes."""

from fastapi import APIRouter, HTTPException

from src.models import AuditEvent

router = APIRouter(prefix="/audit", tags=["audit"])


@router.post("/events")
async def post_events(events: list[AuditEvent]) -> dict:
    """Persist a batch of audit events forwarded from an edge."""
    raise HTTPException(status_code=501, detail="Not Implemented")


@router.get("/events")
async def get_events(
    service: str | None = None,
    actor: str | None = None,
    device_id: str | None = None,
    limit: int = 100,
) -> dict:
    """Query stored audit events."""
    raise HTTPException(status_code=501, detail="Not Implemented")
