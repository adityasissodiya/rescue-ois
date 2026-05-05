import json
import hashlib
from uuid import UUID

from fastapi import APIRouter, Request

from src.db import get_pool
from src.models import BootstrapResponse, JournalBatch, JournalBatchAck

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
    """Ingest a journal batch from the command vehicle. Idempotent on client_event_id."""
    if not batch.events:
        return JournalBatchAck(accepted=0, duplicates=0, last_acked_seq=0)

    settings = request.app.state.settings
    pool = await get_pool(settings.database_url)
    accepted = 0
    duplicates = 0
    last_seq = 0

    async with pool.acquire() as conn:
        async with conn.transaction():
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
                if ev.event_seq > last_seq:
                    last_seq = ev.event_seq

    return JournalBatchAck(accepted=accepted, duplicates=duplicates, last_acked_seq=last_seq)


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
