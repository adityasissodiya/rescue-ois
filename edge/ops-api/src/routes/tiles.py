"""Tile routes: serve local PMTiles via Martin."""

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/tiles", tags=["tiles"])


@router.get("/{path:path}")
async def get_tile(path: str) -> dict:
    """Proxy to local Martin instance for PMTiles serving."""
    raise HTTPException(status_code=501, detail="Not Implemented")
