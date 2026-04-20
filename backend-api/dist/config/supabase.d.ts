import 'dotenv/config';
/**
 * Public client — uses the anon key.
 * Respects Row Level Security; use for user-scoped reads/writes.
 */
export declare const supabase: import("@supabase/supabase-js").SupabaseClient<any, "public", "public", any, any>;
/**
 * Service-role client — bypasses RLS entirely.
 * Use ONLY for backend-initiated writes:
 *   - crowd_source ingestion from AI pipeline
 *   - metric_window aggregation
 *   - audit_log writes
 * NEVER expose this client to user-facing routes.
 */
export declare const supabaseAdmin: import("@supabase/supabase-js").SupabaseClient<any, "public", "public", any, any>;
//# sourceMappingURL=supabase.d.ts.map