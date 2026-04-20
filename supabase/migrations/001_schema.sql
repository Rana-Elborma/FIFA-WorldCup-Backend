-- =============================================================================
-- 001_schema.sql  —  Crowd Management System Core Schema
-- =============================================================================
-- Tables: stadium, zone, gate, crowd_source, metric_window,
--         prediction, alert, gate_command, user_role, audit_log
-- Matches the approved ER diagram.
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ── Enums ─────────────────────────────────────────────────────────────────────

CREATE TYPE severity_level  AS ENUM ('low', 'medium', 'high', 'critical');
CREATE TYPE command_type    AS ENUM ('open', 'close', 'restrict', 'emergency_close');
CREATE TYPE user_role_enum  AS ENUM ('admin', 'operator', 'viewer');
CREATE TYPE audit_operation AS ENUM ('INSERT', 'UPDATE', 'DELETE', 'LOGIN', 'LOGOUT', 'ACCESS');

-- ── stadium ───────────────────────────────────────────────────────────────────
-- Top-level entity. All zones and gates belong to a stadium.

CREATE TABLE IF NOT EXISTS stadium (
    stadium_id  UUID  PRIMARY KEY DEFAULT uuid_generate_v4(),
    name        TEXT  NOT NULL,
    city        TEXT  NOT NULL,
    capacity    INT   NOT NULL CHECK (capacity > 0)
);

-- ── zone ──────────────────────────────────────────────────────────────────────
-- Physical areas within a stadium (North Stand, Gate Plaza, etc.).

CREATE TABLE IF NOT EXISTS zone (
    zone_id     UUID   PRIMARY KEY DEFAULT uuid_generate_v4(),
    stadium_id  UUID   NOT NULL REFERENCES stadium(stadium_id) ON DELETE CASCADE,
    name        TEXT   NOT NULL,
    area_m2     FLOAT  NOT NULL CHECK (area_m2 > 0)
);

-- ── gate ──────────────────────────────────────────────────────────────────────
-- Physical gates within a zone (entry/exit points).

CREATE TABLE IF NOT EXISTS gate (
    gate_id     UUID    PRIMARY KEY DEFAULT uuid_generate_v4(),
    zone_id     UUID    NOT NULL REFERENCES zone(zone_id) ON DELETE CASCADE,
    name        TEXT    NOT NULL,
    is_open     BOOLEAN NOT NULL DEFAULT TRUE
);

-- ── crowd_source ──────────────────────────────────────────────────────────────
-- Anonymised location pings from edge devices / mobile beacons.
-- longitude_enc: AES-256-GCM encrypted coordinate (only backend decrypts).
-- session_hash:  SHA-256 + pepper of device session — raw ID never stored.
-- nearest_gate_id: resolved at ingest time from geo-lookup.

CREATE TABLE IF NOT EXISTS crowd_source (
    source_id       UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    longitude_enc   TEXT        NOT NULL,           -- AES-256-GCM encrypted
    stadium_id      UUID        NOT NULL REFERENCES stadium(stadium_id) ON DELETE CASCADE,
    zone_id         UUID        NOT NULL REFERENCES zone(zone_id)    ON DELETE CASCADE,
    nearest_gate_id UUID                 REFERENCES gate(gate_id)    ON DELETE SET NULL,
    session_hash    TEXT        NOT NULL,           -- SHA-256+pepper; no raw device ID
    recorded_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
COMMENT ON COLUMN crowd_source.longitude_enc IS 'AES-256-GCM encrypted. Format: iv:tag:ciphertext (base64).';
COMMENT ON COLUMN crowd_source.session_hash  IS 'SHA-256+pepper of device session token. Raw ID never stored.';

-- ── metric_window ─────────────────────────────────────────────────────────────
-- Aggregated crowd metrics computed over a time window (e.g. 1-min tumbling).
-- Derived from crowd_source pings + AI inference pipeline.

CREATE TABLE IF NOT EXISTS metric_window (
    window_id        UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    ts_start         TIMESTAMPTZ NOT NULL,
    ts_end           TIMESTAMPTZ NOT NULL,
    stadium_id       UUID        NOT NULL REFERENCES stadium(stadium_id) ON DELETE CASCADE,
    zone_id          UUID        NOT NULL REFERENCES zone(zone_id)    ON DELETE CASCADE,
    gate_id          UUID                 REFERENCES gate(gate_id)    ON DELETE SET NULL,
    density_ppm2     FLOAT       NOT NULL CHECK (density_ppm2 >= 0),   -- people per m²
    arrivals_per_min FLOAT       NOT NULL CHECK (arrivals_per_min >= 0),
    queue_len_est    FLOAT                CHECK (queue_len_est >= 0),
    flow_rate        FLOAT                CHECK (flow_rate >= 0),
    CONSTRAINT valid_window CHECK (ts_end > ts_start)
);
COMMENT ON TABLE  metric_window IS 'Aggregated 1-min tumbling window metrics from AI inference.';
COMMENT ON COLUMN metric_window.density_ppm2 IS 'People per square metre within the zone/gate area.';

-- ── prediction ────────────────────────────────────────────────────────────────
-- LightGBM/LSTM forward predictions (15-min, 30-min, etc.).

CREATE TABLE IF NOT EXISTS prediction (
    pred_id          UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    ts_generated     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    horizon_min      INT         NOT NULL CHECK (horizon_min > 0),  -- e.g. 15, 30, 60
    stadium_id       UUID        NOT NULL REFERENCES stadium(stadium_id) ON DELETE CASCADE,
    zone_id          UUID        NOT NULL REFERENCES zone(zone_id)    ON DELETE CASCADE,
    gate_id          UUID                 REFERENCES gate(gate_id)    ON DELETE SET NULL,
    density_pred     FLOAT       NOT NULL CHECK (density_pred >= 0),
    wait_pred_min    FLOAT                CHECK (wait_pred_min >= 0),
    congestion_prob  FLOAT                CHECK (congestion_prob BETWEEN 0 AND 1),
    confidence       FLOAT                CHECK (confidence BETWEEN 0 AND 1),
    severity         severity_level NOT NULL
);

-- ── alert ─────────────────────────────────────────────────────────────────────
-- Operational alerts raised by automated rules or operators.

CREATE TABLE IF NOT EXISTS alert (
    alert_id     UUID           PRIMARY KEY DEFAULT uuid_generate_v4(),
    ts           TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
    stadium_id   UUID           NOT NULL REFERENCES stadium(stadium_id) ON DELETE CASCADE,
    zone_id      UUID           NOT NULL REFERENCES zone(zone_id)    ON DELETE CASCADE,
    gate_id      UUID                    REFERENCES gate(gate_id)    ON DELETE SET NULL,
    severity     severity_level NOT NULL,
    message      TEXT           NOT NULL,
    is_resolved  BOOLEAN        NOT NULL DEFAULT FALSE,
    resolved_at  TIMESTAMPTZ,
    resolved_by  UUID                    REFERENCES auth.users(id)   ON DELETE SET NULL
);

-- ── gate_command ──────────────────────────────────────────────────────────────
-- Commands issued to physical gate controllers (open/close/restrict).

CREATE TABLE IF NOT EXISTS gate_command (
    cmd_id       UUID          PRIMARY KEY DEFAULT uuid_generate_v4(),
    ts           TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    stadium_id   UUID          NOT NULL REFERENCES stadium(stadium_id) ON DELETE CASCADE,
    gate_id      UUID          NOT NULL REFERENCES gate(gate_id)    ON DELETE CASCADE,
    command_type command_type  NOT NULL,
    issued_by    UUID                   REFERENCES auth.users(id)   ON DELETE SET NULL
);

-- ── user_role ─────────────────────────────────────────────────────────────────
-- Maps auth.users to application roles.
-- Created automatically on signup by trigger in 003_triggers.sql.

CREATE TABLE IF NOT EXISTS user_role (
    user_id  UUID           PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    role     user_role_enum NOT NULL DEFAULT 'viewer'
);

-- ── audit_log ─────────────────────────────────────────────────────────────────
-- Immutable security audit trail. Append-only (enforced in 003_triggers.sql).
-- ip_hash: SHA-256+pepper of client IP — raw IP never stored.

CREATE TABLE IF NOT EXISTS audit_log (
    log_id      UUID          PRIMARY KEY DEFAULT uuid_generate_v4(),
    ts          TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    user_id     UUID                   REFERENCES auth.users(id) ON DELETE SET NULL,
    table_name  TEXT          NOT NULL,
    operation   audit_operation NOT NULL,
    record_id   TEXT,
    payload     JSONB
);
COMMENT ON TABLE audit_log IS 'Append-only audit trail. UPDATE and DELETE blocked by triggers.';
COMMENT ON COLUMN audit_log.payload IS 'Sanitised diff or action metadata. No raw PII.';

-- =============================================================================
-- INDEXES
-- =============================================================================

-- zone / gate lookups
CREATE INDEX IF NOT EXISTS idx_zone_stadium          ON zone(stadium_id);
CREATE INDEX IF NOT EXISTS idx_gate_zone             ON gate(zone_id);

-- crowd_source: time + location queries
CREATE INDEX IF NOT EXISTS idx_crowd_stadium_time    ON crowd_source(stadium_id, recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_crowd_zone_time       ON crowd_source(zone_id, recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_crowd_gate            ON crowd_source(nearest_gate_id);

-- metric_window: time-series queries
CREATE INDEX IF NOT EXISTS idx_mw_zone_time          ON metric_window(zone_id, ts_start DESC);
CREATE INDEX IF NOT EXISTS idx_mw_gate_time          ON metric_window(gate_id, ts_start DESC);
CREATE INDEX IF NOT EXISTS idx_mw_stadium_time       ON metric_window(stadium_id, ts_start DESC);

-- prediction: horizon + recency
CREATE INDEX IF NOT EXISTS idx_pred_zone_horizon     ON prediction(zone_id, horizon_min, ts_generated DESC);
CREATE INDEX IF NOT EXISTS idx_pred_gate_horizon     ON prediction(gate_id, horizon_min, ts_generated DESC);
CREATE INDEX IF NOT EXISTS idx_pred_severity         ON prediction(severity);

-- alert: unresolved first
CREATE INDEX IF NOT EXISTS idx_alert_zone_unresolved ON alert(zone_id, is_resolved) WHERE is_resolved = FALSE;
CREATE INDEX IF NOT EXISTS idx_alert_stadium_ts      ON alert(stadium_id, ts DESC);
CREATE INDEX IF NOT EXISTS idx_alert_severity        ON alert(severity);

-- gate_command: gate history
CREATE INDEX IF NOT EXISTS idx_cmd_gate_ts           ON gate_command(gate_id, ts DESC);
CREATE INDEX IF NOT EXISTS idx_cmd_stadium_ts        ON gate_command(stadium_id, ts DESC);

-- audit_log: actor + table queries
CREATE INDEX IF NOT EXISTS idx_audit_user_ts         ON audit_log(user_id, ts DESC);
CREATE INDEX IF NOT EXISTS idx_audit_table_ts        ON audit_log(table_name, ts DESC);
CREATE INDEX IF NOT EXISTS idx_audit_ts              ON audit_log(ts DESC);
