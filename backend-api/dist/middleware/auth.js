"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.requireAuth = requireAuth;
const jsonwebtoken_1 = __importDefault(require("jsonwebtoken"));
const supabase_1 = require("../config/supabase");
/**
 * Verifies the Supabase JWT from the Authorization header.
 * Attaches req.user = { id, email, role } on success.
 */
async function requireAuth(req, res, next) {
    const authHeader = req.headers.authorization;
    if (!authHeader?.startsWith('Bearer ')) {
        return res.status(401).json({ error: 'Missing or invalid Authorization header' });
    }
    const token = authHeader.slice(7);
    try {
        // Verify signature with Supabase JWT secret
        const payload = jsonwebtoken_1.default.verify(token, process.env.SUPABASE_JWT_SECRET);
        // Fetch role from user_role table using service client (bypasses RLS)
        const { data, error } = await supabase_1.supabase
            .from('user_role')
            .select('role')
            .eq('user_id', payload.sub)
            .single();
        if (error || !data) {
            return res.status(401).json({ error: 'User not found or inactive' });
        }
        req.user = {
            id: payload.sub,
            email: payload.email,
            role: data.role,
        };
        return next();
    }
    catch {
        return res.status(401).json({ error: 'Invalid or expired token' });
    }
}
//# sourceMappingURL=auth.js.map