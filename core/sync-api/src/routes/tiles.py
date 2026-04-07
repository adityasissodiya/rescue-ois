"""Tile routes: proxy to Martin for /tiles/{path}."""

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/tiles", tags=["tiles"])


@router.get("/{path:path}")
async def get_tile(path: str) -> dict:
    """Proxy a vector tile request to Martin."""
    raise HTTPException(status_code=501, detail="Not Implemented")
