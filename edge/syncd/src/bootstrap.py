"""Journal-prefix bootstrap: pull the authoritative prefix from core (T-05).

A vehicle edge may only be promoted to command once it already holds the full
incident-journal prefix. Without this, a promoted edge would begin sequencing
from an empty journal and fork history. This module is the edge half of that
handshake; the core half is ``GET /sync/journal-events`` in
``core/sync-api/src/routes/sync.py``.

Protocol:

1. Page ``GET /sync/journal-events`` until ``has_more`` is false.
2. Insert each row into ``incident.journal``, idempotent on ``client_event_id``
   (unique index from edge migration 004), so a resumed or repeated bootstrap
   cannot duplicate rows.
3. Advance ``incident.state.last_event_seq`` to the end of the prefix.
4. Verify the local prefix is contiguous from 1 before reporting success.

Step 3 is essential and easy to miss: ``accept.py`` allocates the next
``event_seq`` from ``incident.state.last_event_seq`` under ``FOR UPDATE``. If
the state row were left at 0 after inserting an inherited prefix, the newly
promoted command would restart numbering at 1 and immediately violate
``UNIQUE (incident_id, event_seq)``.

Bootstrapped rows are stamped ``command_epoch = 0``, marking them as inherited
rather than committed under this edge's own tenure. Rows this edge accepts
after promotion carry its real epoch, so the journal records where authority
changed hands.

This module replaces the core-to-edge replication that ``pull.py`` previously
only claimed to perform.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any
from uuid import UUID

import httpx

from src.config import settings
from src.db import get_pool

logger = logging.getLogger("syncd.bootstrap")

PAGE_LIMIT = 500
_TIMEOUT = httpx.Timeout(30.0, connect=5.0, read=30.0, write=5.0, pool=5.0)


def verify_contiguous_prefix(row_count: int, min_seq: int | None, max_seq: int | None) -> bool:
    """Return True when the local journal holds a gap-free prefix from 1.

    Kept pure so it can be unit-tested without a database, mirroring
    ``accept.validate_request_epoch``.

    An empty journal is a valid (empty) prefix: an incident with no events yet
    is legitimately bootstrapped. Otherwise the prefix must start at 1 and have
    exactly as many rows as its highest sequence number.
    """
    if row_count == 0:
        return min_seq is None and max_seq is None
    if min_seq != 1:
        return False
    return max_seq == row_count


def _parse_ts(value: Any) -> datetime:
    """Core serializes created_at as an ISO-8601 string; asyncpg needs a datetime.

    ``accept.py`` never needs this because Pydantic has already coerced the
    value before it reaches the insert. Here the row arrives as raw JSON, so
    the conversion is ours to make. Accepts a trailing ``Z`` as well as an
    explicit UTC offset.
    """
    if isinstance(value, datetime):
        return value
    text = str(value)
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    return datetime.fromisoformat(text)


async def _insert_page(conn: Any, incident_id: UUID, events: list[dict]) -> int:
    inserted = 0
    for ev in events:
        payload = ev["payload"]
        result = await conn.execute(
            """
            INSERT INTO incident.journal
                (id, incident_id, event_seq, event_type, payload,
                 device_id, user_id, created_at, client_event_id, command_epoch)
            VALUES (gen_random_uuid(), $1, $2, $3, $4, $5, $6, $7, $8, 0)
            ON CONFLICT (client_event_id) DO NOTHING
            """,
            incident_id,
            int(ev["event_seq"]),
            ev["event_type"],
            json.dumps(payload) if isinstance(payload, (dict, list)) else payload,
            ev["device_id"],
            ev["user_id"],
            _parse_ts(ev["created_at"]),
            UUID(str(ev["client_event_id"])),
        )
        if result.endswith(" 1"):
            inserted += 1
    return inserted


async def bootstrap_journal_prefix(
    incident_id: str | UUID,
    *,
    page_limit: int = PAGE_LIMIT,
    client: httpx.AsyncClient | None = None,
) -> bool:
    """Fetch and install the authoritative journal prefix for one incident.

    Returns True only if the resulting local journal is a contiguous prefix.
    A False return means the edge must not be promoted.
    """
    incident_uuid = incident_id if isinstance(incident_id, UUID) else UUID(str(incident_id))
    pool = await get_pool(settings.database_url)
    url = f"{settings.core_base_url}/sync/journal-events"

    owns_client = client is None
    http = client or httpx.AsyncClient(timeout=_TIMEOUT)
    after_seq = 0
    fetched = 0
    inserted_total = 0

    try:
        while True:
            response = await http.get(
                url,
                params={
                    "incident_id": str(incident_uuid),
                    "after_seq": after_seq,
                    "limit": page_limit,
                },
            )
            if response.status_code != 200:
                logger.error(
                    "bootstrap: core returned status=%s body=%s",
                    response.status_code,
                    response.text[:200],
                )
                return False

            body = response.json()
            events = body.get("events") or []
            if events:
                async with pool.acquire() as conn, conn.transaction():
                    inserted_total += await _insert_page(conn, incident_uuid, events)
                fetched += len(events)

            if not body.get("has_more"):
                break

            next_after = int(body.get("next_after_seq", after_seq))
            if next_after <= after_seq:
                # Defensive: a non-advancing cursor would loop forever.
                logger.error(
                    "bootstrap: cursor did not advance (after_seq=%d, next=%d); aborting",
                    after_seq,
                    next_after,
                )
                return False
            after_seq = next_after
    finally:
        if owns_client:
            await http.aclose()

    async with pool.acquire() as conn, conn.transaction():
        row = await conn.fetchrow(
            """
            SELECT count(*) AS n, min(event_seq) AS lo, max(event_seq) AS hi
            FROM incident.journal
            WHERE incident_id = $1
            """,
            incident_uuid,
        )
        row_count = int(row["n"])
        min_seq = int(row["lo"]) if row["lo"] is not None else None
        max_seq = int(row["hi"]) if row["hi"] is not None else None

        if not verify_contiguous_prefix(row_count, min_seq, max_seq):
            logger.error(
                "bootstrap: prefix not contiguous (rows=%d min=%s max=%s); refusing",
                row_count,
                min_seq,
                max_seq,
            )
            return False

        # Advance the sequencing cursor so post-promotion accepts continue
        # after the inherited prefix instead of colliding with it.
        await conn.execute(
            """
            INSERT INTO incident.state (incident_id, last_event_seq, state)
            VALUES ($1, $2, '{}'::jsonb)
            ON CONFLICT (incident_id) DO UPDATE
                SET last_event_seq = GREATEST(incident.state.last_event_seq, EXCLUDED.last_event_seq),
                    updated_at = now()
            """,
            incident_uuid,
            max_seq or 0,
        )

    logger.info(
        "bootstrap ok incident=%s fetched=%d inserted=%d prefix_len=%d",
        incident_uuid,
        fetched,
        inserted_total,
        row_count,
    )
    return True
