-- ============================================================
-- Migration 5: AES-256 encryption for camera crowd data
-- Encrypts density, queue length, and flow rate columns
-- in metric_window so raw camera readings are never stored
-- as plain text in the database.
-- ============================================================

-- ── Step 1: Add encrypted columns to metric_window ───────────
alter table metric_window
  add column if not exists density_enc      bytea,
  add column if not exists arrivals_enc     bytea,
  add column if not exists queue_len_enc    bytea,
  add column if not exists flow_rate_enc    bytea;

-- ── Step 2: Trigger function — auto-encrypts on INSERT ───────
-- Whenever a row is inserted into metric_window with plain
-- float values, the trigger encrypts them into the _enc
-- columns and nulls out the plain columns.
create or replace function _encrypt_metric_window()
  returns trigger
  language plpgsql
  security definer
as $$
begin
  if NEW.density_ppm2 is not null then
    NEW.density_enc    := enc_float(NEW.density_ppm2);
    NEW.density_ppm2   := null;
  end if;

  if NEW.arrivals_per_min is not null then
    NEW.arrivals_enc      := enc_float(NEW.arrivals_per_min);
    NEW.arrivals_per_min  := null;
  end if;

  if NEW.queue_len_est is not null then
    NEW.queue_len_enc  := enc_float(NEW.queue_len_est::float);
    NEW.queue_len_est  := null;
  end if;

  if NEW.flow_rate is not null then
    NEW.flow_rate_enc  := enc_float(NEW.flow_rate);
    NEW.flow_rate      := null;
  end if;

  return NEW;
end;
$$;

create or replace trigger trg_encrypt_metric_window
  before insert on metric_window
  for each row execute function _encrypt_metric_window();

-- ── Step 3: Secure INSERT function (called by backend/app) ───
-- Accepts plain camera readings, database encrypts before storing.
-- Nobody outside the database ever sees the AES key.
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
    density_ppm2, arrivals_per_min, queue_len_est, flow_rate,
    ts_start, ts_end
  ) values (
    p_stadium_id, p_zone_id, p_gate_id,
    p_density_ppm2, p_arrivals_per_min, p_queue_len_est, p_flow_rate,
    now(), now() + interval '15 seconds'
  )
  returning window_id into v_id;

  return v_id;
end;
$$;

-- Allow the app and backend to call this function.
grant execute on function insert_metric_window to anon, authenticated;

-- ── Step 4: Decrypted view (service-role only) ────────────────
-- Use this view to read decrypted data in admin tools.
-- Blocked for anon/authenticated by RLS.
create or replace view metric_window_decrypted as
select
  window_id,
  ts_start,
  ts_end,
  stadium_id,
  zone_id,
  gate_id,
  dec_float(density_enc)    as density_ppm2,
  dec_float(arrivals_enc)   as arrivals_per_min,
  dec_float(queue_len_enc)  as queue_len_est,
  dec_float(flow_rate_enc)  as flow_rate
from metric_window
where density_enc is not null;

-- Revoke direct table read from non-admin roles.
revoke select on metric_window from anon, authenticated;
grant execute on function insert_metric_window to anon, authenticated;
