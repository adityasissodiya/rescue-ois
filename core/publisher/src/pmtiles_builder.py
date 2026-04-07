"""PMTiles builder.

Generates a single PMTiles archive per layer set defined in the publication
config. Uses tippecanoe (or equivalent) under the hood; the wrapper here is
responsible for ordering, zoom levels, and SRID handling.
"""


async def build(layer_set: str, output_path: str) -> None:
    """Build a PMTiles archive for `layer_set` at `output_path`."""
    # TODO: shell out to tippecanoe / pmtiles tooling, write to a temp path,
    # rename atomically into output_path on success.
    raise NotImplementedError
