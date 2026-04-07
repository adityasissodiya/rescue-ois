"""Pydantic models for ops-api."""

from datetime import datetime

from pydantic import BaseModel


class FieldEdit(BaseModel):
    client_event_id: str
    incident_id: str
    event_type: str
    payload: dict
    device_id: str
    user_id: str
    occurred_at: datetime


class BootstrapResponse(BaseModel):
    master_version: str
    incident_id: str | None
    aoi_geojson: dict | None
    plan_ids: list[str]
    last_event_seq: int | None
