"""Tablet-facing API: bootstrap, search, field-edit submission."""

from fastapi import APIRouter, HTTPException

from src.models import FieldEdit

router = APIRouter(prefix="/api", tags=["api"])


@router.get("/bootstrap")
async def get_bootstrap() -> dict:
    """Return the initial bundle for a freshly-connected tablet."""
    raise HTTPException(status_code=501, detail="Not Implemented")


@router.get("/search")
async def search(q: str) -> dict:
    """Local search across cached sites/plans/hazards."""
    raise HTTPException(status_code=501, detail="Not Implemented")


@router.post("/events")
async def post_event(edit: FieldEdit) -> dict:
    """Accept a field edit. On command role, append to journal. On responder, queue in outbox."""
    raise HTTPException(status_code=501, detail="Not Implemented")
