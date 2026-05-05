#!/usr/bin/env bash
# dev-down.sh - tear down core, command edge, and all responder edges.

set -euo pipefail

cd "$(dirname "$0")/.."
ROOT="$(pwd)"

cd "$ROOT/edge"
for proj in $(docker compose ls --format json 2>/dev/null | python3 -c '
import json, sys
for p in json.load(sys.stdin):
    if p["Name"].startswith("edge-resp-") or p["Name"] == "edge-cmd":
        print(p["Name"])
'); do
    echo "Stopping $proj..."
    docker compose -p "$proj" down -v || true
done

cd "$ROOT/core"
echo "Stopping core..."
docker compose -p core down -v || true

if docker network inspect rescue-ois-net >/dev/null 2>&1; then
    docker network rm rescue-ois-net || true
fi

echo "All down."
