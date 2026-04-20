import 'dotenv/config';
import express from 'express';
import helmet from 'helmet';
import cors from 'cors';
import rateLimit from 'express-rate-limit';

import authRoutes     from './routes/auth';
import stadiumRoutes  from './routes/stadium';
import readingRoutes  from './routes/readings';
import alertRoutes    from './routes/alerts';
import dashboardRoutes from './routes/dashboard';

const app  = express();
const PORT = process.env.PORT ?? 3001;

// ── Security headers ──────────────────────────────────────────────────────────
app.use(helmet());

// ── CORS ──────────────────────────────────────────────────────────────────────
app.use(cors({
  origin: process.env.NODE_ENV === 'production'
    ? ['https://your-frontend-domain.com']   // lock down in prod
    : '*',
  methods: ['GET', 'POST', 'PATCH', 'DELETE'],
  allowedHeaders: ['Content-Type', 'Authorization'],
}));

// ── Body parsing ──────────────────────────────────────────────────────────────
app.use(express.json({ limit: '1mb' }));

// ── Rate limiting ─────────────────────────────────────────────────────────────
const limiter = rateLimit({
  windowMs: 60 * 1000,   // 1 minute
  max: 120,              // 120 req/min per IP
  standardHeaders: true,
  legacyHeaders: false,
});
app.use(limiter);

// ── Health check ──────────────────────────────────────────────────────────────
app.get('/health', (_req, res) => {
  res.json({ status: 'ok', service: 'crowd-ai-backend-api', ts: new Date().toISOString() });
});

// ── Routes ────────────────────────────────────────────────────────────────────
app.use('/auth',      authRoutes);
app.use('/stadiums',  stadiumRoutes);
app.use('/readings',  readingRoutes);
app.use('/alerts',    alertRoutes);
app.use('/dashboard', dashboardRoutes);

// ── 404 handler ───────────────────────────────────────────────────────────────
app.use((_req, res) => res.status(404).json({ error: 'Not found' }));

// ── Global error handler ──────────────────────────────────────────────────────
app.use((err: Error, _req: express.Request, res: express.Response, _next: express.NextFunction) => {
  console.error('[error]', err.message);
  res.status(500).json({ error: 'Internal server error' });
});

// ── Start ─────────────────────────────────────────────────────────────────────
app.listen(PORT, () => {
  console.log(`[crowd-api] listening on http://localhost:${PORT}`);
});

export default app;
