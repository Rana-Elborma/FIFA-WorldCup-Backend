/**
 * Alert routes
 * GET   /alerts           → list alerts (optional: stadium_id, zone_id, unresolved)
 * POST  /alerts           → create alert (operator+)
 * PATCH /alerts/:id       → resolve alert (operator+)
 * DELETE /alerts/:id      → delete alert (admin)
 */
import { Router, Request, Response } from 'express';
import { supabase, supabaseAdmin } from '../config/supabase';
import { requireAuth } from '../middleware/auth';
import { requireRole } from '../middleware/rbac';

const router = Router();

// ── GET /alerts ───────────────────────────────────────────────────────────────
router.get('/', requireAuth, async (req: Request, res: Response) => {
  const { stadium_id, zone_id, unresolved, limit = '50' } = req.query as {
    stadium_id?: string;
    zone_id?: string;
    unresolved?: string;
    limit?: string;
  };

  let query = supabase
    .from('alert')
    .select(`
      alert_id, ts, severity, message, is_resolved, resolved_at,
      stadium:stadium_id ( name ),
      zone:zone_id ( name ),
      gate:gate_id ( name )
    `)
    .order('ts', { ascending: false })
    .limit(Number(limit));

  if (stadium_id) query = query.eq('stadium_id', stadium_id);
  if (zone_id)    query = query.eq('zone_id', zone_id);
  if (unresolved === 'true') query = query.eq('is_resolved', false);

  const { data, error } = await query;
  if (error) return res.status(500).json({ error: error.message });
  return res.json(data);
});

// ── POST /alerts ──────────────────────────────────────────────────────────────
router.post('/', requireAuth, requireRole('operator'), async (req: Request, res: Response) => {
  const { stadium_id, zone_id, gate_id, severity, message } = req.body as {
    stadium_id: string;
    zone_id: string;
    gate_id?: string;
    severity: 'low' | 'medium' | 'high' | 'critical';
    message: string;
  };

  if (!stadium_id || !zone_id || !severity || !message) {
    return res.status(400).json({ error: 'stadium_id, zone_id, severity, message required' });
  }

  const { data, error } = await supabaseAdmin
    .from('alert')
    .insert({ stadium_id, zone_id, gate_id, severity, message })
    .select()
    .single();

  if (error) return res.status(500).json({ error: error.message });
  return res.status(201).json(data);
});

// ── PATCH /alerts/:id — resolve ───────────────────────────────────────────────
router.patch('/:id', requireAuth, requireRole('operator'), async (req: Request, res: Response) => {
  const { data, error } = await supabaseAdmin
    .from('alert')
    .update({
      is_resolved: true,
      resolved_by: req.user!.id,
      resolved_at: new Date().toISOString(),
    })
    .eq('alert_id', req.params.id)
    .select()
    .single();

  if (error) return res.status(500).json({ error: error.message });
  return res.json(data);
});

// ── DELETE /alerts/:id ────────────────────────────────────────────────────────
router.delete('/:id', requireAuth, requireRole('admin'), async (req: Request, res: Response) => {
  const { error } = await supabaseAdmin
    .from('alert')
    .delete()
    .eq('alert_id', req.params.id);

  if (error) return res.status(500).json({ error: error.message });

  await supabaseAdmin.from('audit_log').insert({
    user_id:    req.user!.id,
    table_name: 'alert',
    operation:  'DELETE',
    record_id:  req.params.id,
    payload:    {},
  });

  return res.status(204).send();
});

export default router;
