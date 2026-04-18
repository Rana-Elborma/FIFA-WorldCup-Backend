-- ============================================================
-- Migration 7: AES-256 encryption for prediction, alert,
--              gate_command, and audit_log tables.
-- After this migration, NO sensitive data is stored as
-- plain text anywhere in the database.
-- ============================================================

-- ── Helper: encrypt / decrypt text values ────────────────────
create or replace function enc_text(p_value text)
  returns bytea
  language sql
  security definer
  stable
as $$
  select pgp_sym_encrypt(p_value, _aes_key(), 'cipher-algo=aes256');
$$;

create or replace function dec_text(p_cipher bytea)
  returns text
  language sql
  security definer
  stable
as $$
  select pgp_sym_decrypt(p_cipher, _aes_key());
$$;

-- ── Helper: encrypt / decrypt JSONB values ───────────────────
create or replace function enc_json(p_value jsonb)
  returns bytea
  language sql
  security definer
  stable
as $$
  select pgp_sym_encrypt(p_value::text, _aes_key(), 'cipher-algo=aes256');
$$;

create or replace function dec_json(p_cipher bytea)
  returns jsonb
  language sql
  security definer
  stable
as $$
  select pgp_sym_decrypt(p_cipher, _aes_key())::jsonb;
$$;


-- ════════════════════════════════════════════════════════════
-- PREDICTION TABLE
-- ════════════════════════════════════════════════════════════

alter table prediction
  add column if not exists density_pred_enc    bytea,
  add column if not exists wait_pred_enc       bytea,
  add column if not exists congestion_enc      bytea,
  add column if not exists confidence_enc      bytea,
  add column if not exists severity_enc        bytea;

-- Drop plain columns
alter table prediction
  drop column if exists density_pred,
  drop column if exists wait_pred_min,
  drop column if exists congestion_prob,
  drop column if exists confidence,
  drop column if exists severity;

-- Secure insert RPC for prediction
create or replace function insert_prediction(
  p_stadium_id      int,
  p_zone_id         int,
  p_gate_id         int,
  p_density_pred    float,
  p_wait_pred_min   float,
  p_congestion_prob float,
  p_confidence      float,
  p_severity        text,
  p_horizon_min     int default 15
)
  returns bigint
  language plpgsql
  security definer
as $$
declare v_id bigint;
begin
  insert into prediction (
    stadium_id, zone_id, gate_id, horizon_min,
    density_pred_enc, wait_pred_enc,
    congestion_enc, confidence_enc, severity_enc
  ) values (
    p_stadium_id, p_zone_id, p_gate_id, p_horizon_min,
    enc_float(p_density_pred),
    enc_float(p_wait_pred_min),
    enc_float(p_congestion_prob),
    enc_float(p_confidence),
    enc_text(p_severity)
  )
  returning pred_id into v_id;
  return v_id;
end;
$$;

grant execute on function insert_prediction to anon, authenticated;

-- Decrypted view (service-role only)
create or replace view prediction_decrypted
  with (security_invoker = true)
as
select
  pred_id,
  ts_generated,
  horizon_min,
  stadium_id, zone_id, gate_id,
  dec_float(density_pred_enc) as density_pred,
  dec_float(wait_pred_enc)    as wait_pred_min,
  dec_float(congestion_enc)   as congestion_prob,
  dec_float(confidence_enc)   as confidence,
  dec_text(severity_enc)      as severity
from prediction
where severity_enc is not null;

revoke all on prediction           from anon, authenticated;
revoke all on prediction_decrypted from anon, authenticated;
grant select on prediction_decrypted to service_role;


-- ════════════════════════════════════════════════════════════
-- ALERT TABLE
-- ════════════════════════════════════════════════════════════

alter table alert
  add column if not exists severity_enc bytea,
  add column if not exists reason_enc   bytea;

alter table alert
  drop column if exists severity,
  drop column if exists reason;

-- Secure insert RPC for alert
create or replace function insert_alert(
  p_stadium_id int,
  p_zone_id    int,
  p_gate_id    int,
  p_severity   text,
  p_reason     text,
  p_pred_id    bigint default null
)
  returns bigint
  language plpgsql
  security definer
as $$
declare v_id bigint;
begin
  insert into alert (
    stadium_id, zone_id, gate_id,
    severity_enc, reason_enc, pred_id
  ) values (
    p_stadium_id, p_zone_id, p_gate_id,
    enc_text(p_severity),
    enc_text(p_reason),
    p_pred_id
  )
  returning alert_id into v_id;
  return v_id;
end;
$$;

grant execute on function insert_alert to anon, authenticated;

-- Decrypted view (service-role only)
create or replace view alert_decrypted
  with (security_invoker = true)
as
select
  alert_id, ts, status,
  stadium_id, zone_id, gate_id, pred_id,
  dec_text(severity_enc) as severity,
  dec_text(reason_enc)   as reason
from alert
where severity_enc is not null;

revoke all on alert           from anon, authenticated;
revoke all on alert_decrypted from anon, authenticated;
grant select on alert_decrypted to service_role;


-- ════════════════════════════════════════════════════════════
-- GATE_COMMAND TABLE
-- ════════════════════════════════════════════════════════════

alter table gate_command
  add column if not exists command_type_enc bytea,
  add column if not exists parameters_enc   bytea;

alter table gate_command
  drop column if exists command_type,
  drop column if exists parameters;

-- Secure insert RPC for gate_command
create or replace function insert_gate_command(
  p_stadium_id   int,
  p_gate_id      int,
  p_command_type text,
  p_parameters   jsonb default null,
  p_alert_id     bigint default null
)
  returns bigint
  language plpgsql
  security definer
as $$
declare v_id bigint;
begin
  insert into gate_command (
    stadium_id, gate_id,
    command_type_enc, parameters_enc, alert_id
  ) values (
    p_stadium_id, p_gate_id,
    enc_text(p_command_type),
    case when p_parameters is not null then enc_json(p_parameters) else null end,
    p_alert_id
  )
  returning cmd_id into v_id;
  return v_id;
end;
$$;

grant execute on function insert_gate_command to anon, authenticated;

-- Decrypted view (service-role only)
create or replace view gate_command_decrypted
  with (security_invoker = true)
as
select
  cmd_id, ts, stadium_id, gate_id,
  ack_status, ack_ts, alert_id,
  dec_text(command_type_enc)           as command_type,
  case when parameters_enc is not null
       then dec_json(parameters_enc) end as parameters
from gate_command
where command_type_enc is not null;

revoke all on gate_command           from anon, authenticated;
revoke all on gate_command_decrypted from anon, authenticated;
grant select on gate_command_decrypted to service_role;


-- ════════════════════════════════════════════════════════════
-- AUDIT_LOG TABLE
-- ════════════════════════════════════════════════════════════

alter table audit_log
  add column if not exists payload_enc bytea;

alter table audit_log
  drop column if exists payload;

-- Update audit trigger to encrypt payload before storing
create or replace function _audit_log_trigger()
  returns trigger
  language plpgsql
  security definer
as $$
declare
  v_record_id text;
  v_payload   jsonb;
begin
  case TG_TABLE_NAME
    when 'prediction'    then v_record_id := coalesce(NEW.pred_id,   OLD.pred_id)::text;
    when 'alert'         then v_record_id := coalesce(NEW.alert_id,  OLD.alert_id)::text;
    when 'gate_command'  then v_record_id := coalesce(NEW.cmd_id,    OLD.cmd_id)::text;
    when 'gate'          then v_record_id := coalesce(NEW.gate_id,   OLD.gate_id)::text;
    when 'metric_window' then v_record_id := coalesce(NEW.window_id, OLD.window_id)::text;
    else                      v_record_id := null;
  end case;

  v_payload := case TG_OP
    when 'DELETE' then to_jsonb(OLD)
    else               to_jsonb(NEW)
  end;

  insert into audit_log (table_name, operation, record_id, payload_enc)
  values (TG_TABLE_NAME, TG_OP, v_record_id, enc_json(v_payload));

  return coalesce(NEW, OLD);
end;
$$;

-- Decrypted view (service-role only)
create or replace view audit_log_decrypted
  with (security_invoker = true)
as
select
  log_id, ts, user_id,
  table_name, operation, record_id,
  case when payload_enc is not null
       then dec_json(payload_enc) end as payload
from audit_log;

revoke all on audit_log           from anon, authenticated;
revoke all on audit_log_decrypted from anon, authenticated;
grant select on audit_log_decrypted to service_role;
