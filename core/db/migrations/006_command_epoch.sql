-- 006_command_epoch.sql
-- Core-issued command-authority epochs for multi-edge fenced promotion.
--
-- Until now the command epoch was per-edge-local: each edge's own
-- incident.command_epoch table (edge migration 005) was the sole source of
-- truth, so two edges could each believe they held a valid epoch and neither
-- could learn otherwise. Issuing the epoch at the regional core makes the
-- INSERT below the single serialization point for promotion: two concurrent
-- promotion attempts for the same incident produce two distinct epoch_id
-- values, and only the edge that received the higher one may commit.
--
-- Scoping note: epochs are per-incident here, whereas the edge table is
-- global (one counter per edge, no incident_id). One core serves many
-- concurrent incidents, so a global counter would be semantically wrong at
-- this tier. The edge-local table becomes a cache/fallback for when core is
-- unreachable at startup; see edge/syncd/src/accept.py.
--
-- Authority transfer remains operator-initiated (ADR-0004). This table records
-- which tenure is current; it does not decide who should hold it.

CREATE TABLE IF NOT EXISTS master.command_epoch (
    incident_id UUID        NOT NULL REFERENCES master.incidents(id) ON DELETE CASCADE,
    epoch_id    BIGINT      NOT NULL,
    started_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    started_by  TEXT        NOT NULL,
    node_id     TEXT        NOT NULL,
    PRIMARY KEY (incident_id, epoch_id)
);

COMMENT ON TABLE master.command_epoch IS
  'One row per command tenure per incident. epoch_id increases monotonically within an incident; the current epoch is max(epoch_id). The primary key enforces EpochAuthorityCoupling at the database level: an (incident_id, epoch_id) pair can be issued exactly once.';

COMMENT ON COLUMN master.command_epoch.started_by IS
  'Operator identity plus confirmation provenance recorded at promotion time.';

COMMENT ON COLUMN master.command_epoch.node_id IS
  'Edge node designated as command for this tenure (e.g. edge-resp-1).';

CREATE OR REPLACE VIEW master.current_command_epoch AS
SELECT incident_id, MAX(epoch_id) AS epoch_id
FROM master.command_epoch
GROUP BY incident_id;

COMMENT ON VIEW master.current_command_epoch IS
  'Current command epoch per incident. Read by core sync-api when issuing the next epoch and when validating forwarded journal batches; cached by edge syncd.';
