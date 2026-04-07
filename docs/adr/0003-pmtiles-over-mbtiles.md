# ADR-0003: PMTiles over MBTiles for Offline Tile Packages

## Status

Accepted

## Context

Vehicle K430s need to serve offline map tiles to field tablets via Martin. The two practical options are MBTiles (SQLite) and PMTiles (single-file, HTTP-range-request friendly). MBTiles is more widely supported in legacy GIS tooling, but it requires a SQLite handle and locking when served, which complicates concurrent reads, atomic swaps during package updates, and CDN-style range serving.

## Decision

Use **PMTiles** as the canonical offline package format. Martin serves PMTiles natively, the publisher builds them in the regional core, and `package-cache` on the edge stores and exposes them via Nginx with byte-range support. Atomic swaps are a single file rename.

## Consequences

**Positive:**

- One file per package — trivially atomic to swap or replace.
- HTTP range requests allow partial cache warming and resumable downloads from `sync-api`.
- No SQLite locking issues under concurrent reads.
- Martin supports PMTiles directly.

**Negative:**

- Slightly less mature tooling ecosystem in some legacy GIS workflows than MBTiles.
- Requires a build step in the publisher; we cannot just hand a tile directory off to the edge.
