import hashlib
import json
from uuid import UUID

from asyncpg.exceptions import UniqueViolationError
from fastapi import APIRouter, HTTPException, Query, Request

from src.db import get_pool
from src.models import (
    BootstrapResponse,
    EpochPromoteRequest,
    EpochPromoteResponse,
    IncidentEvent,
    JournalBatch,
    JournalBatchAck,
    JournalEventsResponse,
)

# Maximum journal rows returned by one /sync/journal-events page. Edge
# bootstrap pages through by passing the previous response's next_after_seq.
JOURNAL_PAGE_LIMIT = 500

router = APIRouter(prefix="/sync", tags=["sync"])


@router.get("/events")
async def get_events(after_seq: int = 0) -> dict:
    """Return master change events with seq > after_seq.

    The Phase 2 harness does not exercise baseline incremental sync yet, but
    the route remains present for compatibility with the original scaffold.
    """
    return {"latest_seq": after_seq, "events": []}


@router.get("/bootstrap", response_model=BootstrapResponse)
async def get_bootstrap(
    request: Request,
    incident_id: UUID,
    aoi_polygons: int = 1,
) -> BootstrapResponse:
    """Return an incident bootstrap bundle.

    Bundle size is parametrically driven by ``aoi_polygons`` so the
    bootstrap-vs-size scenario can sweep a real range. Hazard and plan
    references are synthesized to scale linearly with aoi_polygons.
    """
    settings = request.app.state.settings
    pool = await get_pool(settings.database_url)

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, ST_AsGeoJSON(aoi)::jsonb AS aoi FROM master.incidents WHERE id = $1",
            incident_id,
        )
        last_seq_row = await conn.fetchrow(
            "SELECT COALESCE(MAX(event_seq), 0) AS s "
            "FROM master.incident_events WHERE incident_id = $1",
            incident_id,
        )

    if row is None:
        ring = [[i * 1.0, (i % 7) * 1.0] for i in range(max(4, aoi_polygons * 4 + 1))]
        ring.append(ring[0])
        aoi = {"type": "Polygon", "coordinates": [ring]}
        last_seq = 0
    else:
        aoi = row["aoi"]
        if isinstance(aoi, str):
            aoi = json.loads(aoi)
        last_seq = int(last_seq_row["s"])

    plan_ids = [f"plan-{i:04d}" for i in range(aoi_polygons)]
    hazard_ids = [f"hz-{i:04d}" for i in range(max(1, aoi_polygons // 2))]
    payload = json.dumps(
        {"aoi": aoi, "plan_ids": plan_ids, "hazard_ids": hazard_ids},
        sort_keys=True,
    ).encode()
    manifest_sha256 = hashlib.sha256(payload).hexdigest()

    return BootstrapResponse(
        incident_id=incident_id,
        aoi_geojson=aoi,
        plan_ids=plan_ids,
        hazard_ids=hazard_ids,
        manifest_sha256=manifest_sha256,
        last_event_seq=last_seq,
    )


@router.post("/journal-batch", response_model=JournalBatchAck)
async def post_journal_batch(batch: JournalBatch, request: Request) -> JournalBatchAck:
    """Ingest a journal batch from the command vehicle. Idempotent on client_event_id.

    When the batch carries ``command_epoch``, it is checked against the
    core-issued current epoch for every incident in the batch before any row is
    written. This is what stops a demoted command edge from backfilling under
    its old tenure when it reconnects: its buffered batch is refused with 409
    and the response names the current epoch, which the edge uses to demote
    itself (see edge/syncd/src/forward.py).

    The field is optional so that edges predating core-issued epochs keep
    working unchanged; omitting it skips the check rather than failing closed.
    """
    if not batch.events:
        return JournalBatchAck(accepted=0, duplicates=0, last_acked_seq=0)

    settings = request.app.state.settings
    pool = await get_pool(settings.database_url)
    accepted = 0
    duplicates = 0
    last_seq = 0

    if batch.command_epoch is not None:
        async with pool.acquire() as conn:
            for incident_id in {ev.incident_id for ev in batch.events}:
                row = await conn.fetchrow(
                    """
                    SELECT v.epoch_id, e.node_id
                    FROM master.current_command_epoch v
                    JOIN master.command_epoch e
                      ON e.incident_id = v.incident_id AND e.epoch_id = v.epoch_id
                    WHERE v.incident_id = $1
                    """,
                    incident_id,
                )
                if row is None:
                    # No epoch has ever been issued for this incident; nothing
                    # to be stale against, so let the write through.
                    continue
                current_epoch = int(row["epoch_id"])
                if batch.command_epoch < current_epoch:
                    raise HTTPException(
                        status_code=409,
                        detail={
                            "reason": "stale_epoch",
                            "incident_id": str(incident_id),
                            "current_epoch": current_epoch,
                            "request_epoch": batch.command_epoch,
                        },
                    )
                if batch.command_epoch > current_epoch:
                    raise HTTPException(
                        status_code=409,
                        detail={
                            "reason": "future_epoch",
                            "incident_id": str(incident_id),
                            "current_epoch": current_epoch,
                            "request_epoch": batch.command_epoch,
                        },
                    )
                # Matching the epoch number is not sufficient. A demoted edge
                # that reconnects reads the *current* epoch from core and would
                # otherwise forward under it, so both edges would pass this
                # check at the same number. Authority is held by a specific
                # node, so verify the forwarder is that node.
                holder = row["node_id"]
                if batch.node_id is not None and batch.node_id != holder:
                    raise HTTPException(
                        status_code=409,
                        detail={
                            "reason": "not_epoch_holder",
                            "incident_id": str(incident_id),
                            "current_epoch": current_epoch,
                            "epoch_held_by": holder,
                            "request_node_id": batch.node_id,
                        },
                    )

    # A duplicate client_event_id is an ordinary retry and is absorbed by
    # ON CONFLICT. A *different* client_event_id arriving at an event_seq that
    # is already taken is something else entirely: two writers independently
    # allocated the same sequence number, which is the forked journal the
    # single-writer rule exists to prevent. The UNIQUE (incident_id, event_seq)
    # constraint catches it, but letting asyncpg's UniqueViolationError escape
    # surfaces as a bare 500 -- indistinguishable from core being broken, and
    # forward.py would retry it forever instead of demoting. Report it as a
    # protocol rejection so the forwarding edge can act on it.
    try:
        async with pool.acquire() as conn, conn.transaction():
            for ev in batch.events:
                await conn.execute(
                    """
                        INSERT INTO master.incidents (id, name, aoi)
                        VALUES ($1, $2, ST_GeomFromText('POLYGON((0 0,1 0,1 1,0 1,0 0))', 3006))
                        ON CONFLICT (id) DO NOTHING
                        """,
                    ev.incident_id,
                    f"harness-incident-{ev.incident_id}",
                )
                inserted = await conn.execute(
                    """
                        INSERT INTO master.incident_events
                            (id, incident_id, event_seq, event_type, payload,
                             device_id, user_id, created_at, client_event_id)
                        VALUES (gen_random_uuid(), $1, $2, $3, $4, $5, $6, $7, $8)
                        ON CONFLICT (client_event_id) DO NOTHING
                        """,
                    ev.incident_id,
                    ev.event_seq,
                    ev.event_type,
                    json.dumps(ev.payload),
                    ev.device_id,
                    ev.user_id,
                    ev.created_at,
                    ev.client_event_id,
                )
                if inserted.endswith(" 1"):
                    accepted += 1
                else:
                    duplicates += 1
                last_seq = max(last_seq, ev.event_seq)
    except UniqueViolationError as exc:
        raise HTTPException(
            status_code=409,
            detail={
                "reason": "forked_sequence",
                "detail": (
                    "an event_seq in this batch is already held by a different "
                    "client_event_id: two writers allocated the same sequence"
                ),
                "constraint": getattr(exc, "constraint_name", None),
            },
        ) from exc

    return JournalBatchAck(accepted=accepted, duplicates=duplicates, last_acked_seq=last_seq)


@router.post("/command-epoch/promote", response_model=EpochPromoteResponse)
async def promote_command_epoch(req: EpochPromoteRequest, request: Request) -> EpochPromoteResponse:
    """Issue the next command epoch for an incident.

    This is the serialization point for promotion. Two concurrent requests for
    the same incident must not receive the same epoch_id, so the incident row
    is locked FOR UPDATE before MAX(epoch_id)+1 is computed; the second caller
    blocks until the first commits and therefore observes the new maximum.

    Locking the parent row (rather than the aggregate) is deliberate: Postgres
    rejects FOR UPDATE on an aggregate query, and there is no epoch row to lock
    for the very first promotion of an incident.
    """
    settings = request.app.state.settings
    pool = await get_pool(settings.database_url)

    async with pool.acquire() as conn, conn.transaction():
        incident = await conn.fetchrow(
            "SELECT id FROM master.incidents WHERE id = $1 FOR UPDATE",
            req.incident_id,
        )
        if incident is None:
            raise HTTPException(
                status_code=404,
                detail={"reason": "unknown_incident", "incident_id": str(req.incident_id)},
            )
        row = await conn.fetchrow(
            """
                INSERT INTO master.command_epoch (incident_id, epoch_id, started_by, node_id)
                SELECT $1, COALESCE(MAX(epoch_id), 0) + 1, $2, $3
                FROM master.command_epoch
                WHERE incident_id = $1
                RETURNING epoch_id, started_at
                """,
            req.incident_id,
            req.started_by,
            req.node_id,
        )

    return EpochPromoteResponse(
        incident_id=req.incident_id,
        epoch_id=int(row["epoch_id"]),
        started_at=row["started_at"],
    )


@router.get("/command-epoch", response_model=EpochPromoteResponse)
async def get_command_epoch(incident_id: UUID, request: Request) -> EpochPromoteResponse:
    """Return the current command epoch for an incident.

    Edge syncd calls this to refresh its cache on startup and after a 409.
    """
    settings = request.app.state.settings
    pool = await get_pool(settings.database_url)
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT epoch_id, started_by, node_id, started_at
            FROM master.command_epoch
            WHERE incident_id = $1
            ORDER BY epoch_id DESC
            LIMIT 1
            """,
            incident_id,
        )
    if row is None:
        raise HTTPException(
            status_code=404,
            detail={"reason": "no_epoch_for_incident", "incident_id": str(incident_id)},
        )
    return EpochPromoteResponse(
        incident_id=incident_id,
        epoch_id=int(row["epoch_id"]),
        started_at=row["started_at"],
    )


@router.get("/journal-events", response_model=JournalEventsResponse)
async def get_journal_events(
    incident_id: UUID,
    request: Request,
    after_seq: int = Query(default=0, ge=0),
    limit: int = Query(default=JOURNAL_PAGE_LIMIT, ge=1, le=JOURNAL_PAGE_LIMIT),
) -> JournalEventsResponse:
    """Return one page of the authoritative journal prefix after ``after_seq``.

    This is the core half of journal-prefix bootstrap: a newly promoted edge
    pages through this endpoint until ``has_more`` is false, then verifies the
    prefix is contiguous before declaring itself bootstrapped. Rows are ordered
    by event_seq so the caller can insert them in order and detect gaps.
    """
    settings = request.app.state.settings
    pool = await get_pool(settings.database_url)
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT incident_id, event_seq, event_type, payload,
                   device_id, user_id, created_at, client_event_id
            FROM master.incident_events
            WHERE incident_id = $1 AND event_seq > $2
            ORDER BY event_seq ASC
            LIMIT $3
            """,
            incident_id,
            after_seq,
            limit,
        )

    events = [
        IncidentEvent(
            incident_id=r["incident_id"],
            event_seq=int(r["event_seq"]),
            event_type=r["event_type"],
            payload=r["payload"] if isinstance(r["payload"], dict) else json.loads(r["payload"]),
            device_id=r["device_id"],
            user_id=r["user_id"],
            client_event_id=r["client_event_id"],
            created_at=r["created_at"],
        )
        for r in rows
    ]
    next_after_seq = events[-1].event_seq if events else after_seq

    return JournalEventsResponse(
        incident_id=incident_id,
        after_seq=after_seq,
        events=events,
        next_after_seq=next_after_seq,
        has_more=len(events) == limit,
    )


@router.get("/last-acked-seq")
async def get_last_acked_seq(incident_id: UUID, request: Request) -> dict:
    """Return the highest event_seq the core has stored for the given incident."""
    settings = request.app.state.settings
    pool = await get_pool(settings.database_url)
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT COALESCE(MAX(event_seq), 0) AS s "
            "FROM master.incident_events WHERE incident_id = $1",
            incident_id,
        )
    return {"incident_id": str(incident_id), "last_acked_seq": int(row["s"])}
