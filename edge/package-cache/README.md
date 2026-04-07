# package-cache

Manages the local PMTiles and attachment cache on a vehicle K430. Performs atomic swaps when new packages are downloaded by `syncd`, exposes a small admin API for inspection.

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

| Variable     | Description                  |
|--------------|------------------------------|
| `CACHE_DIR`  | Local cache root directory   |
