-- 004_idempotency_and_sync_state.sql
-- Add client_event_id for end-to-end idempotency on outbox AND journal,
-- add incident_id to outbox so events can be routed to the correct journal,
-- and add a key-value sync_state table for last_acked_seq_to_core tracking.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

ALTER TABLE outbox.device_outbox
    ADD COLUMN incident_id     UUID NOT NULL,
    ADD COLUMN client_event_id UUID NOT NULL;

CREATE UNIQUE INDEX device_outbox_client_event_id
    ON outbox.device_outbox (client_event_id);

CREATE INDEX device_outbox_incident
    ON outbox.device_outbox (incident_id);

ALTER TABLE incident.journal
    ADD COLUMN client_event_id UUID NOT NULL;

CREATE UNIQUE INDEX journal_client_event_id
    ON incident.journal (client_event_id);

CREATE SCHEMA IF NOT EXISTS sync;

CREATE TABLE sync.state (
    key           TEXT PRIMARY KEY,
    value         JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE sync.state IS
  'Generic kv for syncd bookkeeping. Keys used so far: last_acked_seq_to_core.';
