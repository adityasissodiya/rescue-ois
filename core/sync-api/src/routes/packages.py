"""Package routes: serve published packages and manifests."""

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/packages", tags=["packages"])


@router.get("/{path:path}")
async def get_package(path: str) -> dict:
    """Serve a published package file (PMTiles, attachment archive, manifest)."""
    raise HTTPException(status_code=501, detail="Not Implemented")
