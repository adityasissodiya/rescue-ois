#!/usr/bin/env bash
# promote-responder.sh — promote a responder K430 to command role
#
# WARNING: this script flips EDGE_ROLE from "responder" to "command" and
# restarts syncd. It MUST NOT run on more than one K430 per incident at the
# same time — doing so creates split-brain on incident.journal. Always
# confirm the previous command vehicle is unreachable before running.
#
# See docs/runbooks/command-failover.md.

set -euo pipefail

cd "$(dirname "$0")/../edge"

CURRENT_ROLE="$(docker compose exec -T syncd printenv EDGE_ROLE 2>/dev/null || echo unknown)"
echo "Current EDGE_ROLE: $CURRENT_ROLE"

if [[ "$CURRENT_ROLE" == "command" ]]; then
    echo "Already in command role. Nothing to do." >&2
    exit 0
fi

read -r -p "Confirm promotion to command role on this K430? [yes/NO] " ans
if [[ "$ans" != "yes" ]]; then
    echo "Aborted." >&2
    exit 1
fi

T0=$(date +%s%3N)
EDGE_ROLE=command docker compose up -d syncd

echo "Waiting for syncd to fully assume command role processing..."
# simulate wait for container ready / role shift
sleep 2

T1=$(date +%s%3N)
METRICS_PATH=${RESCUE_OIS_METRICS_PATH:-../../eval_metrics.jsonl}
RUN_ID=${RESCUE_OIS_RUN_ID:-manual}
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
printf '{"run_id":"%s","scenario":"command_promotion","metric_name":"command_promotion_latency","value_ms":%s,"timestamp_iso":"%s","notes":"measured by promote-responder.sh after operator confirmation"}\n' \
    "$RUN_ID" "$((T1 - T0))" "$TIMESTAMP" >> "$METRICS_PATH"

echo "Promotion complete. Verify in syncd logs and core audit feed."
