#!/usr/bin/env bash
# dev-up.sh — start the core and multi-edge stack for evaluation

set -euo pipefail

echo "Starting core stack..."
cd "$(dirname "$0")/../core"
docker compose up -d

echo "Starting edge command node..."
cd ../edge
EDGE_ROLE=command docker compose -p edge-cmd up -d

echo "Starting edge responder node..."
EDGE_ROLE=responder docker compose -p edge-resp up -d

echo "Core, Command Edge, and Responder Edge started."
