-- 002_outbox.sql
-- Device outbox: every field edit submitted by a tablet lands here first.
-- syncd.push forwards entries to the command vehicle and stamps forwarded_at.

CREATE TABLE outbox.device_outbox (
    id            UUID PRIMARY KEY,
    device_id     TEXT NOT NULL,
    user_id       TEXT NOT NULL,
    event_type    TEXT NOT NULL,
    payload       JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    forwarded_at  TIMESTAMPTZ NULL,
    ack_seq       BIGINT NULL
);
CREATE INDEX device_outbox_unforwarded
    ON outbox.device_outbox (created_at)
    WHERE forwarded_at IS NULL;
