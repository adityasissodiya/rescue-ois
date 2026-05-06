"""asyncpg pool plus thin helpers for outbox, journal, and sync_state."""

from __future__ import annotations

import asyncio
import json

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


async def get_kv(conn: asyncpg.Connection, key: str, default: int = 0) -> int:
    row = await conn.fetchrow(
        "SELECT value FROM sync.state WHERE key = $1",
        key,
    )
    if row is None:
        return default
    val = row["value"]
    if isinstance(val, dict):
        return int(val.get("v", default))
    if isinstance(val, str):
        decoded = json.loads(val)
        if isinstance(decoded, dict):
            return int(decoded.get("v", default))
    return int(val)


async def set_kv(conn: asyncpg.Connection, key: str, value: int) -> None:
    await conn.execute(
        """
        INSERT INTO sync.state (key, value, updated_at)
        VALUES ($1, jsonb_build_object('v', $2::bigint), now())
        ON CONFLICT (key) DO UPDATE
            SET value = EXCLUDED.value, updated_at = now()
        """,
        key,
        value,
    )
