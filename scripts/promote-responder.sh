#!/usr/bin/env bash
# promote-responder.sh — promote a responder K430 to command role.
#
# Performs the fenced promotion: insert a new row into incident.command_epoch
# on the local edge Postgres so the epoch_id increases monotonically, then
# flip EDGE_ROLE from responder to command and restart syncd so it picks up
# the new epoch on startup (see edge/syncd/src/accept.py::init_epoch_cache).
#
# WARNING: this script creates split-brain on incident.journal if the previous
# command vehicle is reachable and continues to accept writes. Always confirm
# the previous command is unreachable before running.
#
# Required environment (override per edge in multi-edge dev):
#   EDGE_COMPOSE_PROJECT   default: edge-resp-1   (docker compose -p name)
#   EDGE_DB_CONTAINER      default: edge-resp-1-postgres-1
#   EDGE_DB                default: rescue_ois_edge
#   EDGE_SYNCD_HEALTH_URL  default: http://127.0.0.1:18201/health
#
# Optional:
#   RESCUE_OIS_METRICS_PATH    where to append the JSONL promotion record
#                              (default: ./eval_metrics.jsonl in repo root)
#   RESCUE_OIS_RUN_ID          run identifier echoed into the JSONL record
#   PROMOTION_NON_INTERACTIVE  set to 1 to skip the operator prompts, with
#                              required env PREVIOUS_COMMAND_VEHICLE_ID and
#                              PREVIOUS_COMMAND_UNREACHABLE=yes
#
# See docs/runbooks/command-failover.md.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/edge"

EDGE_COMPOSE_PROJECT="${EDGE_COMPOSE_PROJECT:-edge-resp-1}"
EDGE_DB_CONTAINER="${EDGE_DB_CONTAINER:-edge-resp-1-postgres-1}"
EDGE_DB="${EDGE_DB:-rescue_ois_edge}"
EDGE_SYNCD_HEALTH_URL="${EDGE_SYNCD_HEALTH_URL:-http://127.0.0.1:18201/health}"
NON_INTERACTIVE="${PROMOTION_NON_INTERACTIVE:-0}"

CURRENT_ROLE="$(docker compose -p "$EDGE_COMPOSE_PROJECT" exec -T syncd printenv EDGE_ROLE 2>/dev/null || echo unknown)"
echo "Current EDGE_ROLE in $EDGE_COMPOSE_PROJECT: $CURRENT_ROLE"
if [[ "$CURRENT_ROLE" == "command" ]]; then
    echo "Already in command role. Nothing to do." >&2
    exit 0
fi

# Operator confirmation. Plan Phase 4.3: the script must require the operator
# to type the previous command vehicle id and confirm previous command is
# unreachable.
if [[ "$NON_INTERACTIVE" == "1" ]]; then
    PREV_ID="${PREVIOUS_COMMAND_VEHICLE_ID:-}"
    PREV_UNREACH="${PREVIOUS_COMMAND_UNREACHABLE:-}"
    if [[ -z "$PREV_ID" || "$PREV_UNREACH" != "yes" ]]; then
        echo "PROMOTION_NON_INTERACTIVE=1 requires PREVIOUS_COMMAND_VEHICLE_ID and PREVIOUS_COMMAND_UNREACHABLE=yes" >&2
        exit 2
    fi
    OPERATOR_CONFIRMATION_RECEIVED="non_interactive"
else
    read -r -p "Previous command vehicle id (e.g. edge-cmd): " PREV_ID
    if [[ -z "$PREV_ID" ]]; then
        echo "Aborted: previous command vehicle id required." >&2
        exit 1
    fi
    read -r -p "Has the previous command vehicle been confirmed unreachable? [yes/NO] " PREV_UNREACH
    if [[ "$PREV_UNREACH" != "yes" ]]; then
        echo "Aborted: previous command must be unreachable before promotion." >&2
        exit 1
    fi
    OPERATOR_CONFIRMATION_RECEIVED="interactive_typed:yes"
fi

# Capture old epoch from the local DB before insert (single source of truth
# for this edge; cross-edge coordination is out of scope here).
OLD_EPOCH="$(docker exec "$EDGE_DB_CONTAINER" psql -U postgres "$EDGE_DB" -tAc \
    "SELECT COALESCE(MAX(epoch_id), 0) FROM incident.command_epoch" 2>/dev/null || echo 0)"

T0=$(date +%s%3N)

NEW_EPOCH="$(docker exec "$EDGE_DB_CONTAINER" psql -U postgres "$EDGE_DB" -tAc \
    "INSERT INTO incident.command_epoch (started_by, node_id) VALUES \
     ('$OPERATOR_CONFIRMATION_RECEIVED|prev=$PREV_ID', '$EDGE_COMPOSE_PROJECT') \
     RETURNING epoch_id")"

EDGE_ROLE=command docker compose -p "$EDGE_COMPOSE_PROJECT" up -d --force-recreate syncd

# Wait for syncd to be healthy at its new role.
for _ in $(seq 1 30); do
    if curl -fs "$EDGE_SYNCD_HEALTH_URL" >/dev/null 2>&1; then
        break
    fi
    sleep 1
done

T1=$(date +%s%3N)
LATENCY_MS=$((T1 - T0))

METRICS_PATH="${RESCUE_OIS_METRICS_PATH:-$ROOT/eval_metrics.jsonl}"
RUN_ID="${RESCUE_OIS_RUN_ID:-manual}"
TIMESTAMP="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

printf '{"run_id":"%s","scenario":"command_promotion","metric_name":"command_promotion_latency","value_ms":%d,"timestamp_iso":"%s","scenario_params":{"old_epoch":%d,"new_epoch":%d,"latency_ms":%d,"operator_confirmation_received":"%s","previous_command_vehicle_id":"%s","edge_compose_project":"%s"},"notes":"promote-responder.sh; fenced promotion: command_epoch row inserted before EDGE_ROLE flip"}\n' \
    "$RUN_ID" "$LATENCY_MS" "$TIMESTAMP" "$OLD_EPOCH" "$NEW_EPOCH" "$LATENCY_MS" "$OPERATOR_CONFIRMATION_RECEIVED" "$PREV_ID" "$EDGE_COMPOSE_PROJECT" >> "$METRICS_PATH"

echo "Promotion complete. old_epoch=$OLD_EPOCH new_epoch=$NEW_EPOCH latency_ms=$LATENCY_MS"
echo "Record appended to $METRICS_PATH. Verify in syncd logs and core audit feed."
