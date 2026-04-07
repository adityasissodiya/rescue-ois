"""Publication pipeline orchestrator.

Stages:
    1. staging validate     — sanity-check staging.* tables (geometry, FKs, NOT NULLs)
    2. promote              — copy validated rows from staging into master.*
    3. build PMTiles        — invoke pmtiles_builder for the configured layer set
    4. build attachments    — bundle attachments into tar.zst archives
    5. write manifest       — produce manifest.json + sha256sum.txt + signature
    6. publish              — atomic swap into PUBLISH_DIR
"""


async def run_pipeline(incident_id: str | None) -> None:
    """Execute the publication pipeline.

    If `incident_id` is provided, run an incident-specific publication that bundles
    only the AOI-relevant subset. Otherwise run the full regional publication.
    """
    # TODO: stage 1 - staging validation
    # TODO: stage 2 - promote staging -> master
    # TODO: stage 3 - build PMTiles via pmtiles_builder.build()
    # TODO: stage 4 - build attachments via attachments.bundle()
    # TODO: stage 5 - write manifest via manifest.write()
    # TODO: stage 6 - atomic publish swap into PUBLISH_DIR
    raise NotImplementedError
