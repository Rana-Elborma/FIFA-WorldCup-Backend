import { Request, Response, NextFunction } from 'express';
import type { AuthUser } from './auth';

const ROLE_RANK: Record<AuthUser['role'], number> = {
  viewer:   1,
  operator: 2,
  admin:    3,
};

/**
 * Middleware factory — requires at least the given role level.
 * Use after requireAuth.
 *
 * @example
 *   router.post('/gate-commands', requireAuth, requireRole('operator'), handler)
 */
export function requireRole(minRole: AuthUser['role']) {
  return (req: Request, res: Response, next: NextFunction) => {
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
