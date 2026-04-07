#!/usr/bin/env bash
# build-pmtiles.sh — manually trigger the publisher pipeline to (re)build PMTiles
#
# Wraps the publisher service's pipeline.run_pipeline() entry point. Useful for
# operators who need to force a rebuild outside the normal scheduled cycle.

set -euo pipefail

INCIDENT_ID="${1:-}"

cd "$(dirname "$0")/../core"

if [[ -n "$INCIDENT_ID" ]]; then
    echo "Triggering incident-scoped publish for $INCIDENT_ID..."
    docker compose exec publisher python -c \
        "import asyncio; from src.pipeline import run_pipeline; asyncio.run(run_pipeline('$INCIDENT_ID'))"
else
    echo "Triggering full regional publish..."
    docker compose exec publisher python -c \
        "import asyncio; from src.pipeline import run_pipeline; asyncio.run(run_pipeline(None))"
fi
