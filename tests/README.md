# Tests of the executable seed

Run from the repository root:

```bash
make test        # or: .venv/bin/python -m pytest -c tests/pytest.ini tests
```

`tests/pytest.ini` puts `src/` and the repository root on the import path. No test
uses the network, the Docker harnesses or real keys; Ed25519 keys are fixture keys
derived from public strings (`src/mandate/auth.py`) and are for tests only.

## Files

| File | Tests | What they show |
|---|---|---|
| `test_scenarios.py` | 98 | Each directed scenario in `experiments/scenarios.py` meets its expectations; the Ed25519 mode gives a byte-identical trace to the symbolic mode; positive scenarios are not vacuous; the three fixtures of the 11 November 2026 rules are frozen (configuration and trace digests); each negative control finds its intended violation and its control twin is clean; malformed scenarios raise errors instead of producing outcomes; the file-backed store gives the same trace |
| `test_checker.py` | 10 | The independent checker (`experiments/checker.py`) on hand-written traces: a clean trace and each violation code it reports |
| `test_crypto_store.py` | 8 | Canonical encoding (golden bytes), signature binding to type and scope, real Ed25519 verification with fixture keys, distinct-signer validity, and that a restarted signer reloads its state and refuses a second vote |

## Deliberately broken variants (negative controls)

Each variant switches off one guard of `seed-v0` (`src/mandate/kernel.py`, `BROKEN`).
Each runs in a scenario `NC-*` that the checker must flag, and in a twin `NC-*-CONTROL`
that runs the same events under `seed-v0` and must be clean.

| Rule set | Guard switched off | Violations the checker must report |
|---|---|---|
| `broken-o2-start-guard` | O2: `s >= M_u + g` | `EPOCH-ORDER`, `SEPARATION` |
| `broken-o1-epoch-guard` | O1: `k = E_u` | `EPOCH-ORDER`, `SEPARATION` |
| `broken-d1-end-check` | D1: `tau <= e` | `INVALID-EVIDENCE`, `WITHDRAWAL-EXPIRY` |
| `broken-d1-replay` | D1: reject a repeated `(k, h, cid)` | `REPLAY` |
| `broken-distinct-signers` | validity counts distinct signers | `INVALID-EVIDENCE`, `WITHDRAWAL-EXPIRY` |
| `broken-commit-after-release` | persistence before release (section 6.4) | `GRANT-UNIQUENESS`, `SEPARATION` |

A passing negative control shows that the checker can see that kind of fault in that
scenario. It does not show that the checker finds every fault of the kind.

## What the tests do not cover

The scenarios are directed: each fixes one schedule. There is no randomized or
exhaustive exploration of schedules in this suite; the bounded TLA+ model
(`spec/tla/`) covers small bounds only. Wall-clock time is never measured: all times in
traces are synthetic integers.
