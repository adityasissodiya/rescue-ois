"""Operation-based LWW Element Set used by the Hanssen-style baseline.

Hanssen 2025 evaluates operation-based CRDT replication for emergency-management
systems using LWW-Element-Set semantics: elements have immutable UUIDs, operations
are ADD/UPD/DEL, each operation carries a physical-clock timestamp, and the latest
timestamp wins. This module implements that narrow comparison point.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from time import time_ns
from typing import Any, Iterable, Literal
from uuid import uuid4

OperationKind = Literal["add", "upd", "del"]


@dataclass(frozen=True, order=True)
class Version:
    """Deterministic LWW version tuple.

    The timestamp is the semantic LWW component. replica_id/op_id only break ties
    so all replicas converge even when two operations have the same timestamp.
    """

    timestamp_ns: int
    replica_id: str
    op_id: str


@dataclass
class FieldValue:
    value: Any
    version: Version


@dataclass
class ElementState:
    fields: dict[str, FieldValue] = field(default_factory=dict)
    tombstone: Version | None = None

    def visible_fields(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for name, cell in self.fields.items():
            if self.tombstone is None or cell.version > self.tombstone:
                result[name] = cell.value
        return result

    def is_visible(self) -> bool:
        return bool(self.visible_fields())


@dataclass(frozen=True)
class Operation:
    op_id: str
    kind: OperationKind
    element_id: str
    fields: dict[str, Any]
    timestamp_ns: int
    replica_id: str

    @classmethod
    def new(
        cls,
        *,
        kind: OperationKind,
        element_id: str,
        replica_id: str,
        fields: dict[str, Any] | None = None,
        timestamp_ns: int | None = None,
        op_id: str | None = None,
    ) -> "Operation":
        return cls(
            op_id=op_id or str(uuid4()),
            kind=kind,
            element_id=element_id,
            fields=dict(fields or {}),
            timestamp_ns=timestamp_ns if timestamp_ns is not None else time_ns(),
            replica_id=replica_id,
        )

    @property
    def version(self) -> Version:
        return Version(self.timestamp_ns, self.replica_id, self.op_id)

    def to_json(self) -> dict[str, Any]:
        return {
            "op_id": self.op_id,
            "kind": self.kind,
            "element_id": self.element_id,
            "fields": self.fields,
            "timestamp_ns": self.timestamp_ns,
            "replica_id": self.replica_id,
        }

    @classmethod
    def from_json(cls, payload: dict[str, Any]) -> "Operation":
        return cls(
            op_id=str(payload["op_id"]),
            kind=payload["kind"],
            element_id=str(payload["element_id"]),
            fields=dict(payload.get("fields") or {}),
            timestamp_ns=int(payload["timestamp_ns"]),
            replica_id=str(payload["replica_id"]),
        )


class LWWElementSet:
    """In-memory operation-based LWW Element Set."""

    def __init__(self, replica_id: str) -> None:
        self.replica_id = replica_id
        self._elements: dict[str, ElementState] = {}
        self._ops: dict[str, Operation] = {}

    def reset(self) -> None:
        self._elements.clear()
        self._ops.clear()

    def local_edit(
        self,
        element_id: str,
        fields: dict[str, Any],
        *,
        timestamp_ns: int | None = None,
        op_id: str | None = None,
    ) -> Operation:
        op = Operation.new(
            kind="upd",
            element_id=element_id,
            fields=fields,
            timestamp_ns=timestamp_ns,
            replica_id=self.replica_id,
            op_id=op_id,
        )
        self.apply(op)
        return op

    def local_delete(
        self,
        element_id: str,
        *,
        timestamp_ns: int | None = None,
        op_id: str | None = None,
    ) -> Operation:
        op = Operation.new(
            kind="del",
            element_id=element_id,
            fields={},
            timestamp_ns=timestamp_ns,
            replica_id=self.replica_id,
            op_id=op_id,
        )
        self.apply(op)
        return op

    def apply_many(self, ops: Iterable[Operation]) -> int:
        count = 0
        for op in ops:
            if self.apply(op):
                count += 1
        return count

    def apply(self, op: Operation) -> bool:
        if op.op_id in self._ops:
            return False
        self._ops[op.op_id] = op
        element = self._elements.setdefault(op.element_id, ElementState())
        if op.kind in {"add", "upd"}:
            for key, value in op.fields.items():
                current = element.fields.get(key)
                if current is None or op.version > current.version:
                    element.fields[key] = FieldValue(value=value, version=op.version)
        elif op.kind == "del":
            if element.tombstone is None or op.version > element.tombstone:
                element.tombstone = op.version
        else:  # pragma: no cover - guarded by typing and service validation
            raise ValueError(f"unknown operation kind: {op.kind}")
        return True

    def operations(self) -> list[Operation]:
        return sorted(self._ops.values(), key=lambda op: (op.timestamp_ns, op.replica_id, op.op_id))

    def state(self) -> dict[str, dict[str, Any]]:
        result: dict[str, dict[str, Any]] = {}
        for element_id, element in sorted(self._elements.items()):
            visible = element.visible_fields()
            if visible:
                result[element_id] = visible
        return result

    def metadata(self) -> dict[str, Any]:
        return {
            "replica_id": self.replica_id,
            "op_count": len(self._ops),
            "element_count": len(self._elements),
            "visible_element_count": len(self.state()),
            "digest": self.digest(),
        }

    def digest(self) -> str:
        payload = repr(sorted((k, sorted(v.items())) for k, v in self.state().items())).encode()
        return sha256(payload).hexdigest()
