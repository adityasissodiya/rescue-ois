"""Forward incident journal slices to the regional core (command role).

Reads journal rows past the locally-tracked last_acked_seq_to_core, posts
batches to core sync-api /sync/journal-batch, advances the cursor on success.
Idempotent end-to-end via client_event_id.

Command-authority lease (T-09)
------------------------------
A network-isolated former command edge cannot be *told* that its epoch is
stale: there is no channel by which to tell it. The TLA+ model says the same
thing structurally -- its only safe promotion action requires the promoting
vehicle to still reach the vehicle it replaces. So instead of waiting to be
informed, a command edge fences *itself* on a timeout it cannot renew.

Every successful round-trip to core renews a lease stored in ``sync.state``
under ``command_lease_expires_at``. While the lease is valid the edge accepts
authority-bearing writes; once it lapses, ``accept.py`` refuses them. This
trades local write availability for a bound on how long two edges can both
believe they hold authority.

Two deliberate design choices:

* **The lease is renewed on a heartbeat, not only when there is traffic.** An
  idle command edge is still a command edge; if renewal depended on having
  rows to forward, a quiet incident would self-fence for no reason.
* **The gate fails open until the first renewal.** An edge that has never
  established a lease is not fenced. Without this, the single-edge fencing
  experiment -- which never contacts core -- would be refused instantly, and
  the existing measured result would be destroyed by a change meant to add to
  it.

Self-demotion: if core rejects a forwarded batch with a stale epoch, this edge
has been superseded while it was away. It records the demotion and stops
forwarding rather than retrying forever. The buffered rows are left in place
for manual reconciliation; automatic merge is explicitly out of scope.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time

import httpx

from src.config import settings
from src.db import get_kv, get_pool, set_kv

logger = logging.getLogger("syncd.forward")

POLL_INTERVAL_S = 1.0
BATCH_SIZE = 200
KV_KEY = "last_acked_seq_to_core"
KV_LEASE = "command_lease_expires_at"
KV_DEMOTED = "command_demoted"

# Core rejections that mean "you are no longer the writer for this incident",
# as opposed to a transient failure worth retrying.
#
#   stale_epoch      -- a newer epoch has been issued since this edge wrote
#   not_epoch_holder -- the epoch number matches, but it is held by another
#                       node; this is what a *reconnected* demoted edge sees,
#                       because it can read the current number from core and
#                       would otherwise look current to itself
#   forked_sequence  -- another writer already allocated one of these
#                       event_seq values, so this edge's journal has forked
#
# Treating only stale_epoch as demoting would leave a reconnected old command
# retrying not_epoch_holder forever instead of standing down.
DEMOTING_REJECTIONS = frozenset({"stale_epoch", "not_epoch_holder", "forked_sequence"})


_TIMEOUT = httpx.Timeout(15.0, connect=5.0, read=15.0, write=5.0, pool=5.0)


async def renew_lease(conn) -> int:
    """Extend the authority lease. Returns the new expiry (unix seconds)."""
    expires_at = int(time.time() + settings.lease_window_s)
    await set_kv(conn, KV_LEASE, expires_at)
    return expires_at


async def lease_is_valid(conn, now: float | None = None) -> bool:
    """True when no lease has been established yet, or the lease is unexpired.

    The "never established" case returns True by design; see module docstring.
    """
    expires_at = await get_kv(conn, KV_LEASE, 0)
    if expires_at == 0:
        return True
    return (now or time.time()) < expires_at


async def mark_demoted(conn, reason: str) -> None:
    await set_kv(conn, KV_DEMOTED, 1)
    logger.error(
        "AUTHORITY LOST: this edge has been superseded (%s). "
        "It will stop forwarding; buffered rows are retained for manual "
        "reconciliation. Operator action required.",
        reason,
    )


async def _heartbeat(conn, client: httpx.AsyncClient) -> bool:
    """Cheap core round-trip used to renew the lease when there is no traffic."""
    try:
        response = await client.get(f"{settings.core_base_url}/health")
    except httpx.RequestError:
        return False
    if response.status_code != 200:
        return False
    await renew_lease(conn)
    return True


def incident_cursor_key(incident_id) -> str:
    """Per-incident forwarding cursor key.

    The original implementation tracked a single global ``last_acked_seq_to_core``
    while ``event_seq`` is allocated *per incident*. Any edge that had forwarded
    a high sequence for one incident would then silently skip every lower
    sequence of a different incident, because the selection predicate was
    ``event_seq > <global cursor>``. Those events were never forwarded and never
    retried -- they were simply invisible to the forwarder.

    This was found by a two-edge test in which an edge holding a cursor of 99
    from one incident refused to forward seq 1 of another. The legacy global key
    is deliberately left in place rather than migrated: re-forwarding is
    harmless because core deduplicates on ``client_event_id``.
    """
    return f"{KV_KEY}:{incident_id}"


async def _forward_incident(conn, incident_id) -> int:
    """Forward one incident's pending journal slice. Returns rows forwarded."""
    key = incident_cursor_key(incident_id)
    last_acked = await get_kv(conn, key, 0)
    rows = await conn.fetch(
        """
        SELECT incident_id, event_seq, event_type, payload,
               device_id, user_id, created_at, client_event_id, command_epoch
        FROM incident.journal
        WHERE incident_id = $1 AND event_seq > $2
        ORDER BY event_seq ASC
        LIMIT $3
        """,
        incident_id,
        last_acked,
        BATCH_SIZE,
    )
    if not rows:
        return 0

    events = [
        {
            "incident_id": str(r["incident_id"]),
            "event_seq": int(r["event_seq"]),
            "payload": r["payload"] if isinstance(r["payload"], dict) else json.loads(r["payload"]),
            "event_type": r["event_type"],
            "device_id": r["device_id"],
            "user_id": r["user_id"],
            "client_event_id": str(r["client_event_id"]),
            "created_at": r["created_at"].isoformat(),
        }
        for r in rows
    ]

    body: dict = {"events": events}
    # Declare the epoch these rows were committed under so core can refuse a
    # superseded writer. Bootstrapped rows carry epoch 0 and are not claimed.
    epoch = int(rows[0]["command_epoch"])
    if epoch > 0:
        body["command_epoch"] = epoch
    # Declare which edge is forwarding. Core checks this against the node
    # recorded as holding the epoch: quoting the right epoch number is not
    # enough to establish authority, since a demoted edge that reconnects can
    # read the current number from core.
    if settings.node_id:
        body["node_id"] = settings.node_id

    url = f"{settings.core_base_url}/sync/journal-batch"
    t0 = time.perf_counter_ns()
    async with httpx.AsyncClient(timeout=_TIMEOUT) as fresh:
        try:
            resp = await asyncio.wait_for(fresh.post(url, json=body), timeout=17.0)
        except TimeoutError as e:
            raise httpx.ReadTimeout("asyncio wait_for fired") from e
    t1 = time.perf_counter_ns()

    if resp.status_code == 409:
        detail = {}
        try:
            parsed = resp.json()
            detail = parsed.get("detail") if isinstance(parsed, dict) else {}
        except ValueError:
            pass
        reason = detail.get("reason") if isinstance(detail, dict) else None
        if reason in DEMOTING_REJECTIONS:
            await mark_demoted(
                conn,
                f"core rejected forwarding for incident {incident_id} with "
                f"reason={reason} (current_epoch={detail.get('current_epoch')}, "
                f"epoch_held_by={detail.get('epoch_held_by')}, "
                f"this_node={settings.node_id or 'unset'})",
            )
        else:
            logger.warning("forward: core rejected 409 reason=%s", reason)
        return 0

    if resp.status_code != 200:
        logger.warning("forward: core rejected status=%s body=%s", resp.status_code, resp.text)
        return 0

    new_last_acked = max(int(r["event_seq"]) for r in rows)
    await set_kv(conn, key, new_last_acked)
    expires_at = await renew_lease(conn)
    logger.info(
        "forward ok incident=%s rows=%d cursor=%d latency_ns=%d lease_until=%d",
        incident_id,
        len(rows),
        new_last_acked,
        t1 - t0,
        expires_at,
    )
    return len(rows)


async def _forward_once(client: httpx.AsyncClient | None = None) -> int:
    pool = await get_pool(settings.database_url)
    async with pool.acquire() as conn:
        if await get_kv(conn, KV_DEMOTED, 0) == 1:
            return 0

        incidents = await conn.fetch("SELECT DISTINCT incident_id FROM incident.journal")

        total = 0
        for row in incidents:
            total += await _forward_incident(conn, row["incident_id"])
            if await get_kv(conn, KV_DEMOTED, 0) == 1:
                # Authority was lost mid-pass; stop rather than keep pushing.
                break

        if total == 0:
            # Idle: renew anyway, so a quiet command edge does not self-fence.
            async with httpx.AsyncClient(timeout=_TIMEOUT) as fresh:
                await _heartbeat(conn, fresh)
        return total


_ITERATION_DEADLINE_S = 25.0


async def run() -> None:
    if settings.edge_role != "command":
        logger.info("forward: not a command, exiting")
        return
    while True:
        try:
            forwarded = await asyncio.wait_for(
                _forward_once(), timeout=_ITERATION_DEADLINE_S
            )
        except TimeoutError:
            logger.warning("forward: iteration deadline exceeded, retrying")
            forwarded = 0
        except httpx.RequestError as e:
            logger.warning("forward: transport error: %s", e)
            forwarded = 0
        except Exception:
            # logger.exception already records the traceback; repeating the
            # exception object in the message duplicates it (ruff TRY401).
            logger.exception("forward: unhandled error in _forward_once")
            forwarded = 0
        await asyncio.sleep(POLL_INTERVAL_S if forwarded else POLL_INTERVAL_S * 2)
