/**
 * Auth routes — Supabase Auth integration.
 * POST /auth/register → create user in Supabase Auth + user_role
 * POST /auth/login    → sign in, return JWT + name (frontend needs "name")
 * POST /auth/logout   → invalidate session
 * GET  /auth/me       → return current user + role
 */
import { Router, Request, Response } from 'express';
import { supabase, supabaseAdmin } from '../config/supabase';
import { requireAuth } from '../middleware/auth';

const router = Router();

// ── POST /auth/register ───────────────────────────────────────────────────────
router.post('/register', async (req: Request, res: Response) => {
  const { email, password, name, role: requestedRole } = req.body as {
    email?: string;
    password?: string;
    name?: string;
    role?: string;
  };

  if (!email || !password) {
    return res.status(400).json({ message: 'email and password are required' });
  }

  // Create user in Supabase Auth (admin bypasses email confirmation)
  const { data, error } = await supabaseAdmin.auth.admin.createUser({
    email,
    password,
    user_metadata: { display_name: name ?? email.split('@')[0] },
    email_confirm: true,
  });

  if (error || !data.user) {
    return res.status(400).json({ message: error?.message ?? 'Registration failed' });
  }

  // The on_auth_user_created trigger inserts into user_role automatically.
  // As a safety fallback, upsert in case the trigger was delayed.
  await supabaseAdmin
    .from('user_role')
    .upsert({ user_id: data.user.id, role: 'viewer' }, { onConflict: 'user_id' });

  return res.status(201).json({
    name: name ?? email.split('@')[0],
    role: 'viewer',
    user: {
      id:    data.user.id,
      email: data.user.email,
      name:  name ?? email.split('@')[0],
      role:  'viewer',
    },
  });
});

// ── POST /auth/login ──────────────────────────────────────────────────────────
router.post('/login', async (req: Request, res: Response) => {
  const { email, password } = req.body as { email?: string; password?: string };

  if (!email || !password) {
    return res.status(400).json({ message: 'email and password are required' });
  }

  const { data, error } = await supabase.auth.signInWithPassword({ email, password });

  if (error || !data.session) {
    return res.status(401).json({ message: error?.message ?? 'Invalid credentials. Please try again.' });
  }

  // Fetch role
  const { data: roleRow } = await supabaseAdmin
    .from('user_role')
    .select('role')
    .eq('user_id', data.user.id)
    .single();

  const role = roleRow?.role ?? 'viewer';
  const name = (data.user.user_metadata?.display_name as string) ?? email.split('@')[0];

  // Audit log (fire and forget)
  supabaseAdmin.from('audit_log').insert({
    user_id:    data.user.id,
    table_name: 'auth',
    operation:  'LOGIN',
    record_id:  data.user.id,
    payload:    { email },
  });

  return res.json({
    access_token:  data.session.access_token,
    refresh_token: data.session.refresh_token,
    expires_in:    data.session.expires_in,
    name,
    role,
    user: {
      id:    data.user.id,
      email: data.user.email,
      name,
      role,
    },
  });
});

// ── POST /auth/logout ─────────────────────────────────────────────────────────
router.post('/logout', requireAuth, async (req: Request, res: Response) => {
  await supabase.auth.signOut();

  supabaseAdmin.from('audit_log').insert({
    user_id:    req.user!.id,
    table_name: 'auth',
    operation:  'LOGOUT',
    record_id:  req.user!.id,
    payload:    {},
  });

  return res.json({ message: 'Logged out' });
});

// ── GET /auth/me ──────────────────────────────────────────────────────────────
router.get('/me', requireAuth, async (req: Request, res: Response) => {
  return res.json({ user: req.user });
});

export default router;
