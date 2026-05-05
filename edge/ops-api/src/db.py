"""asyncpg connection pool helpers for ops-api."""

from __future__ import annotations

import asyncio

import asyncpg

_pool: asyncpg.Pool | None = None


async def get_pool(dsn: str) -> asyncpg.Pool:
    global _pool
    if _pool is None:
        plain_dsn = dsn.replace("postgresql+asyncpg://", "postgresql://")
        for attempt in range(30):
            try:
                _pool = await asyncpg.create_pool(plain_dsn, min_size=1, max_size=8)
                break
            except (OSError, asyncpg.PostgresError):
                if attempt == 29:
                    raise
                await asyncio.sleep(1)
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
