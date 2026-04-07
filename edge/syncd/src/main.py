from fastapi import FastAPI

from src.config import settings

app = FastAPI(title="syncd")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "syncd", "role": settings.edge_role}
