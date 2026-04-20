"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
/**
 * Alert routes
 * GET   /alerts           → list alerts (optional: stadium_id, zone_id, unresolved)
 * POST  /alerts           → create alert (operator+)
 * PATCH /alerts/:id       → resolve alert (operator+)
 * DELETE /alerts/:id      → delete alert (admin)
 */
const express_1 = require("express");
const supabase_1 = require("../config/supabase");
const auth_1 = require("../middleware/auth");
const rbac_1 = require("../middleware/rbac");
const router = (0, express_1.Router)();
// ── GET /alerts ───────────────────────────────────────────────────────────────
router.get('/', auth_1.requireAuth, async (req, res) => {
    const { stadium_id, zone_id, unresolved, limit = '50' } = req.query;
    let query = supabase_1.supabase
        .from('alert')
        .select(`
      alert_id, ts, severity, message, is_resolved, resolved_at,
      stadium:stadium_id ( name ),
      zone:zone_id ( name ),
      gate:gate_id ( name )
    `)
        .order('ts', { ascending: false })
        .limit(Number(limit));
    if (stadium_id)
        query = query.eq('stadium_id', stadium_id);
    if (zone_id)
        query = query.eq('zone_id', zone_id);
    if (unresolved === 'true')
        query = query.eq('is_resolved', false);
    const { data, error } = await query;
    if (error)
        return res.status(500).json({ error: error.message });
    return res.json(data);
});
// ── POST /alerts ──────────────────────────────────────────────────────────────
router.post('/', auth_1.requireAuth, (0, rbac_1.requireRole)('operator'), async (req, res) => {
    const { stadium_id, zone_id, gate_id, severity, message } = req.body;
    if (!stadium_id || !zone_id || !severity || !message) {
        return res.status(400).json({ error: 'stadium_id, zone_id, severity, message required' });
    }
    const { data, error } = await supabase_1.supabaseAdmin
        .from('alert')
        .insert({ stadium_id, zone_id, gate_id, severity, message })
        .select()
        .single();
    if (error)
        return res.status(500).json({ error: error.message });
    return res.status(201).json(data);
});
// ── PATCH /alerts/:id — resolve ───────────────────────────────────────────────
router.patch('/:id', auth_1.requireAuth, (0, rbac_1.requireRole)('operator'), async (req, res) => {
    const { data, error } = await supabase_1.supabaseAdmin
        .from('alert')
        .update({
        is_resolved: true,
        resolved_by: req.user.id,
        resolved_at: new Date().toISOString(),
    })
        .eq('alert_id', req.params.id)
        .select()
        .single();
    if (error)
        return res.status(500).json({ error: error.message });
    return res.json(data);
});
// ── DELETE /alerts/:id ────────────────────────────────────────────────────────
router.delete('/:id', auth_1.requireAuth, (0, rbac_1.requireRole)('admin'), async (req, res) => {
    const { error } = await supabase_1.supabaseAdmin
        .from('alert')
        .delete()
        .eq('alert_id', req.params.id);
    if (error)
        return res.status(500).json({ error: error.message });
    await supabase_1.supabaseAdmin.from('audit_log').insert({
        user_id: req.user.id,
        table_name: 'alert',
        operation: 'DELETE',
        record_id: req.params.id,
        payload: {},
    });
    return res.status(204).send();
});
exports.default = router;
//# sourceMappingURL=alerts.js.map