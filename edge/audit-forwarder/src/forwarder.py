"""Audit forwarder loop.

Reads recent unforwarded audit events from the local audit table, batches them
according to BATCH_SIZE, posts them to the core audit-api, and marks them
forwarded once acked. Retries with exponential backoff on transient failures.
"""


async def run() -> None:
    """Continuously forward batches of audit events to core audit-api."""
    # TODO: SELECT FROM audit.local WHERE forwarded_at IS NULL LIMIT batch_size
    # POST to settings.core_audit_url
    # On 200, UPDATE forwarded_at; on transient error, backoff and retry.
    raise NotImplementedError
