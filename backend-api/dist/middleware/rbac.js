"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.requireRole = requireRole;
const ROLE_RANK = {
    viewer: 1,
    operator: 2,
    admin: 3,
};
/**
 * Middleware factory — requires at least the given role level.
 * Use after requireAuth.
 *
 * @example
 *   router.post('/gate-commands', requireAuth, requireRole('operator'), handler)
 */
function requireRole(minRole) {
    return (req, res, next) => {
        if (!req.user) {
            return res.status(401).json({ error: 'Unauthenticated' });
        }
        if (ROLE_RANK[req.user.role] < ROLE_RANK[minRole]) {
            return res.status(403).json({
                error: `Requires ${minRole} role or higher. Your role: ${req.user.role}`,
            });
        }
        return next();
    };
}
//# sourceMappingURL=rbac.js.map