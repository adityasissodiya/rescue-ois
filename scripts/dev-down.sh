#!/usr/bin/env bash
# dev-down.sh — tear down the core stack
set -euo pipefail

cd "$(dirname "$0")/../core"
docker compose down
