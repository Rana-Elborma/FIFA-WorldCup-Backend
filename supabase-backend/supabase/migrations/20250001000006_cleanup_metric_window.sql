-- ============================================================
-- Migration 6: Clean up metric_window
-- - Drop plain-text columns (always null after trigger)
-- - Restrict decrypted view to postgres/service role only
-- - Restrict gps_event_decrypted view the same way
-- ============================================================

-- ── Step 1: Drop trigger + plain columns ─────────────────────
-- The trigger referenced the plain columns; drop it first.
drop trigger if exists trg_encrypt_metric_window on metric_window;
drop function if exists _encrypt_metric_window();

alter table metric_window
  drop column if exists density_ppm2,
  drop column if exists arrivals_per_min,
  drop column if exists queue_len_est,
  drop column if exists flow_rate;

-- ── Step 1b: Recreate insert function to encrypt directly ─────
-- Now that plain columns are gone, the RPC encrypts values
-- itself before inserting — no trigger needed.
create or replace function insert_metric_window(
  p_stadium_id       int,
  p_zone_id          int,
  p_gate_id          int,
  p_density_ppm2     float,
  p_arrivals_per_min float,
  p_queue_len_est    int,
  p_flow_rate        float
)
  returns bigint
  language plpgsql
  security definer
as $$
declare
  v_id bigint;
begin
  insert into metric_window (
    stadium_id, zone_id, gate_id,
    density_enc, arrivals_enc, queue_len_enc, flow_rate_enc,
    ts_start, ts_end
  ) values (
    p_stadium_id, p_zone_id, p_gate_id,
    enc_float(p_density_ppm2),
    enc_float(p_arrivals_per_min),
    enc_float(p_queue_len_est::float),
    enc_float(p_flow_rate),
    now(), now() + interval '15 seconds'
  )
  returning window_id into v_id;

  return v_id;
end;
$$;

grant execute on function insert_metric_window to anon, authenticated;

-- ── Step 2: Rebuild decrypted view without plain columns ──────
create or replace view metric_window_decrypted
  with (security_invoker = true)
as
select
  window_id,
  ts_start,
  ts_end,
  stadium_id,
  zone_id,
  gate_id,
  dec_float(density_enc)   as density_ppm2,
  dec_float(arrivals_enc)  as arrivals_per_min,
  dec_float(queue_len_enc) as queue_len_est,
  dec_float(flow_rate_enc) as flow_rate
from metric_window
where density_enc is not null;

-- ── Step 3: Lock down both decrypted views ────────────────────
-- Only the postgres (service) role can read decrypted data.
-- The anon and authenticated roles see nothing.
revoke all on metric_window_decrypted from anon, authenticated;
revoke all on gps_event_decrypted     from anon, authenticated;

grant select on metric_window_decrypted to service_role;
grant select on gps_event_decrypted     to service_role;

-- ── Step 4: Also lock the raw encrypted table ─────────────────
-- Direct reads of the raw table are blocked for app users.
-- They must go through the insert_metric_window() RPC function.
revoke all on metric_window from anon, authenticated;
