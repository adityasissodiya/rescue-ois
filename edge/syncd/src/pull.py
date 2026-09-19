"""Core-to-edge baseline pull. NOT IMPLEMENTED.

Sync flow 1 (core master data and published packages replicated down to every
vehicle edge) is deployment design only. No baseline replication, package
download, or HTTP range-request transfer is implemented in this prototype, and
the evaluation does not measure any of it.

This module previously contained a loop that slept and then emitted
``pull_sync_start`` / ``pull_sync_complete`` records with a fabricated
``latency_ms`` to a logger named ``eval_metrics``. Those numbers described
nothing that happened and shared a namespace with the real evaluation harness
output, so they were removed rather than left to be mistaken for measurements.

For the one replication path that *is* implemented -- fetching the
authoritative incident-journal prefix from core before a promotion -- see
``src/bootstrap.py``.
"""

from __future__ import annotations

import logging

logger = logging.getLogger("syncd.pull")


async def run() -> None:
    """No-op. Kept so the module remains importable and the gap stays visible.

    Not started by ``main.py``: the lifespan wires only ``push`` (responder) and
    ``forward`` (command).
    """
    logger.info("pull: core-to-edge baseline replication is not implemented; see bootstrap.py")
