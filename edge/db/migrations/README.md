# edge/db/migrations

Numbered, forward-only PostgreSQL migrations for the vehicle K430 edge database.

The `incident.*` tables are only populated on a **command-role** K430. Responders apply the same migration but never write to them.

Apply via:

```bash
DATABASE_URL=postgresql://... ./scripts/run-migrations.sh edge
```
