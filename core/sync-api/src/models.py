"""Pydantic models for sync-api."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class IncidentEvent(BaseModel):
    incident_id: UUID
    event_seq: int
    event_type: str
    payload: dict
    device_id: str
    user_id: str
    client_event_id: UUID
    created_at: datetime


class JournalBatch(BaseModel):
    events: list[IncidentEvent]


class JournalBatchAck(BaseModel):
    accepted: int
    duplicates: int
    last_acked_seq: int


class BootstrapResponse(BaseModel):
    incident_id: UUID
    aoi_geojson: dict
    plan_ids: list[str]
    hazard_ids: list[str]
    manifest_sha256: str
    last_event_seq: int
