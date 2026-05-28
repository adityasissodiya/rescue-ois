-- 005_command_epoch.sql
-- Durable command-authority epoch for fenced promotion.
-- Each row in command_epoch records one operationally designated command
-- vehicle. A fenced promotion inserts a new row, monotonically incrementing
-- epoch_id. The current epoch is max(epoch_id). Incident.journal entries
-- carry the epoch at which they were committed; the syncd accept path
-- rejects /accept/event-batch requests that carry a different command_epoch
-- than the running command's cached current value (see edge/syncd/src/accept.py).

CREATE SCHEMA IF NOT EXISTS incident;

CREATE TABLE incident.command_epoch (
    epoch_id    BIGSERIAL PRIMARY KEY,
    started_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    started_by  TEXT NOT NULL,
    node_id     TEXT NOT NULL
);

COMMENT ON TABLE incident.command_epoch IS
  'One row per operationally designated command vehicle. epoch_id increases monotonically; current epoch = max(epoch_id).';

-- Seed the bootstrap epoch so a fresh deployment has a defined current epoch.
-- epoch_id is BIGSERIAL, so this first row is epoch 1 (not 0); the
-- incident.current_epoch view therefore returns 1 on a fresh deployment.
-- Operator and node identifiers for the initial row are placeholders that the
-- bootstrap procedure can override.
INSERT INTO incident.command_epoch (started_by, node_id)
VALUES ('bootstrap', 'edge-cmd');

ALTER TABLE incident.journal
    ADD COLUMN command_epoch BIGINT NOT NULL DEFAULT 0;

CREATE INDEX journal_incident_epoch_seq
    ON incident.journal (incident_id, command_epoch, event_seq);

CREATE OR REPLACE VIEW incident.current_epoch AS
SELECT MAX(epoch_id) AS epoch_id FROM incident.command_epoch;

COMMENT ON VIEW incident.current_epoch IS
  'Single-row view returning the max epoch_id. Cached by syncd on startup; reread on promotion.';
