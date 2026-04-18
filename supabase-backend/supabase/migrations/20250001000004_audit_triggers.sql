-- ============================================================
-- Migration 4: Audit log triggers
-- Every INSERT / UPDATE / DELETE on sensitive tables writes a
-- record to audit_log automatically.
-- ============================================================

create or replace function _audit_log_trigger()
  returns trigger
  language plpgsql
  security definer
as $$
declare
  v_record_id text;
  v_payload   jsonb;
begin
  -- Capture the PK as text for any table
  case TG_TABLE_NAME
    when 'prediction'    then v_record_id := coalesce(NEW.pred_id,  OLD.pred_id)::text;
    when 'alert'         then v_record_id := coalesce(NEW.alert_id, OLD.alert_id)::text;
    when 'gate_command'  then v_record_id := coalesce(NEW.cmd_id,   OLD.cmd_id)::text;
    when 'gate'          then v_record_id := coalesce(NEW.gate_id,  OLD.gate_id)::text;
    when 'metric_window' then v_record_id := coalesce(NEW.window_id,OLD.window_id)::text;
    else                      v_record_id := null;
  end case;

  -- Full row snapshot (NEW after write, OLD before delete)
  v_payload := case TG_OP
    when 'DELETE' then to_jsonb(OLD)
    else               to_jsonb(NEW)
  end;

  insert into audit_log (table_name, operation, record_id, payload)
  values (TG_TABLE_NAME, TG_OP, v_record_id, v_payload);

  return coalesce(NEW, OLD);
end;
$$;

-- ── Attach to tables that need auditing ──────────────────────
create trigger _audit_prediction
  after insert or update or delete on prediction
  for each row execute function _audit_log_trigger();

create trigger _audit_alert
  after insert or update or delete on alert
  for each row execute function _audit_log_trigger();

create trigger _audit_gate_command
  after insert or update or delete on gate_command
  for each row execute function _audit_log_trigger();

create trigger _audit_gate
  after insert or update or delete on gate
  for each row execute function _audit_log_trigger();

create trigger _audit_metric_window
  after insert on metric_window
  for each row execute function _audit_log_trigger();
