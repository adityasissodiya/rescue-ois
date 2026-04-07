"""Authentication helpers for ops-api.

Tablets authenticate via mTLS client certificates issued by the organizational
CA. The K430 server cert is pinned in the tablet trust store.
"""

from fastapi import Request


async def require_tablet_identity(request: Request) -> str:
    """Resolve the calling tablet's identity from the mTLS client cert."""
    # TODO: extract subject CN, validate against CA, return tablet_id.
    raise NotImplementedError
