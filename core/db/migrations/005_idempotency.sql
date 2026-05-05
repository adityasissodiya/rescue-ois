-- 005_idempotency.sql
-- Mirror the edge journal idempotency column on the core copy so backfill
-- from command vehicle is idempotent end-to-end.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

ALTER TABLE master.incident_events
    ADD COLUMN client_event_id UUID NOT NULL;

CREATE UNIQUE INDEX incident_events_client_event_id
    ON master.incident_events (client_event_id);
