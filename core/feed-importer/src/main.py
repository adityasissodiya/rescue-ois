from fastapi import FastAPI
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/rescue_ois"
    lm_api_key: str = ""
    smhi_api_key: str = ""
    trv_api_key: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
app = FastAPI(title="feed-importer")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "feed-importer"}
