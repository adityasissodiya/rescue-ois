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

- [ ] Tests pass locally (`pytest` for affected Python services, `./gradlew test` for tablet)
- [ ] `ruff check` clean for affected services
- [ ] Documentation updated where relevant (README, ADR, runbook)
- [ ] Any new SQL migrations are forward-only and numbered
- [ ] No secrets, keys, or `.env` files committed
- [ ] CODEOWNERS reviewed if touching shared infrastructure
