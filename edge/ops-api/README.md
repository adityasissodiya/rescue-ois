# ops-api

Vehicle K430 HTTPS API serving field tablets over the local OPS-TABLET VLAN.

## Endpoints

- `GET /api/bootstrap` — initial bundle for a tablet (master subset, AOI, plan refs)
- `GET /api/search` — local search across cached sites/plans/hazards
- `POST /api/events` — submit a field edit (idempotent via client UUID)
- `GET /tiles/{path}` — local vector tiles
- `GET /files/{path}` — attachment files

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

| Variable        | Description                                  |
|-----------------|----------------------------------------------|
| `DATABASE_URL`  | PostgreSQL (edge K430)                       |
| `EDGE_ROLE`     | `command` or `responder` (default responder) |
| `FILES_DIR`     | Path to local attachment cache               |
