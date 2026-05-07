# Rescue OIS - Hypothesis Property Tests

Implementation-level property tests that mirror the TLA+ safety
specification under `formal/tla/`. Two layers:

- Tests against `protocol_simulator.py` (in-process). Fast, deterministic,
  many schedules.
- Tests against the running Docker stack (opt-in). Slow, few schedules,
  but covers the actual implementation.

## Run

```bash
cd formal/python
pip install -e .
pytest
```

## Real-stack tests

These are skipped by default. To run:

```bash
./scripts/dev-up.sh
cd formal/python
RESCUE_OIS_REAL_STACK=1 pytest tests/test_against_real.py
```
