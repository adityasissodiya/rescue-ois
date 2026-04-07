#!/usr/bin/env bash
# run-migrations.sh — apply numbered SQL migrations against $DATABASE_URL
#
# Usage:
#   DATABASE_URL=postgresql://... ./scripts/run-migrations.sh         # apply core/db/migrations
#   DATABASE_URL=postgresql://... ./scripts/run-migrations.sh edge    # apply edge/db/migrations

set -euo pipefail

TIER="${1:-core}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MIGRATIONS_DIR="$ROOT/$TIER/db/migrations"

if [[ -z "${DATABASE_URL:-}" ]]; then
    echo "DATABASE_URL must be set" >&2
    exit 1
fi

if [[ ! -d "$MIGRATIONS_DIR" ]]; then
    echo "No migrations directory at $MIGRATIONS_DIR" >&2
    exit 1
fi

for sql in "$MIGRATIONS_DIR"/*.sql; do
    [[ -e "$sql" ]] || continue
    echo "Applying $(basename "$sql")..."
    psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f "$sql"
done

echo "Done."
