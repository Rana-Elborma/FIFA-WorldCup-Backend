import { createClient } from '@supabase/supabase-js';
import 'dotenv/config';

const url  = process.env.SUPABASE_URL!;
const anon = process.env.SUPABASE_ANON_KEY!;
const svc  = process.env.SUPABASE_SERVICE_ROLE_KEY!;

if (!url || !anon || !svc) {
  throw new Error('Missing Supabase env vars: SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY');
}

/**
 * Public client — uses the anon key.
 * Respects Row Level Security; use for user-scoped reads/writes.
 */
export const supabase = createClient(url, anon, {
  auth: { persistSession: false },
});

/**
 * Service-role client — bypasses RLS entirely.
 * Use ONLY for backend-initiated writes:
 *   - crowd_source ingestion from AI pipeline
 *   - metric_window aggregation
 *   - audit_log writes
 * NEVER expose this client to user-facing routes.
 */
export const supabaseAdmin = createClient(url, svc, {
  auth: { persistSession: false },
});
