-- 001_edge_schema.sql
-- Edge K430 database schemas. Cache holds replicated master subset, incident
-- holds the live journal (command role only), outbox holds field edits queued
-- for forwarding.

CREATE EXTENSION IF NOT EXISTS postgis;

CREATE SCHEMA IF NOT EXISTS cache;
CREATE SCHEMA IF NOT EXISTS incident;
CREATE SCHEMA IF NOT EXISTS outbox;
