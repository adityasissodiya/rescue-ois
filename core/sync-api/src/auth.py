"""Authentication helpers for sync-api.

Edges authenticate to sync-api by virtue of their position on the WireGuard
overlay plus an mTLS client certificate issued by the organizational CA.
"""

from fastapi import Request


async def require_edge_identity(request: Request) -> str:
    """Resolve and return the calling edge K430's identity from request context."""
    # TODO: extract client cert subject from request, validate against CA,
    # return canonical edge_id.
    raise NotImplementedError
