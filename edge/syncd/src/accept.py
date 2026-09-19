"""HTTP accept endpoint for command-role syncd.

Receives event batches from responder syncd processes, allocates the next
incident-scoped event_seq inside a single transaction, persists into
incident.journal, and acknowledges with the highest accepted seq.

Idempotency: on collision against the journal_client_event_id unique index,
the event is treated as a duplicate and not re-sequenced.

Command-epoch fencing: every request must carry X-Command-Epoch matching the
current command epoch. Stale (less) and future (greater) values are rejected
with HTTP 409 before any journal work. Each accepted event is stamped with the
epoch it was committed under.

Where the epoch comes from (T-08)
---------------------------------
Epochs are now issued by the regional core, per incident
(``master.command_epoch``, core migration 006). Core issuance is what makes
promotion serializable across two independent edges: each edge has its own
Postgres, so a purely edge-local counter can never tell two edges apart.

Resolution order for an incident's epoch is deliberately narrow:

1. in-process cache;
2. core ``GET /sync/command-epoch`` -- authoritative when it returns one;
3. the edge-local ``incident.current_epoch`` view -- used when core returns
   404 (no epoch ever issued for this incident) or is unreachable.

Step 3 is not merely a convenience. Falling back on 404 keeps the existing
single-edge fencing experiment (``scripts/evaluate-fenced-promotion.py``)
measuring exactly what it measured before: that harness mutates the local
command_epoch table and restarts syncd, never promoting at core, so core has
no epoch for its incident and the local table remains in control. Making core
unconditionally authoritative would have silently turned that harness into a
no-op and invalidated the paper's measured fenced-promotion result.

Falling back when core is *unreachable* is the availability half of the same
trade-off: a command edge that has lost its backhaul must keep accepting
authority-bearing writes, since backhaul loss is not authority loss. The
bound on how long it may do so is the command-authority lease
(``settings.lease_window_s``), enforced in ``forward.py``.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from uuid import UUID

import httpx
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from src.config import settings
from src.db import get_kv, get_pool

router = APIRouter(prefix="/accept", tags=["accept"])
logger = logging.getLogger("syncd.accept")


# Per-incident command-epoch cache. Populated lazily from core (or the local
# fallback) on first use for an incident, and invalidated by
# refresh_epoch_cache() after a rejection.
_epoch_cache: dict[UUID, int] = {}

# Epoch read from the edge-local incident.current_epoch view at startup. Used
# only when core has no epoch for an incident or cannot be reached.
_local_fallback_epoch: int | None = None

_CORE_TIMEOUT = httpx.Timeout(5.0, connect=2.0, read=5.0, write=2.0, pool=2.0)


async def _read_local_epoch() -> int | None:
    """Read the edge-local current epoch, or None if the table is empty."""
    pool = await get_pool(settings.database_url)
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT epoch_id FROM incident.current_epoch")
    if row is None or row["epoch_id"] is None:
        return None
    return int(row["epoch_id"])


async def init_epoch_cache() -> None:
    """Prime the local fallback epoch. Called by the FastAPI lifespan.

    Deliberately does not contact core: at startup no incident is in play yet,
    and a command edge must be able to start while partitioned from core.
    """
    global _local_fallback_epoch
    if settings.edge_role != "command":
        return
    _local_fallback_epoch = await _read_local_epoch()
    _epoch_cache.clear()
    logger.info(
        "epoch_cache: initialised local_fallback=%s lease_window_s=%s",
        _local_fallback_epoch,
        settings.lease_window_s,
    )


async def fetch_core_epoch(incident_id: UUID) -> int | None:
    """Ask core for the current epoch of one incident.

    Returns None when core has issued no epoch for this incident (404) or is
    unreachable; the caller then falls back to the local view.
    """
    url = f"{settings.core_base_url}/sync/command-epoch"
    try:
        async with httpx.AsyncClient(timeout=_CORE_TIMEOUT) as client:
            response = await client.get(url, params={"incident_id": str(incident_id)})
    except httpx.RequestError as exc:
        logger.warning("epoch: core unreachable (%s); using local fallback", exc)
        return None

    if response.status_code == 404:
        return None
    if response.status_code != 200:
        logger.warning(
            "epoch: core returned status=%s body=%s; using local fallback",
            response.status_code,
            response.text[:200],
        )
        return None
    return int(response.json()["epoch_id"])


async def get_epoch_for_incident(incident_id: UUID) -> int | None:
    """Resolve the epoch for one incident: cache, then core, then local."""
    cached = _epoch_cache.get(incident_id)
    if cached is not None:
        return cached

    epoch = await fetch_core_epoch(incident_id)
    if epoch is not None:
        _epoch_cache[incident_id] = epoch
        logger.info("epoch: incident=%s epoch=%d source=core", incident_id, epoch)
        return epoch

    # Fallback values are deliberately NOT cached. Caching one would open a
    # stale-authority window: if this incident is promoted at core later, a
    # cached local value would keep this edge fencing against a superseded
    # epoch until something forced a refresh -- exactly the failure the
    # core-issued epoch exists to prevent. Re-reading costs one indexed row
    # from the local database, and the next call picks up a core promotion as
    # soon as one exists.
    local = _local_fallback_epoch
    if local is None:
        local = await _read_local_epoch()
    if local is not None:
        logger.info(
            "epoch: incident=%s epoch=%d source=local-fallback (not cached)",
            incident_id,
            local,
        )
    return local


async def refresh_epoch_cache(incident_id: UUID | None = None) -> int | None:
    """Invalidate and re-resolve. Call after a promotion or a rejection.

    With no argument the whole cache is dropped and the local fallback re-read,
    which is what a role flip needs.
    """
    global _local_fallback_epoch
    if incident_id is None:
        _epoch_cache.clear()
        _local_fallback_epoch = await _read_local_epoch()
        return _local_fallback_epoch
    _epoch_cache.pop(incident_id, None)
    return await get_epoch_for_incident(incident_id)


def get_current_epoch(incident_id: UUID | None = None) -> int | None:
    """Test/observability hook. Reads cache only; never performs I/O."""
    if incident_id is None:
        return _local_fallback_epoch
    return _epoch_cache.get(incident_id)


def _set_current_epoch_for_tests(value: int | None, incident_id: UUID | None = None) -> None:
    """Test-only setter. Production code uses init/refresh_epoch_cache."""
    global _local_fallback_epoch
    if incident_id is None:
        _local_fallback_epoch = value
        _epoch_cache.clear()
        return
    if value is None:
        _epoch_cache.pop(incident_id, None)
    else:
        _epoch_cache[incident_id] = value


def validate_request_epoch(client_epoch: int | None, current_epoch: int | None) -> None:
    """Compare the request's claimed command_epoch against the current one.

    Raises HTTPException(409) on mismatch. A missing header (None) is treated
    as a stale request: the responder must send the header.

    Pure by design so it can be unit-tested without a database or core; see
    tests/test_accept_epoch.py.
    """
    if current_epoch is None:
        raise HTTPException(
            status_code=503,
            detail="command epoch not initialised",
        )
    if client_epoch is None:
        raise HTTPException(
            status_code=409,
            detail={"reason": "missing_epoch", "current_epoch": current_epoch},
        )
    if client_epoch < current_epoch:
        raise HTTPException(
            status_code=409,
            detail={"reason": "stale_epoch", "current_epoch": current_epoch, "request_epoch": client_epoch},
        )
    if client_epoch > current_epoch:
        raise HTTPException(
            status_code=409,
            detail={"reason": "future_epoch", "current_epoch": current_epoch, "request_epoch": client_epoch},
        )


class IncomingEvent(BaseModel):
    id: str
    incident_id: UUID
    client_event_id: UUID
    device_id: str
    user_id: str
    event_type: str
    payload: dict
    created_at: datetime


class AcceptBatch(BaseModel):
    events: list[IncomingEvent]


class AcceptAck(BaseModel):
    accepted: int
    duplicates: int
    last_acked_seq: int
    current_epoch: int


@router.post("/event-batch", response_model=AcceptAck)
async def accept_event_batch(
    batch: AcceptBatch,
    x_command_epoch: str | None = Header(default=None, alias="X-Command-Epoch"),
) -> AcceptAck:
    if settings.edge_role != "command":
        raise HTTPException(status_code=409, detail="not a command-role node")

    client_epoch: int | None
    if x_command_epoch is None:
        client_epoch = None
    else:
        try:
            client_epoch = int(x_command_epoch)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"X-Command-Epoch is not an integer: {x_command_epoch!r}",
            ) from None

    if not batch.events:
        # No incident in play, so there is no epoch to validate against.
        return AcceptAck(accepted=0, duplicates=0, last_acked_seq=0, current_epoch=0)

    # Command-authority lease gate (T-09). An isolated former command cannot be
    # told its epoch is stale, so it fences itself on a timeout it cannot
    # renew. Checked before epoch resolution because a lapsed lease means this
    # node has no authority at all, which is a different condition from holding
    # the wrong epoch -- hence 503 rather than 409.
    #
    # Fails open when no lease was ever established; see forward.py.
    from src import forward  # local import: avoids a module-level cycle

    pool_for_lease = await get_pool(settings.database_url)
    async with pool_for_lease.acquire() as lease_conn:
        if await get_kv(lease_conn, forward.KV_DEMOTED, 0) == 1:
            raise HTTPException(
                status_code=503,
                detail={
                    "reason": "command_authority_revoked",
                    "detail": "this edge was superseded and has demoted itself",
                },
            )
        if not await forward.lease_is_valid(lease_conn):
            raise HTTPException(
                status_code=503,
                detail={
                    "reason": "command_authority_lease_expired",
                    "lease_window_s": settings.lease_window_s,
                    "detail": "could not renew authority against core within the lease window",
                },
            )

    by_incident: dict[UUID, list[IncomingEvent]] = {}
    for ev in batch.events:
        by_incident.setdefault(ev.incident_id, []).append(ev)

    # Resolve and validate every incident's epoch before opening a transaction:
    # epoch resolution may call core over HTTP, which must not happen while
    # holding a row lock. Validation precedes all journal work, so a rejected
    # batch writes nothing.
    epochs: dict[UUID, int] = {}
    for incident_id in by_incident:
        current_epoch = await get_epoch_for_incident(incident_id)
        validate_request_epoch(client_epoch, current_epoch)
        assert current_epoch is not None  # validate raises 503 when None
        epochs[incident_id] = current_epoch

    pool = await get_pool(settings.database_url)
    accepted = 0
    duplicates = 0
    highest_seq = 0

    async with pool.acquire() as conn, conn.transaction():
        for incident_id, events in by_incident.items():
            incident_epoch = epochs[incident_id]
            await conn.execute(
                """
                    INSERT INTO incident.state (incident_id, last_event_seq, state)
                    VALUES ($1, 0, '{}'::jsonb)
                    ON CONFLICT (incident_id) DO NOTHING
                    """,
                incident_id,
            )
            row = await conn.fetchrow(
                """
                    SELECT last_event_seq FROM incident.state
                    WHERE incident_id = $1
                    FOR UPDATE
                    """,
                incident_id,
            )
            seq = int(row["last_event_seq"])

            for ev in events:
                existing = await conn.fetchrow(
                    "SELECT event_seq FROM incident.journal WHERE client_event_id = $1",
                    ev.client_event_id,
                )
                if existing is not None:
                    duplicates += 1
                    highest_seq = max(highest_seq, int(existing["event_seq"]))
                    continue

                seq += 1
                await conn.execute(
                    """
                        INSERT INTO incident.journal
                            (id, incident_id, event_seq, event_type, payload,
                             device_id, user_id, created_at, client_event_id,
                             command_epoch)
                        VALUES (gen_random_uuid(), $1, $2, $3, $4, $5, $6, $7, $8, $9)
                        """,
                    incident_id,
                    seq,
                    ev.event_type,
                    json.dumps(ev.payload),
                    ev.device_id,
                    ev.user_id,
                    ev.created_at,
                    ev.client_event_id,
                    incident_epoch,
                )
                accepted += 1
                highest_seq = max(highest_seq, seq)

            await conn.execute(
                """
                    UPDATE incident.state
                    SET last_event_seq = $2, updated_at = now()
                    WHERE incident_id = $1
                    """,
                incident_id,
                seq,
            )

    # Every incident in the batch validated against the same client epoch, so
    # any of them reports the same value; batches are single-incident in the
    # evaluated workload.
    return AcceptAck(
        accepted=accepted,
        duplicates=duplicates,
        last_acked_seq=highest_seq,
        current_epoch=next(iter(epochs.values())),
    )
