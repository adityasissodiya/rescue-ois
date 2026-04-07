"""Trafikverket importer.

Pulls road network, traffic events, and ferry schedules from the Trafikverket
Datex/REST APIs into the core `staging` schema.
"""


class TrafikverketImporter:
    async def fetch(self) -> None:
        """Pull the latest Trafikverket road and traffic data."""
        # TODO: implement Trafikverket REST fetch with API key auth.
        raise NotImplementedError

    async def ingest(self, session) -> None:  # noqa: ANN001
        """Load Trafikverket data into staging.trafikverket_*."""
        # TODO: parse, normalize, upsert.
        raise NotImplementedError
