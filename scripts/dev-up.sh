#!/usr/bin/env bash
# dev-up.sh - start core, command edge, and N responder edges on a shared network.
#
# Usage:
#   ./scripts/dev-up.sh                 # 1 responder (default)
#   RESPONDERS=3 ./scripts/dev-up.sh    # 3 responders, named edge-resp-1..3
#
# All projects attach to the rescue-ois-net external network so service DNS
# resolves across compose projects.

set -euo pipefail

RESPONDERS="${RESPONDERS:-1}"
NETWORK_NAME="rescue-ois-net"

if ! docker network inspect "$NETWORK_NAME" >/dev/null 2>&1; then
    echo "Creating external network $NETWORK_NAME..."
    docker network create "$NETWORK_NAME"
fi

cd "$(dirname "$0")/.."
ROOT="$(pwd)"

echo "Starting core stack..."
cd "$ROOT/core"
SYNC_API_PORT="${SYNC_API_PORT:-18000}" docker compose -p core up -d

echo "Starting command edge..."
cd "$ROOT/edge"
EDGE_ROLE=command \
COMPOSE_PROJECT_NAME=edge-cmd \
COMMAND_PEER_URL="" \
CORE_BASE_URL="http://sync-api.core:8000" \
OPS_API_PORT="${CMD_OPS_API_PORT:-18080}" \
SYNCD_PORT="${CMD_SYNCD_PORT:-18081}" \
docker compose -p edge-cmd up -d

for i in $(seq 1 "$RESPONDERS"); do
    echo "Starting responder edge $i..."
    EDGE_ROLE=responder \
    COMPOSE_PROJECT_NAME="edge-resp-$i" \
    COMMAND_PEER_URL="http://syncd.edge-cmd:8000" \
    CORE_BASE_URL="http://sync-api.core:8000" \
    OPS_API_PORT="$((18100 + i))" \
    SYNCD_PORT="$((18200 + i))" \
    docker compose -p "edge-resp-$i" up -d
done

echo "Up: 1 core, 1 command edge, $RESPONDERS responder edges, network=$NETWORK_NAME"
