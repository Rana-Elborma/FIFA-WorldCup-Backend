import { Request, Response, NextFunction } from 'express';
export interface AuthUser {
    id: string;
    email: string;
    role: 'admin' | 'operator' | 'viewer';
}
declare global {
    namespace Express {
        interface Request {
            user?: AuthUser;
        }
    }
}
/**
 * Verifies the Supabase JWT from the Authorization header.
 * Attaches req.user = { id, email, role } on success.
 */
export declare function requireAuth(req: Request, res: Response, next: NextFunction): Promise<void | Response<any, Record<string, any>>>;
//# sourceMappingURL=auth.d.ts.map