from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic_settings import BaseSettings

from src.db import close_pool, get_pool
from src.routes import packages, sync, tiles


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@postgres:5432/rescue_ois"
    packages_dir: str = "/data/packages"

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


app = FastAPI(title="sync-api", lifespan=lifespan)
app.state.settings = settings

app.include_router(sync.router)
app.include_router(tiles.router)
app.include_router(packages.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "sync-api"}
