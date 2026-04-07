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

EDGE_ROLE=command docker compose up -d syncd
echo "Promotion complete. Verify in syncd logs and core audit feed."
