-- 003_incident_tables.sql
-- Incident tables (regional core copy, populated by forwarding from command vehicle).

CREATE TABLE master.incidents (
    id          UUID PRIMARY KEY,
    name        TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'open',
    aoi         GEOMETRY(Polygon, 3006) NOT NULL,
    opened_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    closed_at   TIMESTAMPTZ NULL
);
CREATE INDEX incidents_aoi_gix ON master.incidents USING GIST (aoi);

CREATE TABLE master.incident_events (
    id            UUID PRIMARY KEY,
    incident_id   UUID NOT NULL REFERENCES master.incidents(id) ON DELETE CASCADE,
    event_seq     BIGINT NOT NULL,
    event_type    TEXT NOT NULL,
    payload       JSONB NOT NULL DEFAULT '{}'::jsonb,
    device_id     TEXT NOT NULL,
    user_id       TEXT NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (incident_id, event_seq)
);
CREATE INDEX incident_events_incident_seq ON master.incident_events (incident_id, event_seq);
