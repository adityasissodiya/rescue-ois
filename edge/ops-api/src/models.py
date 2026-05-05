"""Pydantic models for ops-api."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class FieldEdit(BaseModel):
    client_event_id: UUID
    incident_id: UUID
    event_type: str
    payload: dict
    device_id: str
    user_id: str
    occurred_at: datetime


class BootstrapResponse(BaseModel):
    master_version: str
    incident_id: UUID | None
    last_event_seq: int | None
