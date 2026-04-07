"""SMHI importer.

Pulls observations and forecasts (wind, precipitation, temperature) from SMHI
open data APIs into the core `staging` schema.
"""


class SMHIImporter:
    async def fetch(self) -> None:
        """Pull the latest SMHI observations and forecasts."""
        # TODO: implement SMHI Open Data REST fetch.
        raise NotImplementedError

    async def ingest(self, session) -> None:  # noqa: ANN001
        """Load SMHI data into staging.smhi_*."""
        # TODO: parse JSON, upsert into staging tables.
        raise NotImplementedError
