"""File routes: serve cached attachment files."""

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/files", tags=["files"])


@router.get("/{path:path}")
async def get_file(path: str) -> dict:
    """Stream a cached attachment file from FILES_DIR."""
    raise HTTPException(status_code=501, detail="Not Implemented")
