-- 004_audit_tables.sql
-- Audit event store. Receives forwarded entries from edge audit-forwarder.

CREATE TABLE audit.events (
    id           UUID PRIMARY KEY,
    timestamp    TIMESTAMPTZ NOT NULL,
    service      TEXT NOT NULL,
    action       TEXT NOT NULL,
    actor        TEXT NOT NULL,
    device_id    TEXT NULL,
    detail       JSONB NOT NULL DEFAULT '{}'::jsonb,
    source_edge  TEXT NULL
);
CREATE INDEX events_timestamp ON audit.events (timestamp DESC);
CREATE INDEX events_actor ON audit.events (actor);
CREATE INDEX events_device ON audit.events (device_id);
