"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
/**
 * Auth routes — thin wrapper around Supabase Auth.
 * POST /auth/login    → sign in, return JWT
 * POST /auth/logout   → invalidate session
 * GET  /auth/me       → return current user + role
 */
const express_1 = require("express");
const supabase_1 = require("../config/supabase");
const auth_1 = require("../middleware/auth");
const router = (0, express_1.Router)();
// ── POST /auth/login ──────────────────────────────────────────────────────────
router.post('/login', async (req, res) => {
    const { email, password } = req.body;
    if (!email || !password) {
        return res.status(400).json({ error: 'email and password are required' });
    }
    const { data, error } = await supabase_1.supabase.auth.signInWithPassword({ email, password });
    if (error || !data.session) {
        return res.status(401).json({ error: error?.message ?? 'Login failed' });
    }
    // Fetch role from user_role table
    const { data: roleRow } = await supabase_1.supabaseAdmin
        .from('user_role')
        .select('role')
        .eq('user_id', data.user.id)
        .single();
    // Audit log
    await supabase_1.supabaseAdmin.from('audit_log').insert({
        user_id: data.user.id,
        table_name: 'auth',
        operation: 'LOGIN',
        record_id: data.user.id,
        payload: { email },
    });
    return res.json({
        access_token: data.session.access_token,
        refresh_token: data.session.refresh_token,
        expires_in: data.session.expires_in,
        user: {
            id: data.user.id,
            email: data.user.email,
            role: roleRow?.role ?? 'viewer',
        },
    });
});
// ── POST /auth/logout ─────────────────────────────────────────────────────────
router.post('/logout', auth_1.requireAuth, async (req, res) => {
    await supabase_1.supabase.auth.signOut();
    await supabase_1.supabaseAdmin.from('audit_log').insert({
        user_id: req.user.id,
        table_name: 'auth',
        operation: 'LOGOUT',
        record_id: req.user.id,
        payload: {},
    });
    return res.json({ message: 'Logged out' });
});
// ── GET /auth/me ──────────────────────────────────────────────────────────────
router.get('/me', auth_1.requireAuth, async (req, res) => {
    return res.json({ user: req.user });
});
exports.default = router;
//# sourceMappingURL=auth.js.map