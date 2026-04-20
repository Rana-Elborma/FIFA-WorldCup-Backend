import { Request, Response, NextFunction } from 'express';
import jwt from 'jsonwebtoken';
import { supabase } from '../config/supabase';

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
export async function requireAuth(req: Request, res: Response, next: NextFunction) {
  const authHeader = req.headers.authorization;
  if (!authHeader?.startsWith('Bearer ')) {
    return res.status(401).json({ error: 'Missing or invalid Authorization header' });
  }

  const token = authHeader.slice(7);

  try {
    // Verify signature with Supabase JWT secret
    const payload = jwt.verify(token, process.env.SUPABASE_JWT_SECRET!) as jwt.JwtPayload;

    // Fetch role from user_role table using service client (bypasses RLS)
    const { data, error } = await supabase
      .from('user_role')
      .select('role')
      .eq('user_id', payload.sub)
      .single();

    if (error || !data) {
      return res.status(401).json({ error: 'User not found or inactive' });
    }

    req.user = {
      id:    payload.sub as string,
      email: payload.email as string,
      role:  data.role as AuthUser['role'],
    };

    return next();
  } catch {
    return res.status(401).json({ error: 'Invalid or expired token' });
  }
}
