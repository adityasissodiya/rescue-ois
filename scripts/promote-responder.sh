#!/usr/bin/env bash
# promote-responder.sh — promote a responder K430 to command role (two-edge, fenced).
#
# This performs a *fenced* promotion with enforced preconditions, in this order:
#
#   1. The candidate must already hold the complete incident-journal prefix.
#      Enforced by running bootstrap_journal_prefix() inside the candidate's
#      syncd container; it refuses if the local prefix is not contiguous.
#   2. The new epoch is issued by the regional core, not locally. Core's
#      INSERT is the serialization point, so two concurrent promotions for the
#      same incident cannot receive the same epoch.
#   3. Only then is EDGE_ROLE flipped and syncd restarted.
#   4. Responders are repointed at the new command and restarted.
#
# Steps 1 and 2 are the difference from the previous single-edge version, which
# inserted an epoch into its own database and flipped role with no precondition
# at all. NOTE the new dependency: this script now requires reachability to
# core. Promotion while the candidate is fully isolated from core is
# deliberately NOT supported -- there is no safe way to issue an authoritative
# epoch without the witness, and pretending otherwise is what forks a journal.
#
# What this still does NOT do (unchanged, and documented in the runbook):
# it cannot detect whether the previous command is alive. It relies on the
# operator's confirmation. If the previous command is reachable and still
# accepting writes, its own lease and core's epoch check are what eventually
# fence it -- see edge/syncd/src/forward.py.
#
# Required environment:
#   INCIDENT_ID              incident being promoted (core epochs are per-incident)
#
# Optional:
#   EDGE_COMPOSE_PROJECT     default: edge-resp-1   (candidate compose project)
#   EDGE_DB_CONTAINER        default: <project>-postgres-1
#   EDGE_SYNCD_CONTAINER     default: <project>-syncd-1
#   EDGE_DB                  default: rescue_ois_edge
#   EDGE_SYNCD_HEALTH_URL    default: http://127.0.0.1:18201/health
#   CORE_API_URL             host-visible core sync-api (default http://127.0.0.1:18000)
#   CORE_BASE_URL            container-visible core (default http://sync-api.core:8000)
#   RESPONDER_PROJECTS       space-separated projects to repoint; default: auto-detect
#   RESCUE_OIS_METRICS_PATH  JSONL output (default ./eval_metrics.jsonl)
#   RESCUE_OIS_RUN_ID        run identifier
#   PROMOTION_NON_INTERACTIVE=1 with PREVIOUS_COMMAND_VEHICLE_ID and
#                            PREVIOUS_COMMAND_UNREACHABLE=yes to skip prompts
#
# See docs/runbooks/command-failover.md.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

INCIDENT_ID="${INCIDENT_ID:-}"
if [[ -z "$INCIDENT_ID" ]]; then
    echo "INCIDENT_ID is required (core command epochs are per-incident)." >&2
    exit 2
fi

EDGE_COMPOSE_PROJECT="${EDGE_COMPOSE_PROJECT:-edge-resp-1}"
EDGE_DB_CONTAINER="${EDGE_DB_CONTAINER:-${EDGE_COMPOSE_PROJECT}-postgres-1}"
EDGE_SYNCD_CONTAINER="${EDGE_SYNCD_CONTAINER:-${EDGE_COMPOSE_PROJECT}-syncd-1}"
EDGE_DB="${EDGE_DB:-rescue_ois_edge}"
EDGE_SYNCD_HEALTH_URL="${EDGE_SYNCD_HEALTH_URL:-http://127.0.0.1:18201/health}"
CORE_API_URL="${CORE_API_URL:-http://127.0.0.1:18000}"
CORE_BASE_URL="${CORE_BASE_URL:-http://sync-api.core:8000}"
NON_INTERACTIVE="${PROMOTION_NON_INTERACTIVE:-0}"

CURRENT_ROLE="$(docker exec "$EDGE_SYNCD_CONTAINER" printenv EDGE_ROLE 2>/dev/null || echo unknown)"
# Name the container actually inspected, not the compose project: the two are
# independently overridable and reporting the wrong one sends an operator to
# look at a different vehicle than the script just probed.
echo "Current EDGE_ROLE in $EDGE_SYNCD_CONTAINER (project $EDGE_COMPOSE_PROJECT): $CURRENT_ROLE"
if [[ "$CURRENT_ROLE" == "command" ]]; then
    echo "Already in command role. Nothing to do." >&2
    exit 0
fi

# --- operator confirmation ------------------------------------------------
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

T0=$(date +%s%3N)

# --- precondition 1: candidate holds the complete journal prefix ----------
echo "Precondition: bootstrapping journal prefix for $INCIDENT_ID from core..."
set +e
docker exec -e CORE_BASE_URL="$CORE_BASE_URL" -i "$EDGE_SYNCD_CONTAINER" python - "$INCIDENT_ID" <<'PY'
import asyncio, sys
from src.bootstrap import bootstrap_journal_prefix

ok = asyncio.run(bootstrap_journal_prefix(sys.argv[1]))
print("bootstrap_complete=%s" % ok)
sys.exit(0 if ok else 1)
PY
BOOTSTRAP_RC=$?
set -e
if [[ "$BOOTSTRAP_RC" -ne 0 ]]; then
    echo "ABORT: journal-prefix bootstrap did not complete; candidate does not hold a contiguous prefix." >&2
    echo "Promoting now would fork the incident journal. Nothing has been changed." >&2
    exit 3
fi
echo "Precondition met: contiguous prefix present."

# --- precondition 2: core issues the new epoch ----------------------------
echo "Requesting new command epoch from core for incident $INCIDENT_ID..."
EPOCH_RESPONSE="$(curl -fsS -X POST "$CORE_API_URL/sync/command-epoch/promote" \
    -H 'Content-Type: application/json' \
    -d "{\"incident_id\":\"$INCIDENT_ID\",\"started_by\":\"$OPERATOR_CONFIRMATION_RECEIVED|prev=$PREV_ID\",\"node_id\":\"$EDGE_COMPOSE_PROJECT\"}")" || {
    echo "ABORT: core did not issue an epoch. Promotion requires core reachability." >&2
    echo "Nothing has been changed; the candidate is still a responder." >&2
    exit 4
}
# `|| true` so a malformed response reaches the explicit check below with a
# readable message, instead of `set -e` killing the script on grep's exit 1.
NEW_EPOCH="$(printf '%s' "$EPOCH_RESPONSE" | grep -oE '"epoch_id":[0-9]+' | grep -oE '[0-9]+' || true)"
if [[ -z "$NEW_EPOCH" ]]; then
    echo "ABORT: could not parse epoch_id from core response: $EPOCH_RESPONSE" >&2
    exit 4
fi
echo "Core issued epoch $NEW_EPOCH."

# Mirror the epoch into the candidate's local table so it retains a usable
# fallback if core becomes unreachable later (see accept.py resolution order).
docker exec "$EDGE_DB_CONTAINER" psql -U postgres "$EDGE_DB" -qtAc \
    "INSERT INTO incident.command_epoch (epoch_id, started_by, node_id)
     VALUES ($NEW_EPOCH, '$OPERATOR_CONFIRMATION_RECEIVED|prev=$PREV_ID', '$EDGE_COMPOSE_PROJECT')
     ON CONFLICT (epoch_id) DO NOTHING;" >/dev/null 2>&1 || true

# --- step 3: flip role ----------------------------------------------------
#
# Preserve the published port. docker-compose.yml defaults syncd to
# ${SYNCD_PORT:-18081}, which is the port the *incumbent* command edge already
# publishes; recreating without carrying the candidate's own port forward makes
# it try to bind 18081 and collide with the edge it is replacing.
current_published_port() {
    docker port "$1" 8000/tcp 2>/dev/null | head -1 | sed -E 's/.*:([0-9]+)$/\1/'
}

CANDIDATE_PORT="${SYNCD_PORT:-$(current_published_port "$EDGE_SYNCD_CONTAINER")}"
if [[ -z "$CANDIDATE_PORT" ]]; then
    echo "ABORT: could not determine the published syncd port for $EDGE_SYNCD_CONTAINER." >&2
    echo "Set SYNCD_PORT explicitly. Nothing has been changed." >&2
    exit 5
fi
echo "Preserving published syncd port $CANDIDATE_PORT for $EDGE_COMPOSE_PROJECT."

cd "$ROOT/edge"
EDGE_ROLE=command COMPOSE_PROJECT_NAME="$EDGE_COMPOSE_PROJECT" \
CORE_BASE_URL="$CORE_BASE_URL" \
SYNCD_PORT="$CANDIDATE_PORT" \
    docker compose -p "$EDGE_COMPOSE_PROJECT" up -d --force-recreate syncd

for _ in $(seq 1 30); do
    if curl -fs "$EDGE_SYNCD_HEALTH_URL" >/dev/null 2>&1; then break; fi
    sleep 1
done

# --- step 4: repoint responders ------------------------------------------
NEW_COMMAND_PEER_URL="http://syncd.${EDGE_COMPOSE_PROJECT}:8000"
if [[ -n "${RESPONDER_PROJECTS:-}" ]]; then
    PROJECTS="$RESPONDER_PROJECTS"
else
    # `|| true` is load-bearing under `set -euo pipefail`: both greps exit 1
    # when they legitimately match nothing (no responders deployed, or the
    # only responder is the candidate being promoted). Without it the script
    # aborts *after* the role flip but *before* repointing and before writing
    # its metrics record -- leaving a fleet still pointed at the demoted edge
    # while reporting failure.
    PROJECTS="$(docker ps --format '{{.Names}}' \
        | grep -E '^edge-resp-[0-9]+-syncd-1$' \
        | sed -E 's/-syncd-1$//' \
        | grep -v "^${EDGE_COMPOSE_PROJECT}$" \
        | tr '\n' ' ' || true)"
fi

REPOINTED=0
for proj in $PROJECTS; do
    # Same port-preservation concern as the candidate above: recreating a
    # responder without its own published port would drop it onto the default
    # and collide with whichever edge already holds that port.
    proj_port="$(current_published_port "${proj}-syncd-1")"
    if [[ -z "$proj_port" ]]; then
        echo "  WARNING: could not determine published port for ${proj}-syncd-1; skipping repoint." >&2
        continue
    fi
    echo "Repointing $proj (port $proj_port) -> $NEW_COMMAND_PEER_URL"
    EDGE_ROLE=responder COMPOSE_PROJECT_NAME="$proj" \
    COMMAND_PEER_URL="$NEW_COMMAND_PEER_URL" \
    CORE_BASE_URL="$CORE_BASE_URL" \
    SYNCD_PORT="$proj_port" \
        docker compose -p "$proj" up -d --force-recreate syncd >/dev/null
    REPOINTED=$((REPOINTED + 1))
done
echo "Repointed $REPOINTED responder(s)."

T1=$(date +%s%3N)
LATENCY_MS=$((T1 - T0))

METRICS_PATH="${RESCUE_OIS_METRICS_PATH:-$ROOT/eval_metrics.jsonl}"
RUN_ID="${RESCUE_OIS_RUN_ID:-manual}"
TIMESTAMP="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

printf '{"run_id":"%s","scenario":"command_promotion_two_edge","metric_name":"command_promotion_latency","value_ms":%d,"timestamp_iso":"%s","scenario_params":{"incident_id":"%s","new_epoch":%d,"epoch_source":"core","latency_ms":%d,"operator_confirmation_received":"%s","previous_command_vehicle_id":"%s","edge_compose_project":"%s","bootstrap_verified":true,"responders_repointed":%d},"notes":"promote-responder.sh; fenced two-edge promotion: prefix bootstrap verified, core-issued epoch, then role flip"}\n' \
    "$RUN_ID" "$LATENCY_MS" "$TIMESTAMP" "$INCIDENT_ID" "$NEW_EPOCH" "$LATENCY_MS" \
    "$OPERATOR_CONFIRMATION_RECEIVED" "$PREV_ID" "$EDGE_COMPOSE_PROJECT" "$REPOINTED" >> "$METRICS_PATH"

echo "Promotion complete. incident=$INCIDENT_ID new_epoch=$NEW_EPOCH latency_ms=$LATENCY_MS"
echo "Record appended to $METRICS_PATH."
