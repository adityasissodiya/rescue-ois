-- 002_master_tables.sql
-- Master data tables. SRID 3006 = SWEREF 99 TM.

CREATE TABLE master.sites (
    id          UUID PRIMARY KEY,
    name        TEXT NOT NULL,
    geom        GEOMETRY(Point, 3006) NOT NULL,
    metadata    JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX sites_geom_gix ON master.sites USING GIST (geom);

CREATE TABLE master.plans (
    id          UUID PRIMARY KEY,
    site_id     UUID NOT NULL REFERENCES master.sites(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    version     INT  NOT NULL DEFAULT 1,
    status      TEXT NOT NULL DEFAULT 'draft',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE master.hazards (
    id            UUID PRIMARY KEY,
    site_id       UUID NOT NULL REFERENCES master.sites(id) ON DELETE CASCADE,
    substance     TEXT NOT NULL,
    storage_info  JSONB NOT NULL DEFAULT '{}'::jsonb,
    geom          GEOMETRY NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX hazards_geom_gix ON master.hazards USING GIST (geom);

CREATE TABLE master.area_geometries (
    id              UUID PRIMARY KEY,
    plan_id         UUID NOT NULL REFERENCES master.plans(id) ON DELETE CASCADE,
    label           TEXT NOT NULL,
    geom            GEOMETRY(Polygon, 3006) NOT NULL,
    classification  JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX area_geometries_geom_gix ON master.area_geometries USING GIST (geom);
