"""Pydantic models for audit-api."""

from datetime import datetime

from pydantic import BaseModel


class AuditEvent(BaseModel):
    timestamp: datetime
    service: str
    action: str
    actor: str
    device_id: str | None = None
    detail: dict
    source_edge: str | None = None
