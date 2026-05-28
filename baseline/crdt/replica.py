"""FastAPI replica for the CRDT-LWW baseline."""

from __future__ import annotations

import os
from time import time_ns
from typing import Any
from uuid import uuid4

from fastapi import FastAPI
from pydantic import BaseModel, Field

from crdt_lww import LWWElementSet, Operation

REPLICA_ID = os.environ.get("REPLICA_ID", "replica")
store = LWWElementSet(REPLICA_ID)
app = FastAPI(title="CRDT-LWW baseline replica")


class EditRequest(BaseModel):
    element_id: str = Field(default_factory=lambda: str(uuid4()))
    fields: dict[str, Any]
    timestamp_ns: int | None = None
    op_id: str | None = None


class DeleteRequest(BaseModel):
    element_id: str
    timestamp_ns: int | None = None
    op_id: str | None = None


class PushRequest(BaseModel):
    ops: list[dict[str, Any]]


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "replica_id": REPLICA_ID}


@app.post("/admin/reset")
def reset() -> dict[str, Any]:
    store.reset()
    return {"status": "reset", **store.metadata()}


@app.post("/ops/edit")
def edit(req: EditRequest) -> dict[str, Any]:
    op = store.local_edit(
        req.element_id,
        req.fields,
        timestamp_ns=req.timestamp_ns if req.timestamp_ns is not None else time_ns(),
        op_id=req.op_id,
    )
    return {"op": op.to_json(), "state": store.state(), **store.metadata()}


@app.post("/ops/delete")
def delete(req: DeleteRequest) -> dict[str, Any]:
    op = store.local_delete(
        req.element_id,
        timestamp_ns=req.timestamp_ns if req.timestamp_ns is not None else time_ns(),
        op_id=req.op_id,
    )
    return {"op": op.to_json(), "state": store.state(), **store.metadata()}


@app.get("/sync/pull")
def pull() -> dict[str, Any]:
    return {"ops": [op.to_json() for op in store.operations()], **store.metadata()}


@app.post("/sync/push")
def push(req: PushRequest) -> dict[str, Any]:
    applied = store.apply_many(Operation.from_json(op) for op in req.ops)
    return {"applied": applied, "state": store.state(), **store.metadata()}


@app.get("/state")
def state() -> dict[str, Any]:
    return {"state": store.state(), **store.metadata()}
