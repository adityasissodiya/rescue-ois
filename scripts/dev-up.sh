#!/usr/bin/env bash
# dev-up.sh — start the core stack for local development
set -euo pipefail

cd "$(dirname "$0")/../core"
docker compose up -d
