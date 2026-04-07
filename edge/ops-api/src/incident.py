"""Incident journal & state access (command-role K430 only).

On a command vehicle, this module owns writes to `incident.journal` and
`incident.state`. On a responder vehicle, it raises if write methods are called
— responders only ever write to `outbox.device_outbox` via syncd.push.
"""


async def append_event(event: dict) -> int:
    """Append an event to the incident journal and return the assigned event_seq.

    Only callable on a command-role K430. Enforced via EDGE_ROLE check.
    """
    # TODO: check EDGE_ROLE == 'command', else raise; insert into incident.journal
    # with next event_seq, update incident.state projection, return seq.
    raise NotImplementedError


async def current_state(incident_id: str) -> dict:
    """Return the current incident.state projection for `incident_id`."""
    # TODO: SELECT FROM incident.state WHERE incident_id = ...
    raise NotImplementedError
