"""Lantmäteriet importer.

Pulls cadastral, base map, and elevation reference data from the Lantmäteriet
open and licensed APIs into the core `staging` schema.
"""


class LantmaterietImporter:
    async def fetch(self) -> None:
        """Pull the latest available datasets from Lantmäteriet."""
        # TODO: implement HTTP fetch from Lantmäteriet endpoints, write to local
        # spool, hand off to ingest().
        raise NotImplementedError

    async def ingest(self, session) -> None:  # noqa: ANN001 - SQLAlchemy session, typed at call site
        """Validate and load fetched data into staging.lantmateriet_*."""
        # TODO: validate against expected schema, upsert into staging tables,
        # mark a publication candidate row.
        raise NotImplementedError
