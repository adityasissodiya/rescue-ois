"""syncd runtime configuration.

The single most important flag is EDGE_ROLE, which determines whether this
daemon runs in command or responder mode. See architecture/sync-protocol.md.
"""

from typing import Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/rescue_ois_edge"
    edge_role: Literal["command", "responder"] = "responder"
    core_base_url: str = "https://core.rescue-ois.local"
    command_peer_url: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
ROLE: Literal["command", "responder"] = settings.edge_role
