"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
/**
 * Stadium + Zone + Gate routes
 * GET  /stadiums              → list all stadiums
 * GET  /stadiums/:id/zones    → zones in a stadium
 * GET  /stadiums/:id/gates    → all gates in a stadium (via zones)
 * POST /stadiums              → create stadium (admin)
 * PATCH /gates/:id            → open/close gate — issues gate_command (operator+)
 */
const express_1 = require("express");
const supabase_1 = require("../config/supabase");
const auth_1 = require("../middleware/auth");
const rbac_1 = require("../middleware/rbac");
const router = (0, express_1.Router)();
// ── GET /stadiums ─────────────────────────────────────────────────────────────
router.get('/', auth_1.requireAuth, async (_req, res) => {
    const { data, error } = await supabase_1.supabase.from('stadium').select('*');
    if (error)
        return res.status(500).json({ error: error.message });
    return res.json(data);
});
// ── GET /stadiums/:id/zones ───────────────────────────────────────────────────
router.get('/:id/zones', auth_1.requireAuth, async (req, res) => {
    const { data, error } = await supabase_1.supabase
        .from('zone')
        .select('*')
        .eq('stadium_id', req.params.id);
    if (error)
        return res.status(500).json({ error: error.message });
    return res.json(data);
});
// ── GET /stadiums/:id/gates ───────────────────────────────────────────────────
router.get('/:id/gates', auth_1.requireAuth, (0, rbac_1.requireRole)('operator'), async (req, res) => {
    const { data, error } = await supabase_1.supabase
        .from('gate')
        .select('*, zone!inner(stadium_id)')
        .eq('zone.stadium_id', req.params.id);
    if (error)
        return res.status(500).json({ error: error.message });
    return res.json(data);
});
// ── POST /stadiums ────────────────────────────────────────────────────────────
router.post('/', auth_1.requireAuth, (0, rbac_1.requireRole)('admin'), async (req, res) => {
    const { name, city, capacity } = req.body;
    if (!name || !city || !capacity) {
        return res.status(400).json({ error: 'name, city, capacity are required' });
    }
    const { data, error } = await supabase_1.supabaseAdmin
        .from('stadium')
        .insert({ name, city, capacity })
        .select()
        .single();
    if (error)
        return res.status(500).json({ error: error.message });
    await supabase_1.supabaseAdmin.from('audit_log').insert({
        user_id: req.user.id,
        table_name: 'stadium',
        operation: 'INSERT',
        record_id: data.stadium_id,
        payload: { name, city, capacity },
    });
    return res.status(201).json(data);
});
// ── PATCH /gates/:id ──────────────────────────────────────────────────────────
// Issues a gate_command; trigger in DB syncs gate.is_open automatically.
router.patch('/gates/:id', auth_1.requireAuth, (0, rbac_1.requireRole)('operator'), async (req, res) => {
    const { command_type, stadium_id } = req.body;
    if (!command_type || !stadium_id) {
        return res.status(400).json({ error: 'command_type and stadium_id are required' });
    }
    const { data, error } = await supabase_1.supabaseAdmin
        .from('gate_command')
        .insert({
        gate_id: req.params.id,
        stadium_id,
        command_type,
        issued_by: req.user.id,
    })
        .select()
        .single();
    if (error)
        return res.status(500).json({ error: error.message });
    return res.status(201).json(data);
});
exports.default = router;
//# sourceMappingURL=stadium.js.map