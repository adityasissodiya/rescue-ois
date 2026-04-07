from fastapi import FastAPI
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/rescue_ois_edge"
    core_audit_url: str = "https://core.rescue-ois.local/audit/events"
    batch_size: int = 200

    class Config:
        env_file = ".env"


settings = Settings()
app = FastAPI(title="audit-forwarder")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "audit-forwarder"}
