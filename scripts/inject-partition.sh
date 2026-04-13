#!/usr/bin/env bash
# inject-partition.sh - Inject a WAN or mesh partition for evaluation chaos testing
# Output metrics for the start and end of partitions

set -euo pipefail

DURATION=${1:-30} # partition duration in seconds
TARGET=${2:-"wan"} # "wan" or "mesh"

echo "{\"metric\": \"partition_injected\", \"target\": \"${TARGET}\", \"duration\": ${DURATION}, \"ts\": $(date +%s)}" >> eval_metrics.log

if [[ "$TARGET" == "wan" ]]; then
    echo "Simulating WAN partition (Core disconnected from Edge) for ${DURATION}s..."
    # In a real environment, we'd use `docker network disconnect core-net edge-ops-api` 
    # Mocking for the pilot eval phase:
    sleep "$DURATION"
elif [[ "$TARGET" == "mesh" ]]; then
    echo "Simulating Mesh partition (Responders disconnected from Command) for ${DURATION}s..."
    sleep "$DURATION"
else
    echo "Unknown target $TARGET"
    exit 1
fi

echo "{\"metric\": \"partition_resolved\", \"target\": \"${TARGET}\", \"ts\": $(date +%s)}" >> eval_metrics.log
echo "Partition resolved."
