-- =============================================================================
-- 003_triggers.sql  —  Database Triggers
-- =============================================================================
-- 1. on_auth_user_created        → auto-insert row in user_role on signup
-- 2. log_alert_created           → audit log on new alert
-- 3. log_alert_resolved          → audit log when alert is resolved
-- 4. log_gate_command            → audit log on every gate_command insert
-- 5. prevent_audit_log_mutate    → block UPDATE/DELETE on audit_log (append-only)
-- 6. gate_is_open_sync           → sync gate.is_open from gate_command
-- =============================================================================

-- ── 1. Auto-insert user_role on Supabase Auth signup ─────────────────────────

CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
BEGIN
    INSERT INTO public.user_role (user_id, role)
    VALUES (NEW.id, 'viewer')
    ON CONFLICT (user_id) DO NOTHING;  -- idempotent; safe on email confirmation re-run
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION handle_new_user();


-- ── 2. Audit log: new alert created ──────────────────────────────────────────

CREATE OR REPLACE FUNCTION log_alert_created()
RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
BEGIN
    INSERT INTO public.audit_log (user_id, table_name, operation, record_id, payload)
    VALUES (
        auth.uid(),
        'alert',
        'INSERT',
        NEW.alert_id::TEXT,
        jsonb_build_object(
            'stadium_id', NEW.stadium_id,
            'zone_id',    NEW.zone_id,
            'gate_id',    NEW.gate_id,
            'severity',   NEW.severity,
            'message',    LEFT(NEW.message, 200)
        )
    );
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_log_alert_created ON alert;
CREATE TRIGGER trg_log_alert_created
    AFTER INSERT ON alert
    FOR EACH ROW EXECUTE FUNCTION log_alert_created();


-- ── 3. Audit log: alert resolved + auto-set resolved_at ──────────────────────

CREATE OR REPLACE FUNCTION log_alert_resolved()
RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
BEGIN
    IF OLD.is_resolved = FALSE AND NEW.is_resolved = TRUE THEN
        -- Auto-stamp resolved_at if not set by caller
        IF NEW.resolved_at IS NULL THEN
            NEW.resolved_at := NOW();
        END IF;

        INSERT INTO public.audit_log (user_id, table_name, operation, record_id, payload)
        VALUES (
            auth.uid(),
            'alert',
            'UPDATE',
            NEW.alert_id::TEXT,
            jsonb_build_object(
                'action',      'RESOLVED',
                'zone_id',     NEW.zone_id,
                'severity',    NEW.severity,
                'resolved_by', NEW.resolved_by,
                'resolved_at', NEW.resolved_at
            )
        );
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_log_alert_resolved ON alert;
CREATE TRIGGER trg_log_alert_resolved
    BEFORE UPDATE ON alert
    FOR EACH ROW EXECUTE FUNCTION log_alert_resolved();


-- ── 4. Audit log: gate_command issued ────────────────────────────────────────

CREATE OR REPLACE FUNCTION log_gate_command()
RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
BEGIN
    INSERT INTO public.audit_log (user_id, table_name, operation, record_id, payload)
    VALUES (
        auth.uid(),
        'gate_command',
        'INSERT',
        NEW.cmd_id::TEXT,
        jsonb_build_object(
            'stadium_id',    NEW.stadium_id,
            'gate_id',       NEW.gate_id,
            'command_type',  NEW.command_type,
            'issued_by',     NEW.issued_by
        )
    );
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_log_gate_command ON gate_command;
CREATE TRIGGER trg_log_gate_command
    AFTER INSERT ON gate_command
    FOR EACH ROW EXECUTE FUNCTION log_gate_command();


-- ── 5. Prevent mutation of audit_log (append-only) ───────────────────────────

CREATE OR REPLACE FUNCTION prevent_audit_log_mutate()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'audit_log is append-only: UPDATE and DELETE are not permitted.';
END;
$$;

DROP TRIGGER IF EXISTS trg_audit_no_update ON audit_log;
CREATE TRIGGER trg_audit_no_update
    BEFORE UPDATE ON audit_log
    FOR EACH ROW EXECUTE FUNCTION prevent_audit_log_mutate();

DROP TRIGGER IF EXISTS trg_audit_no_delete ON audit_log;
CREATE TRIGGER trg_audit_no_delete
    BEFORE DELETE ON audit_log
    FOR EACH ROW EXECUTE FUNCTION prevent_audit_log_mutate();


-- ── 6. Sync gate.is_open from gate_command ───────────────────────────────────
-- When a gate_command is issued, automatically update gate.is_open.

CREATE OR REPLACE FUNCTION sync_gate_state()
RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER SET search_path = public AS $$
BEGIN
    UPDATE public.gate
    SET is_open = CASE NEW.command_type
                    WHEN 'open'            THEN TRUE
                    WHEN 'close'           THEN FALSE
                    WHEN 'emergency_close' THEN FALSE
                    WHEN 'restrict'        THEN TRUE  -- still open, but restricted flow
                    ELSE is_open
                  END
    WHERE gate_id = NEW.gate_id;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_sync_gate_state ON gate_command;
CREATE TRIGGER trg_sync_gate_state
    AFTER INSERT ON gate_command
    FOR EACH ROW EXECUTE FUNCTION sync_gate_state();
