from fastapi import FastAPI
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/rescue_ois"
    publish_dir: str = "/data/packages"
    signing_key_path: str = "/run/secrets/publisher_signing_key"

    class Config:
        env_file = ".env"


settings = Settings()
app = FastAPI(title="publisher")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "publisher"}
