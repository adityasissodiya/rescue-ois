"""Naturvårdsverket importer.

Pulls protected area, watercourse, and environmental sensitivity data from
Naturvårdsverket open data into the core `staging` schema.
"""


class NaturvardsverketImporter:
    async def fetch(self) -> None:
        """Pull the latest Naturvårdsverket datasets."""
        # TODO: implement Naturvårdsverket open data fetch.
        raise NotImplementedError

    async def ingest(self, session) -> None:  # noqa: ANN001
        """Load Naturvårdsverket data into staging.naturvardsverket_*."""
        # TODO: parse, validate, upsert.
        raise NotImplementedError
