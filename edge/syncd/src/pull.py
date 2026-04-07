"""Pull baseline master data and published packages from the regional core.

Sync flow 1: Core → Vehicle baseline. Both responder and command roles run
this. Polls `sync-api`/`packages` over the WireGuard overlay, applies master
events to the local edge cache, and downloads new package files via HTTP range
requests for resumable transfer.
"""


async def run() -> None:
    """Continuously pull master events and packages from core into the local cache."""
    # TODO: GET /sync/events?after_seq=<local_max>; apply each event into edge
    # cache schema; poll /packages/manifest.json; download new artifacts via
    # range requests; verify sha256 against the manifest.
    raise NotImplementedError
