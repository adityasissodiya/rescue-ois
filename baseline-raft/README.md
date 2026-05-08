# Raft Baseline

This directory contains a small three-voter `hashicorp/raft` baseline for the
paper evaluation. It mirrors only the journal-commit path: the HTTP leader
accepts event batches, appends each event through Raft, and the in-memory FSM
assigns per-incident sequence numbers with client-event-id deduplication.

The baseline is intentionally not a replacement for the prototype. It omits
outbox semantics, promotion procedures, mTLS, audit, tile serving, package
distribution, and durable storage.

Run:

```bash
docker network inspect rescue-ois-net >/dev/null 2>&1 || docker network create rescue-ois-net
docker compose -p baseline-raft -f baseline-raft/docker-compose.yml up -d --build
```

The HTTP APIs are exposed on host ports `18001`, `18002`, and `18003`.
