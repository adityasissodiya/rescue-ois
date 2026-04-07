# audit-api

Receives audit events forwarded from edge `audit-forwarder` and writes them to the core `audit.events` table.

## Endpoints

- `POST /audit/events` — submit a batch of audit events
- `GET /audit/events` — query stored events (filtered by service, actor, device, time range)

## Run locally

```bash
pip install -e .
uvicorn src.main:app --reload
```

## Tests

```bash
pip install -e ".[dev]"
pytest
```

## Environment variables

| Variable       | Description                  |
|----------------|------------------------------|
| `DATABASE_URL` | PostgreSQL connection string |
