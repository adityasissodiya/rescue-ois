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
    # Command epoch the forwarding edge believes it holds. Optional for
    # backward compatibility: edges predating core-issued epochs omit it and
    # are accepted unchecked. Once an edge sends it, a stale value is rejected
    # so a demoted command cannot backfill under its old tenure.
    command_epoch: int | None = None
    # Identity of the forwarding edge. Checked against the node recorded as
    # holding command_epoch: an epoch number alone does not establish who may
    # write, so without this two edges at the same epoch both pass.
    # Optional for backward compatibility, and only as trustworthy as the
    # transport -- the emulation uses unauthenticated identifiers (see the
    # paper's non-claims on WireGuard/mTLS).
    node_id: str | None = None


class JournalBatchAck(BaseModel):
    accepted: int
    duplicates: int
    last_acked_seq: int


class EpochPromoteRequest(BaseModel):
    incident_id: UUID
    started_by: str
    node_id: str


class EpochPromoteResponse(BaseModel):
    incident_id: UUID
    epoch_id: int
    started_at: datetime


class JournalEventsResponse(BaseModel):
    """One page of the authoritative journal prefix, for edge bootstrap."""

    incident_id: UUID
    after_seq: int
    events: list[IncidentEvent]
    next_after_seq: int
    has_more: bool


class BootstrapResponse(BaseModel):
    incident_id: UUID
    aoi_geojson: dict
    plan_ids: list[str]
    hazard_ids: list[str]
    manifest_sha256: str
    last_event_seq: int
