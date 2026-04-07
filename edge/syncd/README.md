# syncd

Edge sync daemon. Behavior depends on `EDGE_ROLE`:

- **responder**: pulls master baseline from core; pushes `outbox.device_outbox` entries to the command vehicle's syncd accept endpoint.
- **command**: pulls master baseline from core; accepts and sequences events from responders into `incident.journal`; forwards the journal to core `sync-api`.

## Run locally

```bash
pip install -e .
EDGE_ROLE=responder uvicorn src.main:app --reload
```

## Tests

```bash
pip install -e ".[dev]"
pytest
```

## Environment variables

| Variable        | Description                                           |
|-----------------|-------------------------------------------------------|
| `DATABASE_URL`  | PostgreSQL (edge K430)                                |
| `EDGE_ROLE`     | `command` or `responder`                              |
| `CORE_BASE_URL` | https URL of the regional core sync-api               |
| `COMMAND_PEER_URL` | https URL of the command K430 (responder mode only)|
