# audit-forwarder

Batches local audit events on the vehicle K430 and forwards them to the regional core `audit-api` over the WireGuard overlay.

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

| Variable                | Description                              |
|-------------------------|------------------------------------------|
| `DATABASE_URL`          | PostgreSQL (edge K430)                   |
| `CORE_AUDIT_URL`        | https URL of core audit-api              |
| `BATCH_SIZE`            | Max events per forward batch (default 200)|
