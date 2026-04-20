/**
 * Crowd readings & metric windows
 * GET  /readings/latest          → latest metric_window per zone
 * GET  /readings/history         → metric_windows for a zone (paginated)
 * POST /readings/ingest          → ingest crowd_source ping (service-role only)
 */
import { Router, Request, Response } from 'express';
import { supabase, supabaseAdmin } from '../config/supabase';
import { requireAuth } from '../middleware/auth';
import { requireRole } from '../middleware/rbac';
import { hashSession, encryptLocation, coarsenLocation } from '../utils/anonymize';

const router = Router();

// ── GET /readings/latest ──────────────────────────────────────────────────────
// Returns the most recent metric_window for every zone in a stadium.
router.get('/latest', requireAuth, async (req: Request, res: Response) => {
  const { stadium_id } = req.query as { stadium_id?: string };

  let query = supabase
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

  if (stadium_id) query = query.eq('stadium_id', stadium_id);

  const { data, error } = await query;
  if (error) return res.status(500).json({ error: error.message });
  return res.json(data);
});

// ── GET /readings/history ─────────────────────────────────────────────────────
router.get('/history', requireAuth, async (req: Request, res: Response) => {
  const { zone_id, limit = '60', offset = '0' } = req.query as {
    zone_id?: string;
    limit?: string;
    offset?: string;
  };

  let query = supabase
    .from('metric_window')
    .select('window_id, ts_start, ts_end, density_ppm2, arrivals_per_min, queue_len_est, flow_rate')
    .order('ts_start', { ascending: false })
    .range(Number(offset), Number(offset) + Number(limit) - 1);

  if (zone_id) query = query.eq('zone_id', zone_id);

  const { data, error } = await query;
  if (error) return res.status(500).json({ error: error.message });
  return res.json(data);
});

// ── POST /readings/ingest ─────────────────────────────────────────────────────
// Called by the Python AI backend (uses SUPABASE_SERVICE_ROLE_KEY in its env).
// Accepts a raw location ping and anonymises it before storing.
router.post('/ingest', requireAuth, requireRole('admin'), async (req: Request, res: Response) => {
  const { lat, lon, session_token, stadium_id, zone_id, nearest_gate_id } = req.body as {
    lat: number;
    lon: number;
    session_token: string;
    stadium_id: string;
    zone_id: string;
    nearest_gate_id?: string;
  };

  if (!lat || !lon || !session_token || !stadium_id || !zone_id) {
    return res.status(400).json({ error: 'lat, lon, session_token, stadium_id, zone_id required' });
  }

  const coarsened     = coarsenLocation(lat, lon);
  const longitude_enc = encryptLocation(coarsened);
  const session_hash  = hashSession(session_token);

  const { data, error } = await supabaseAdmin
    .from('crowd_source')
    .insert({ longitude_enc, session_hash, stadium_id, zone_id, nearest_gate_id })
    .select('source_id, zone_id, stadium_id, recorded_at')
    .single();

  if (error) return res.status(500).json({ error: error.message });
  return res.status(201).json(data);
});

export default router;
