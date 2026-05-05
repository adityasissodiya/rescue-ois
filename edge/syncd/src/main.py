"""syncd FastAPI app + background tasks.

Wires the accept HTTP router (used only when EDGE_ROLE=command) and starts
push (responder) or forward (command) as background asyncio tasks based on
role.
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src import accept, forward, push
from src.config import settings
from src.db import close_pool, get_pool

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("syncd")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await get_pool(settings.database_url)
    bg: asyncio.Task | None = None
    if settings.edge_role == "responder":
        bg = asyncio.create_task(push.run(), name="push")
    elif settings.edge_role == "command":
        bg = asyncio.create_task(forward.run(), name="forward")
    try:
        yield
    finally:
        if bg is not None:
            bg.cancel()
            try:
                await bg
            except asyncio.CancelledError:
                pass
        await close_pool()


app = FastAPI(title="syncd", lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "syncd", "role": settings.edge_role}


app.include_router(accept.router)
