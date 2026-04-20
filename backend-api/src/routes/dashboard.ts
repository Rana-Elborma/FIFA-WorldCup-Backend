/**
 * Dashboard summary route
 * GET /dashboard/summary?stadium_id=...
 *
 * Returns a single aggregated payload for the frontend:
 *   - latest metric_window per zone
 *   - latest prediction (15-min) per zone
 *   - unresolved alert count + most critical alert
 *   - gate statuses
 */
import { Router, Request, Response } from 'express';
import { supabase } from '../config/supabase';
import { requireAuth } from '../middleware/auth';

const router = Router();

router.get('/summary', requireAuth, async (req: Request, res: Response) => {
  const { stadium_id } = req.query as { stadium_id?: string };

  if (!stadium_id) {
    return res.status(400).json({ error: 'stadium_id query param required' });
  }

  // Run all queries in parallel
  const [metricsRes, predictionsRes, alertsRes, gatesRes] = await Promise.all([
    // Latest metric_window per zone
    supabase
      .from('metric_window')
      .select('window_id, ts_start, ts_end, zone_id, gate_id, density_ppm2, arrivals_per_min, queue_len_est, flow_rate')
      .eq('stadium_id', stadium_id)
      .order('ts_start', { ascending: false })
      .limit(20),

    // Latest 15-min prediction per zone
    supabase
      .from('prediction')
      .select('pred_id, ts_generated, horizon_min, zone_id, gate_id, density_pred, wait_pred_min, congestion_prob, confidence, severity')
      .eq('stadium_id', stadium_id)
      .eq('horizon_min', 15)
      .order('ts_generated', { ascending: false })
      .limit(20),

    // Unresolved alerts
    supabase
      .from('alert')
      .select('alert_id, ts, zone_id, gate_id, severity, message')
      .eq('stadium_id', stadium_id)
      .eq('is_resolved', false)
      .order('ts', { ascending: false })
      .limit(10),

    // Gate statuses
    supabase
      .from('gate')
      .select('gate_id, name, is_open, zone:zone_id(name)')
      .eq('zone.stadium_id', stadium_id),
  ]);

  if (metricsRes.error)     return res.status(500).json({ error: metricsRes.error.message });
  if (predictionsRes.error) return res.status(500).json({ error: predictionsRes.error.message });
  if (alertsRes.error)      return res.status(500).json({ error: alertsRes.error.message });
  if (gatesRes.error)       return res.status(500).json({ error: gatesRes.error.message });

  const alerts = alertsRes.data ?? [];
  const severityRank: Record<string, number> = { low: 1, medium: 2, high: 3, critical: 4 };
  const topAlert = alerts.sort((a, b) => severityRank[b.severity] - severityRank[a.severity])[0] ?? null;

  return res.json({
    stadium_id,
    metrics:     metricsRes.data ?? [],
    predictions: predictionsRes.data ?? [],
    alerts: {
      unresolved_count: alerts.length,
      top:              topAlert,
      list:             alerts,
    },
    gates: gatesRes.data ?? [],
    generated_at: new Date().toISOString(),
  });
});

export default router;
