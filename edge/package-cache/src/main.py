from fastapi import FastAPI
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    cache_dir: str = "/data/cache"

    class Config:
        env_file = ".env"


settings = Settings()
app = FastAPI(title="package-cache")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "package-cache"}
