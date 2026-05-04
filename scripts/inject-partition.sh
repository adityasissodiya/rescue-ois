#!/usr/bin/env bash
# inject-partition.sh - Inject a WAN or mesh partition for evaluation chaos testing
# Output metrics for the start and end of partitions

set -euo pipefail

DURATION=${1:-30} # partition duration in seconds
TARGET=${2:-"wan"} # "wan" or "mesh"
METRICS_PATH=${RESCUE_OIS_METRICS_PATH:-eval_metrics.jsonl}
RUN_ID=${RESCUE_OIS_RUN_ID:-manual}

log_event() {
    local metric_name=$1
    local notes=$2
    local timestamp
    timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    printf '{"run_id":"%s","scenario":"partition_%s","metric_name":"%s","value_ms":null,"timestamp_iso":"%s","notes":"%s"}\n' \
        "$RUN_ID" "$TARGET" "$metric_name" "$timestamp" "$notes" >> "$METRICS_PATH"
}

if [[ "$TARGET" == "wan" ]]; then
    log_event "partition_injected" "partition scaffold started for ${DURATION}s"
    echo "Simulating WAN partition (Core disconnected from Edge) for ${DURATION}s..."
    # In a real environment, we'd use `docker network disconnect core-net edge-ops-api` 
    # Mocking for the pilot eval phase:
    sleep "$DURATION"
elif [[ "$TARGET" == "mesh" ]]; then
    log_event "partition_injected" "partition scaffold started for ${DURATION}s"
    echo "Simulating Mesh partition (Responders disconnected from Command) for ${DURATION}s..."
    sleep "$DURATION"
else
    echo "Unknown target $TARGET"
    exit 1
fi

log_event "partition_resolved" "partition scaffold resolved"
echo "Partition resolved."
