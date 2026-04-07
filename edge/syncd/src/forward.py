"""Forward incident journal slices to the regional core (command role).

Sync flow 5: Command → Core. Streams incremental incident.journal rows over
the WG overlay to core sync-api. Tracks the last acked seq locally for resume.
"""


async def run() -> None:
    """Continuously forward incident journal slices to core."""
    # TODO: SELECT FROM incident.journal WHERE event_seq > last_acked_seq
    # POST to {core_base_url}/sync/incident_events
    # On 200, persist new last_acked_seq locally
    raise NotImplementedError
