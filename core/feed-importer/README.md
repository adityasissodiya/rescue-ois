# feed-importer

Pulls authoritative geospatial feeds (Lantmäteriet, SMHI, Trafikverket, Naturvårdsverket) into the Rescue OIS core `staging` schema.

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

| Variable        | Description                            |
|-----------------|----------------------------------------|
| `DATABASE_URL`  | PostgreSQL connection string           |
| `LM_API_KEY`    | Lantmäteriet API key                   |
| `SMHI_API_KEY`  | SMHI API key (if required by endpoint) |
| `TRV_API_KEY`   | Trafikverket API key                   |
