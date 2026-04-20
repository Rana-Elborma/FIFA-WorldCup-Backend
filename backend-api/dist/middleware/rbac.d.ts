import { Request, Response, NextFunction } from 'express';
import type { AuthUser } from './auth';
/**
 * Middleware factory — requires at least the given role level.
 * Use after requireAuth.
 *
 * @example
 *   router.post('/gate-commands', requireAuth, requireRole('operator'), handler)
 */
export declare function requireRole(minRole: AuthUser['role']): (req: Request, res: Response, next: NextFunction) => void | Response<any, Record<string, any>>;
//# sourceMappingURL=rbac.d.ts.map