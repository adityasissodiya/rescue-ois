"""Protocol messages and their canonical, domain-separated encoding (spec/protocol.md, s. 5).

Every signed message is encoded as

    b"mandate-seed/v0" 0x00 <type> 0x00 <scope> 0x00 <canonical JSON of the fields>

where the canonical JSON has sorted keys, no whitespace, ASCII only, and admits only
integers, strings and null. The type and scope tags make a signature on one message type,
or for one scope, invalid for any other.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import ClassVar

PROTOCOL_TAG = "mandate-seed/v0"


def _check_field(name: str, value: object) -> None:
    if value is None or isinstance(value, str):
        return
    if isinstance(value, int) and not isinstance(value, bool):
        return
    raise TypeError(
        f"field {name!r} must be int, str or None, not {type(value).__name__}"
    )


@dataclass(frozen=True)
class Message:
    """Base class. Subclasses set KIND and declare their fields; `scope` comes first."""

    KIND: ClassVar[str] = ""
    scope: str

    def fields(self) -> dict[str, object]:
        d = asdict(self)
        for k, v in d.items():
            _check_field(k, v)
        return d

    def canonical_bytes(self) -> bytes:
        body = json.dumps(
            self.fields(), sort_keys=True, separators=(",", ":"), ensure_ascii=True
        )
        for part in (self.KIND, self.scope):
            if "\x00" in part:
                raise ValueError("NUL byte in a domain tag")
        return b"\x00".join(
            [
                PROTOCOL_TAG.encode(),
                self.KIND.encode(),
                self.scope.encode(),
                body.encode(),
            ]
        )

    def msg_id(self) -> str:
        """Short content identifier used in traces (not a security mechanism)."""
        return f"{self.KIND}:" + hashlib.sha256(self.canonical_bytes()).hexdigest()[:16]

    def describe(self) -> dict[str, object]:
        return {"type": self.KIND, **self.fields()}


@dataclass(frozen=True)
class Grant(Message):
    """Epoch `epoch` belongs to `holder` from `start`. `deputy` exists only in the
    11 November 2026 draft rules (orig-2026-11-11); seed-v0 grants leave it None."""

    KIND: ClassVar[str] = "grant"
    epoch: int
    holder: str
    start: int
    deputy: str | None = None


@dataclass(frozen=True)
class Renewal(Message):
    """Epoch `epoch` is extended to end time `end`."""

    KIND: ClassVar[str] = "renewal"
    epoch: int
    end: int


@dataclass(frozen=True)
class Command(Message):
    """A command signed by `holder` alone. `epoch` is None for lease-based baselines."""

    KIND: ClassVar[str] = "command"
    epoch: int | None
    holder: str
    cid: str
    payload: str


@dataclass(frozen=True)
class Lease(Message):
    """Baselines tc and xl: `holder` may command from `start` to `end`."""

    KIND: ClassVar[str] = "lease"
    holder: str
    start: int
    end: int


@dataclass(frozen=True)
class Order(Message):
    """Baseline qo-w: a quorum approves one command, valid from `start` to `end`."""

    KIND: ClassVar[str] = "order"
    holder: str
    cid: str
    payload: str
    start: int
    end: int


CERTIFICATE_KINDS = (Grant, Renewal, Lease, Order)
