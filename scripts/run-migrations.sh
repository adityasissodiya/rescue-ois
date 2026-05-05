#!/usr/bin/env bash
# run-migrations.sh — apply numbered SQL migrations against $DATABASE_URL
#
# Usage:
#   DATABASE_URL=postgresql://... ./scripts/run-migrations.sh         # apply core/db/migrations
#   DATABASE_URL=postgresql://... ./scripts/run-migrations.sh edge    # apply edge/db/migrations
#   ./scripts/run-migrations.sh                                      # apply inside core-postgres-1
#   ./scripts/run-migrations.sh edge                                 # apply inside all edge-* Postgres containers

set -euo pipefail

TIER="${1:-core}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MIGRATIONS_DIR="$ROOT/$TIER/db/migrations"

if [[ ! -d "$MIGRATIONS_DIR" ]]; then
    echo "No migrations directory at $MIGRATIONS_DIR" >&2
    exit 1
fi

apply_via_url() {
    for sql in "$MIGRATIONS_DIR"/*.sql; do
        [[ -e "$sql" ]] || continue
        echo "Applying $(basename "$sql")..."
        psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f "$sql"
    done
}

apply_in_container() {
    local container="$1"
    local db="$2"
    for sql in "$MIGRATIONS_DIR"/*.sql; do
        [[ -e "$sql" ]] || continue
        echo "Applying $(basename "$sql") in $container..."
        docker exec -i "$container" psql -U postgres "$db" -v ON_ERROR_STOP=1 < "$sql"
    done
}

if [[ -n "${DATABASE_URL:-}" ]]; then
    apply_via_url
else
    if [[ "$TIER" == "core" ]]; then
        if ! docker container inspect core-postgres-1 >/dev/null 2>&1; then
            echo "DATABASE_URL is not set and core-postgres-1 is not running" >&2
            exit 1
        fi
        apply_in_container core-postgres-1 rescue_ois
    elif [[ "$TIER" == "edge" ]]; then
        found=0
        while IFS= read -r container; do
            case "$container" in
                edge-*-postgres-1)
                    found=1
                    apply_in_container "$container" rescue_ois_edge
                    ;;
            esac
        done < <(docker ps --format '{{.Names}}')
        if [[ "$found" -eq 0 ]]; then
            echo "DATABASE_URL is not set and no edge-*-postgres-1 containers are running" >&2
            exit 1
        fi
    else
        echo "Unsupported tier without DATABASE_URL: $TIER" >&2
        exit 1
    fi
fi

echo "Done."
