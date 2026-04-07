# sync-api

Core HTTPS API exposed to vehicle K430 `syncd` over the WireGuard overlay. Serves master baseline, incident bootstrap, vector tiles, and published packages.

## Endpoints

- `GET /sync/events` — incremental master events since `?after_seq=`
- `GET /sync/bootstrap?incident_id=` — incident bundle (AOI, plans, hazards, attachments)
- `GET /tiles/{path}` — proxied vector tiles from Martin
- `GET /packages/{path}` — published package retrieval

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

| Variable        | Description                  |
|-----------------|------------------------------|
| `DATABASE_URL`  | PostgreSQL connection string |
| `PACKAGES_DIR`  | Path to published packages   |
