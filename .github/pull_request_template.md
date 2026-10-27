# Pull Request

## Description

<!-- What does this PR do and why? Link related issues. -->

## Type of change

- [ ] Bug fix
- [ ] New feature
- [ ] Refactor
- [ ] Documentation
- [ ] Infrastructure / CI
- [ ] Migration (forward-only)

## How tested

<!-- Describe the tests you ran, environments, and any manual verification. -->

## Checklist

- [ ] Tests pass locally (`pytest` in each affected Python service and in `testbed/`)
- [ ] `ruff check` clean for affected services
- [ ] Testbed model or simulator changed: experiments re-run, `testbed/results/` committed, `FINDINGS.md` re-read
- [ ] Documentation updated where relevant (README, ADR, runbook; the status in `docs/README.md`)
- [ ] Any new SQL migrations are forward-only and numbered
- [ ] No secrets, keys, or `.env` files committed
