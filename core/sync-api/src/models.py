"""Pydantic models for sync-api request/response payloads."""

from pydantic import BaseModel


class SyncEvent(BaseModel):
    seq: int
    table: str
    op: str
    row_id: str
    payload: dict


class BootstrapBundle(BaseModel):
    incident_id: str
    aoi_geojson: dict
    plan_ids: list[str]
    hazard_ids: list[str]
    attachment_paths: list[str]
