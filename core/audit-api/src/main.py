from fastapi import FastAPI
from pydantic_settings import BaseSettings

from src.routes import router as audit_router


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/rescue_ois"

    class Config:
        env_file = ".env"


settings = Settings()
app = FastAPI(title="audit-api")
app.include_router(audit_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "audit-api"}
