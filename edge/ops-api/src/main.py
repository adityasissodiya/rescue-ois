from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI
from pydantic_settings import BaseSettings

from src.db import close_pool, get_pool
from src.routes import api, files, tiles


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@postgres:5432/rescue_ois_edge"
    edge_role: Literal["command", "responder"] = "responder"
    files_dir: str = "/data/files"

    class Config:
        env_file = ".env"


settings = Settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await get_pool(settings.database_url)
    try:
        yield
    finally:
        await close_pool()


app = FastAPI(title="ops-api", lifespan=lifespan)
app.state.settings = settings

app.include_router(api.router)
app.include_router(tiles.router)
app.include_router(files.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "ops-api", "role": settings.edge_role}
