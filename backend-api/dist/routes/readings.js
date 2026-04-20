"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
/**
 * Crowd readings & metric windows
 * GET  /readings/latest          → latest metric_window per zone
 * GET  /readings/history         → metric_windows for a zone (paginated)
 * POST /readings/ingest          → ingest crowd_source ping (service-role only)
 */
const express_1 = require("express");
const supabase_1 = require("../config/supabase");
const auth_1 = require("../middleware/auth");
const rbac_1 = require("../middleware/rbac");
const anonymize_1 = require("../utils/anonymize");
const router = (0, express_1.Router)();
// ── GET /readings/latest ──────────────────────────────────────────────────────
// Returns the most recent metric_window for every zone in a stadium.
router.get('/latest', auth_1.requireAuth, async (req, res) => {
    const { stadium_id } = req.query;
    let query = supabase_1.supabase
        .from('metric_window')
        .select(`
      window_id, ts_start, ts_end,
      density_ppm2, arrivals_per_min, queue_len_est, flow_rate,
      stadium_id,
      zone:zone_id ( zone_id, name, area_m2 ),
      gate:gate_id ( gate_id, name, is_open )
    `)
        .order('ts_start', { ascending: false })
        .limit(1);
    if (stadium_id)
        query = query.eq('stadium_id', stadium_id);
    const { data, error } = await query;
    if (error)
        return res.status(500).json({ error: error.message });
    return res.json(data);
});
// ── GET /readings/history ─────────────────────────────────────────────────────
router.get('/history', auth_1.requireAuth, async (req, res) => {
    const { zone_id, limit = '60', offset = '0' } = req.query;
    let query = supabase_1.supabase
        .from('metric_window')
        .select('window_id, ts_start, ts_end, density_ppm2, arrivals_per_min, queue_len_est, flow_rate')
        .order('ts_start', { ascending: false })
        .range(Number(offset), Number(offset) + Number(limit) - 1);
    if (zone_id)
        query = query.eq('zone_id', zone_id);
    const { data, error } = await query;
    if (error)
        return res.status(500).json({ error: error.message });
    return res.json(data);
});
// ── POST /readings/ingest ─────────────────────────────────────────────────────
// Called by the Python AI backend (uses SUPABASE_SERVICE_ROLE_KEY in its env).
// Accepts a raw location ping and anonymises it before storing.
router.post('/ingest', auth_1.requireAuth, (0, rbac_1.requireRole)('admin'), async (req, res) => {
    const { lat, lon, session_token, stadium_id, zone_id, nearest_gate_id } = req.body;
    if (!lat || !lon || !session_token || !stadium_id || !zone_id) {
        return res.status(400).json({ error: 'lat, lon, session_token, stadium_id, zone_id required' });
    }
    const coarsened = (0, anonymize_1.coarsenLocation)(lat, lon);
    const longitude_enc = (0, anonymize_1.encryptLocation)(coarsened);
    const session_hash = (0, anonymize_1.hashSession)(session_token);
    const { data, error } = await supabase_1.supabaseAdmin
        .from('crowd_source')
        .insert({ longitude_enc, session_hash, stadium_id, zone_id, nearest_gate_id })
        .select('source_id, zone_id, stadium_id, recorded_at')
        .single();
    if (error)
        return res.status(500).json({ error: error.message });
    return res.status(201).json(data);
});
exports.default = router;
//# sourceMappingURL=readings.js.map