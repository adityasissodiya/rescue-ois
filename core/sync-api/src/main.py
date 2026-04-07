from fastapi import FastAPI
from pydantic_settings import BaseSettings

from src.routes import packages, sync, tiles


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/rescue_ois"
    packages_dir: str = "/data/packages"

    class Config:
        env_file = ".env"


settings = Settings()
app = FastAPI(title="sync-api")

app.include_router(sync.router)
app.include_router(tiles.router)
app.include_router(packages.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "sync-api"}
