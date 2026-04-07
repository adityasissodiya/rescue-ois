# core/db/migrations

Numbered, forward-only PostgreSQL migrations for the regional core database.

Apply via:

```bash
./scripts/run-migrations.sh
```

Migrations must never be edited after merge — add a new file with the next number.
