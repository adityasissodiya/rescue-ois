-- 003_incident_journal.sql
-- Incident journal & state. Only populated on command-role K430.
-- Responder K430s leave these tables empty; they queue events in outbox.device_outbox
-- and forward to the command vehicle.

CREATE TABLE incident.journal (
    id            UUID PRIMARY KEY,
    incident_id   UUID NOT NULL,
    event_seq     BIGINT NOT NULL,
    event_type    TEXT NOT NULL,
    payload       JSONB NOT NULL DEFAULT '{}'::jsonb,
    device_id     TEXT NOT NULL,
    user_id       TEXT NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (incident_id, event_seq)
);
CREATE INDEX journal_incident_seq ON incident.journal (incident_id, event_seq);

CREATE TABLE incident.state (
    incident_id   UUID PRIMARY KEY,
    last_event_seq BIGINT NOT NULL DEFAULT 0,
    state         JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMENT ON TABLE incident.journal IS 'Only populated on command-role K430.';
COMMENT ON TABLE incident.state   IS 'Only populated on command-role K430.';
