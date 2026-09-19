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

    # Identity of this vehicle edge, e.g. "edge-cmd" or "edge-resp-1". Must
    # match the node_id recorded against the command epoch at promotion time
    # (scripts/promote-responder.sh passes the compose project name), because
    # core checks that a forwarded batch comes from the node that actually
    # holds the epoch -- not merely from something quoting the right number.
    node_id: str = ""

    # Command-authority lease (ADR-0004; fenced-promotion design decision).
    #
    # A command edge's write authority is not merely "I was promoted once" but
    # "I have renewed against the core witness recently enough". An isolated
    # former command cannot be told that its epoch is stale -- there is no
    # channel by which to tell it -- so instead it fences *itself* on a timeout
    # it cannot renew. This trades local write availability for the isolated
    # old command in exchange for bounding the window in which two edges can
    # both believe they hold authority.
    #
    # The default matches the heartbeat timeout already documented in
    # docs/runbooks/command-failover.md. It must comfortably exceed the
    # forward-loop poll interval, so a brief core outage does not demote a
    # healthy command edge: losing the backhaul is a different failure from
    # losing authority.
    lease_window_s: float = 90.0

    class Config:
        env_file = ".env"


settings = Settings()
ROLE: Literal["command", "responder"] = settings.edge_role
