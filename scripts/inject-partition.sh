#!/usr/bin/env bash
# inject-partition.sh - partition injection for the evaluation harness.
#
# Usage:
#   ./scripts/inject-partition.sh wan 60      # cut ONLY the command-to-core backhaul for 60s
#   ./scripts/inject-partition.sh mesh 60     # detach a responder edge from the network for 60s
#
# Two partition models, deliberately different:
#
#   wan  - Surgical command-core WAN cut. Drops traffic between the command
#          syncd and the regional core sync-api ONLY, using tc on the command
#          syncd's eth0 (CAP_NET_ADMIN is already granted for the netem
#          harness). The command edge keeps reaching its local Postgres and
#          all responder edges throughout; only the backhaul link is down.
#          This matches the V-F claim ("command-core WAN recovery only;
#          responder-command and incident-journal paths remain available").
#          A previous version used `docker network disconnect`, which also
#          severed the command edge from its own Postgres and from every
#          responder -- not a WAN partition. See git history.
#
#   mesh - Full detach of a responder edge from the bridge via
#          `docker network disconnect`. Used by the command-local isolation
#          harness, where the only requirement is that the responder syncd is
#          unreachable from the command edge; the responder is not written to
#          while isolated, so a full detach does not distort that measurement.
#
# Emits structured audit events to $RESCUE_OIS_PARTITION_AUDIT_PATH
# (default partition_audit.jsonl). These records are intentionally separate
# from the canonical evaluation metrics stream.

set -euo pipefail

TARGET="${1:-wan}"
DURATION="${2:-30}"
NETWORK_NAME="rescue-ois-net"
AUDIT_PATH="${RESCUE_OIS_PARTITION_AUDIT_PATH:-partition_audit.jsonl}"
RUN_ID="${RESCUE_OIS_RUN_ID:-manual}"
RESPONDER_INDEX="${RESPONDER_INDEX:-1}"
CMD_SYNCD_CONTAINER="${CMD_SYNCD_CONTAINER:-edge-cmd-syncd-1}"
CORE_SYNC_CONTAINER="${CORE_SYNC_CONTAINER:-core-sync-api-1}"
SYNCD_IFACE="${SYNCD_IFACE:-eth0}"

emit() {
    local metric="$1"
    local value_ms="$2"
    local notes="$3"
    local ts
    ts="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
    if [[ -z "$value_ms" ]]; then value_ms="null"; fi
    printf '{"run_id":"%s","scenario":"partition_%s","metric_name":"%s","value_ms":%s,"timestamp_iso":"%s","notes":"%s"}\n' \
        "$RUN_ID" "$TARGET" "$metric" "$value_ms" "$ts" "$notes" >> "$AUDIT_PATH"
}

container_ip() {
    docker inspect -f \
        '{{(index .NetworkSettings.Networks "'"$NETWORK_NAME"'").IPAddress}}' "$1"
}

# ---------------------------------------------------------------------------
# wan: surgical command<->core cut via tc on the command syncd.
# ---------------------------------------------------------------------------
wan_apply() {
    local core_ip="$1"
    # Egress command->core: route only core-destined packets into a netem band
    # that drops 100%. priomap is all-zero so every other flow stays in band
    # 1:1 (default pfifo) and is unaffected.
    docker exec "$CMD_SYNCD_CONTAINER" tc qdisc add dev "$SYNCD_IFACE" root handle 1: \
        prio bands 3 priomap 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
    docker exec "$CMD_SYNCD_CONTAINER" tc qdisc add dev "$SYNCD_IFACE" parent 1:2 handle 20: \
        netem loss 100%
    docker exec "$CMD_SYNCD_CONTAINER" tc filter add dev "$SYNCD_IFACE" protocol ip parent 1:0 prio 1 \
        u32 match ip dst "$core_ip/32" flowid 1:2
    # Ingress core->command: drop inbound packets sourced from core so any
    # already-established backhaul socket is fully severed (true link-down).
    docker exec "$CMD_SYNCD_CONTAINER" tc qdisc add dev "$SYNCD_IFACE" handle ffff: ingress
    docker exec "$CMD_SYNCD_CONTAINER" tc filter add dev "$SYNCD_IFACE" parent ffff: protocol ip prio 1 \
        u32 match ip src "$core_ip/32" action drop
}

wan_clear() {
    docker exec "$CMD_SYNCD_CONTAINER" tc qdisc del dev "$SYNCD_IFACE" root 2>/dev/null || true
    docker exec "$CMD_SYNCD_CONTAINER" tc qdisc del dev "$SYNCD_IFACE" ingress 2>/dev/null || true
}

run_wan() {
    for c in "$CMD_SYNCD_CONTAINER" "$CORE_SYNC_CONTAINER"; do
        if ! docker container inspect "$c" >/dev/null 2>&1; then
            echo "Container $c not found. Is the stack up?" >&2
            exit 1
        fi
    done
    local core_ip
    core_ip="$(container_ip "$CORE_SYNC_CONTAINER")"
    if [[ -z "$core_ip" ]]; then
        echo "Could not resolve core IP for $CORE_SYNC_CONTAINER on $NETWORK_NAME" >&2
        exit 1
    fi

    # Clean any leftover qdisc from a crashed prior run, then apply.
    wan_clear
    trap wan_clear EXIT

    local t0_ns
    t0_ns=$(date +%s%N)
    wan_apply "$core_ip"
    emit "partition_injected" "null" "model=tc-surgical core_ip=$core_ip iface=$SYNCD_IFACE duration_s=$DURATION"

    sleep "$DURATION"

    wan_clear
    trap - EXIT
    local t1_ns dur_ms
    t1_ns=$(date +%s%N)
    dur_ms=$(( (t1_ns - t0_ns) / 1000000 ))
    emit "partition_resolved" "$dur_ms" "model=tc-surgical core_ip=$core_ip duration_ms=$dur_ms"
    echo "WAN partition (command<->core, surgical) resolved after ${DURATION}s."
}

# ---------------------------------------------------------------------------
# mesh: full detach of a responder edge from the bridge.
# ---------------------------------------------------------------------------
run_mesh() {
    local container="edge-resp-${RESPONDER_INDEX}-syncd-1"
    if ! docker container inspect "$container" >/dev/null 2>&1; then
        echo "Container $container not found. Is the stack up?" >&2
        exit 1
    fi

    local aliases
    aliases=$(docker inspect "$container" -f \
        '{{range $i,$v := (index .NetworkSettings.Networks "'"$NETWORK_NAME"'").Aliases}}{{if $i}} {{end}}{{$v}}{{end}}')

    local t0_ns
    t0_ns=$(date +%s%N)
    docker network disconnect "$NETWORK_NAME" "$container"
    emit "partition_injected" "null" "model=docker-detach container=$container duration_s=$DURATION"

    sleep "$DURATION"

    local alias_args=()
    for a in $aliases; do alias_args+=(--alias "$a"); done
    docker network connect "${alias_args[@]}" "$NETWORK_NAME" "$container"
    local t1_ns dur_ms
    t1_ns=$(date +%s%N)
    dur_ms=$(( (t1_ns - t0_ns) / 1000000 ))
    emit "partition_resolved" "$dur_ms" "model=docker-detach container=$container duration_ms=$dur_ms"
    echo "Mesh partition on $container resolved after ${DURATION}s."
}

case "$TARGET" in
    wan)  run_wan ;;
    mesh) run_mesh ;;
    *)
        echo "Unknown target: $TARGET (expected wan|mesh)" >&2
        exit 1
        ;;
esac
