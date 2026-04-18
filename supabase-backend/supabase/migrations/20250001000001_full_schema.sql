-- ============================================================
-- Migration 1: Full schema matching ERD
-- ============================================================

-- ── STADIUM ──────────────────────────────────────────────────
create table if not exists stadium (
  stadium_id  serial      primary key,
  name        text        not null,
  city        text,
  capacity    int
);

-- ── USER_ROLE ─────────────────────────────────────────────────
create table if not exists user_role (
  user_id  uuid  primary key default gen_random_uuid(),
  role     text  not null check (role in ('admin','operator','viewer','pi_agent'))
);

-- ── ZONE ─────────────────────────────────────────────────────
create table if not exists zone (
  zone_id     serial  primary key,
  stadium_id  int     not null references stadium(stadium_id) on delete cascade,
  name        text    not null,
  area_m2     float   default 60
);

-- ── GATE ─────────────────────────────────────────────────────
create table if not exists gate (
  gate_id  serial  primary key,
  zone_id  int     references zone(zone_id) on delete set null,
  name     text    not null,
  is_open  bool    default true
);

-- ── GPS_EVENT (PII – coordinates stored AES-256 encrypted) ───
-- latitude_enc and longitude_enc hold pgp_sym_encrypt(value::text, key, 'cipher-algo=aes256')
-- session_hash is a SHA-256 hex digest – no plaintext stored.
create table if not exists gps_event (
  gps_event_id    bigserial   primary key,
  ts              timestamptz default now(),
  latitude_enc    bytea       not null,  -- AES-256 ciphertext
  longitude_enc   bytea       not null,  -- AES-256 ciphertext
  stadium_id      int         references stadium(stadium_id),
  zone_id         int         references zone(zone_id),
  nearest_gate_id int         references gate(gate_id),
  session_hash    text        not null   -- SHA-256(session_id), never reversible
);

-- ── METRIC_WINDOW (raw crowd data, 15-second windows) ────────
create table if not exists metric_window (
  window_id        bigserial   primary key,
  ts_start         timestamptz default now(),
  ts_end           timestamptz,
  stadium_id       int         references stadium(stadium_id),
  zone_id          int         references zone(zone_id),
  gate_id          int         references gate(gate_id),
  density_ppm2     float,
  arrivals_per_min float,
  queue_len_est    int,
  flow_rate        float
);

-- ── PREDICTION (AI forecast) ──────────────────────────────────
create table if not exists prediction (
  pred_id        bigserial   primary key,
  ts_generated   timestamptz default now(),
  horizon_min    int         default 15,
  stadium_id     int         references stadium(stadium_id),
  zone_id        int         references zone(zone_id),
  gate_id        int         references gate(gate_id),
  density_pred   float,
  wait_pred_min  float,
  congestion_prob float,
  confidence     float,
  severity       text        check (severity in ('LOW','MEDIUM','HIGH'))
);

-- ── ALERT ────────────────────────────────────────────────────
create table if not exists alert (
  alert_id    bigserial   primary key,
  ts          timestamptz default now(),
  stadium_id  int         references stadium(stadium_id),
  zone_id     int         references zone(zone_id),
  gate_id     int         references gate(gate_id),
  severity    text        check (severity in ('LOW','MEDIUM','HIGH')),
  reason      text,
  status      text        default 'active' check (status in ('active','acknowledged','resolved')),
  pred_id     bigint      references prediction(pred_id)
);

-- ── GATE_COMMAND ──────────────────────────────────────────────
create table if not exists gate_command (
  cmd_id        bigserial   primary key,
  ts            timestamptz default now(),
  stadium_id    int         references stadium(stadium_id),
  gate_id       int         references gate(gate_id),
  command_type  text        check (command_type in ('open','close','hold')),
  parameters    jsonb,
  ack_status    text        default 'pending' check (ack_status in ('pending','ack','failed')),
  ack_ts        timestamptz,
  alert_id      bigint      references alert(alert_id)
);

-- ── AUDIT_LOG (system operation log) ─────────────────────────
create table if not exists audit_log (
  log_id     bigserial   primary key,
  ts         timestamptz default now(),
  user_id    uuid        references user_role(user_id) on delete set null,
  table_name text        not null,
  operation  text        not null,  -- INSERT / UPDATE / DELETE
  record_id  text,                  -- stringified PK of affected row
  payload    jsonb                  -- full row snapshot (NEW or OLD)
);

-- ── Realtime publications ─────────────────────────────────────
alter publication supabase_realtime add table alert;
alter publication supabase_realtime add table gate_command;
alter publication supabase_realtime add table prediction;
