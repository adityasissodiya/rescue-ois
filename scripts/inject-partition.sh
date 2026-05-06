#!/usr/bin/env bash
# inject-partition.sh - real partition injection via docker network manipulation.
#
# Usage:
#   ./scripts/inject-partition.sh wan 60      # disconnect command edge from core for 60s
#   ./scripts/inject-partition.sh mesh 60     # disconnect a responder from command for 60s
#
# Emits structured events to $RESCUE_OIS_METRICS_PATH (default eval_metrics.jsonl).

set -euo pipefail

TARGET="${1:-wan}"
DURATION="${2:-30}"
NETWORK_NAME="rescue-ois-net"
METRICS_PATH="${RESCUE_OIS_METRICS_PATH:-eval_metrics.jsonl}"
RUN_ID="${RESCUE_OIS_RUN_ID:-manual}"
RESPONDER_INDEX="${RESPONDER_INDEX:-1}"

container_for_target() {
    case "$1" in
        wan)  echo "edge-cmd-syncd-1" ;;
        mesh) echo "edge-resp-${RESPONDER_INDEX}-syncd-1" ;;
        *)    echo "" ;;
    esac
}

container="$(container_for_target "$TARGET")"
if [[ -z "$container" ]]; then
    echo "Unknown target: $TARGET (expected wan|mesh)" >&2
    exit 1
fi

if ! docker container inspect "$container" >/dev/null 2>&1; then
    echo "Container $container not found. Is the stack up?" >&2
    exit 1
fi

emit() {
    local metric="$1"
    local value_ms="$2"
    local notes="$3"
    local ts
    ts="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
    if [[ -z "$value_ms" ]]; then value_ms="null"; fi
    printf '{"run_id":"%s","scenario":"partition_%s","metric_name":"%s","value_ms":%s,"timestamp_iso":"%s","notes":"%s"}\n' \
        "$RUN_ID" "$TARGET" "$metric" "$value_ms" "$ts" "$notes" >> "$METRICS_PATH"
}

ALIASES=$(docker inspect "$container" -f \
    '{{range $i,$v := (index .NetworkSettings.Networks "'"$NETWORK_NAME"'").Aliases}}{{if $i}} {{end}}{{$v}}{{end}}')

T0_NS=$(date +%s%N)
docker network disconnect "$NETWORK_NAME" "$container"
emit "partition_injected" "null" "container=$container target=$TARGET duration_s=$DURATION"

sleep "$DURATION"

ALIAS_ARGS=()
for a in $ALIASES; do ALIAS_ARGS+=(--alias "$a"); done
docker network connect "${ALIAS_ARGS[@]}" "$NETWORK_NAME" "$container"
T1_NS=$(date +%s%N)

DURATION_MS=$(( (T1_NS - T0_NS) / 1000000 ))
emit "partition_resolved" "$DURATION_MS" "container=$container target=$TARGET duration_ms=$DURATION_MS"

echo "Partition $TARGET on $container resolved after ${DURATION}s."
