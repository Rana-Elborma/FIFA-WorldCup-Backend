-- =============================================================================
-- 002_rls.sql  —  Row Level Security Policies
-- =============================================================================
-- Principle: least-privilege. Every table locked down by default.
-- service_role (Python/Node backend) bypasses RLS by design.
-- Helper: current_user_role() reads user_role table for the calling user.
-- =============================================================================

-- ── Helper function ───────────────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION current_user_role()
RETURNS user_role_enum LANGUAGE sql SECURITY DEFINER STABLE AS $$
    SELECT role FROM user_role WHERE user_id = auth.uid();
$$;

CREATE OR REPLACE FUNCTION has_role(required user_role_enum)
RETURNS BOOLEAN LANGUAGE sql SECURITY DEFINER STABLE AS $$
    SELECT COALESCE(
        (SELECT role = required FROM user_role WHERE user_id = auth.uid()),
        FALSE
    );
$$;

CREATE OR REPLACE FUNCTION has_min_role(min_role TEXT)
RETURNS BOOLEAN LANGUAGE sql SECURITY DEFINER STABLE AS $$
    SELECT EXISTS (
        SELECT 1 FROM user_role
        WHERE user_id = auth.uid()
          AND CASE min_role
                WHEN 'viewer'   THEN role IN ('viewer','operator','admin')
                WHEN 'operator' THEN role IN ('operator','admin')
                WHEN 'admin'    THEN role = 'admin'
                ELSE FALSE
              END
    );
$$;

-- ── Enable RLS ────────────────────────────────────────────────────────────────

ALTER TABLE stadium       ENABLE ROW LEVEL SECURITY;
ALTER TABLE zone          ENABLE ROW LEVEL SECURITY;
ALTER TABLE gate          ENABLE ROW LEVEL SECURITY;
ALTER TABLE crowd_source  ENABLE ROW LEVEL SECURITY;
ALTER TABLE metric_window ENABLE ROW LEVEL SECURITY;
ALTER TABLE prediction    ENABLE ROW LEVEL SECURITY;
ALTER TABLE alert         ENABLE ROW LEVEL SECURITY;
ALTER TABLE gate_command  ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_role     ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_log     ENABLE ROW LEVEL SECURITY;

-- =============================================================================
-- stadium — all authenticated users can read; only admins write
-- =============================================================================

CREATE POLICY "stadium: authenticated read"
ON stadium FOR SELECT USING (auth.role() = 'authenticated');

CREATE POLICY "stadium: admin insert"
ON stadium FOR INSERT WITH CHECK (has_min_role('admin'));

CREATE POLICY "stadium: admin update"
ON stadium FOR UPDATE USING (has_min_role('admin'));

CREATE POLICY "stadium: admin delete"
ON stadium FOR DELETE USING (has_min_role('admin'));

-- =============================================================================
-- zone — all authenticated users can read; only admins write
-- =============================================================================

CREATE POLICY "zone: authenticated read"
ON zone FOR SELECT USING (auth.role() = 'authenticated');

CREATE POLICY "zone: admin insert"
ON zone FOR INSERT WITH CHECK (has_min_role('admin'));

CREATE POLICY "zone: admin update"
ON zone FOR UPDATE USING (has_min_role('admin'));

CREATE POLICY "zone: admin delete"
ON zone FOR DELETE USING (has_min_role('admin'));

-- =============================================================================
-- gate — operators+ read; admins write
-- =============================================================================

CREATE POLICY "gate: operator read"
ON gate FOR SELECT USING (has_min_role('operator'));

CREATE POLICY "gate: admin insert"
ON gate FOR INSERT WITH CHECK (has_min_role('admin'));

CREATE POLICY "gate: admin update"
ON gate FOR UPDATE USING (has_min_role('admin'));

CREATE POLICY "gate: admin delete"
ON gate FOR DELETE USING (has_min_role('admin'));

-- =============================================================================
-- crowd_source — INSERT only by service_role; SELECT by operators+
-- =============================================================================

-- Only operators and admins can read raw crowd source data
CREATE POLICY "crowd_source: operator read"
ON crowd_source FOR SELECT USING (has_min_role('operator'));

-- No authenticated user can INSERT — service_role only (bypasses RLS)

-- =============================================================================
-- metric_window — all authenticated users can read; service_role writes
-- =============================================================================

CREATE POLICY "metric_window: authenticated read"
ON metric_window FOR SELECT USING (auth.role() = 'authenticated');

-- INSERT/UPDATE done exclusively by service_role (AI pipeline)

-- =============================================================================
-- prediction — all authenticated users can read; service_role writes
-- =============================================================================

CREATE POLICY "prediction: authenticated read"
ON prediction FOR SELECT USING (auth.role() = 'authenticated');

-- INSERT done exclusively by service_role (model microservice)

-- =============================================================================
-- alert — authenticated read; operators+ insert/update; admin delete
-- =============================================================================

CREATE POLICY "alert: authenticated read"
ON alert FOR SELECT USING (auth.role() = 'authenticated');

CREATE POLICY "alert: operator insert"
ON alert FOR INSERT WITH CHECK (has_min_role('operator'));

CREATE POLICY "alert: operator update"
ON alert FOR UPDATE USING (has_min_role('operator'));

CREATE POLICY "alert: admin delete"
ON alert FOR DELETE USING (has_min_role('admin'));

-- =============================================================================
-- gate_command — operators+ can read and insert; admin can delete
-- =============================================================================

CREATE POLICY "gate_command: operator read"
ON gate_command FOR SELECT USING (has_min_role('operator'));

CREATE POLICY "gate_command: operator insert"
ON gate_command FOR INSERT WITH CHECK (has_min_role('operator'));

-- gate_commands are immutable once issued — no UPDATE policy
-- Only admins can purge (rare)
CREATE POLICY "gate_command: admin delete"
ON gate_command FOR DELETE USING (has_min_role('admin'));

-- =============================================================================
-- user_role — users see their own role; admins see and manage all
-- =============================================================================

CREATE POLICY "user_role: own read"
ON user_role FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "user_role: admin read all"
ON user_role FOR SELECT USING (has_min_role('admin'));

-- Only admins can assign/change roles
CREATE POLICY "user_role: admin insert"
ON user_role FOR INSERT WITH CHECK (has_min_role('admin'));

CREATE POLICY "user_role: admin update"
ON user_role FOR UPDATE USING (has_min_role('admin'));

CREATE POLICY "user_role: admin delete"
ON user_role FOR DELETE USING (has_min_role('admin'));

-- =============================================================================
-- audit_log — READ only by admins; all WRITES by service_role only
-- =============================================================================

CREATE POLICY "audit_log: admin read"
ON audit_log FOR SELECT USING (has_min_role('admin'));

-- No INSERT/UPDATE/DELETE for authenticated users.
-- service_role bypasses RLS and handles all audit_log writes.
