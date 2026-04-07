from typing import Literal

from fastapi import FastAPI
from pydantic_settings import BaseSettings

from src.routes import api, files, tiles


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/rescue_ois_edge"
    edge_role: Literal["command", "responder"] = "responder"
    files_dir: str = "/data/files"

    class Config:
        env_file = ".env"


settings = Settings()
app = FastAPI(title="ops-api")

app.include_router(api.router)
app.include_router(tiles.router)
app.include_router(files.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "ops-api"}
