-- ============================================================
-- Migration 3: Row-Level Security policies
-- Philosophy:
--   • Public/anon users: read-only on operational tables
--   • Authenticated: same as anon (gate assignment app)
--   • Service role: full access (bypasses RLS automatically)
--   • PII tables (gps_event, audit_log): no public access
-- ============================================================

-- ── Enable RLS on every table ─────────────────────────────────
alter table stadium       enable row level security;
alter table zone          enable row level security;
alter table gate          enable row level security;
alter table metric_window enable row level security;
alter table prediction    enable row level security;
alter table alert         enable row level security;
alter table gate_command  enable row level security;
alter table gps_event     enable row level security;
alter table audit_log     enable row level security;
alter table user_role     enable row level security;

-- ── stadium – public read ─────────────────────────────────────
create policy "stadium_public_read"
  on stadium for select using (true);

-- ── zone – public read ────────────────────────────────────────
create policy "zone_public_read"
  on zone for select using (true);

-- ── gate – public read ────────────────────────────────────────
create policy "gate_public_read"
  on gate for select using (true);

-- ── metric_window – public read ───────────────────────────────
create policy "metric_window_public_read"
  on metric_window for select using (true);

-- ── prediction – public read ──────────────────────────────────
create policy "prediction_public_read"
  on prediction for select using (true);

-- ── alert – public read (app shows alerts to users) ──────────
create policy "alert_public_read"
  on alert for select using (true);

-- ── gate_command – public read (Pi agent polls pending cmds) ─
create policy "gate_command_public_read"
  on gate_command for select using (true);

-- ── gps_event – NO public access (PII) ───────────────────────
-- All reads/writes must go through the insert_gps_event() RPC
-- or the service role.
create policy "gps_event_deny_all"
  on gps_event for all using (false);

-- ── audit_log – NO public access ─────────────────────────────
create policy "audit_log_deny_all"
  on audit_log for all using (false);

-- ── user_role – NO public access ─────────────────────────────
create policy "user_role_deny_all"
  on user_role for all using (false);
