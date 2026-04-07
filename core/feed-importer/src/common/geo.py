"""Geometry helpers for staging ingestion.

All Rescue OIS master geometries are stored in SRID 3006 (SWEREF 99 TM).
Importers should use the helpers here to convert source coordinates.
"""

SWEREF99_TM = 3006
WGS84 = 4326


def project_hint(source_srid: int) -> str:
    """Return a SQL fragment that projects from `source_srid` to SWEREF 99 TM."""
    return f"ST_Transform(ST_SetSRID(:geom, {source_srid}), {SWEREF99_TM})"
