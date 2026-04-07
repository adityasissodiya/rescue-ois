# publisher

Runs the staging → master → build → publish pipeline. Produces PMTiles, attachment tarballs, and a signed `manifest.json` consumed by edge `syncd` for baseline sync.

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

| Variable          | Description                                |
|-------------------|--------------------------------------------|
| `DATABASE_URL`    | PostgreSQL connection string               |
| `PUBLISH_DIR`     | Output directory for built packages        |
| `SIGNING_KEY_PATH`| Path to signing key for manifest signature |
