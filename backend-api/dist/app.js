"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
require("dotenv/config");
const express_1 = __importDefault(require("express"));
const helmet_1 = __importDefault(require("helmet"));
const cors_1 = __importDefault(require("cors"));
const express_rate_limit_1 = __importDefault(require("express-rate-limit"));
const auth_1 = __importDefault(require("./routes/auth"));
const stadium_1 = __importDefault(require("./routes/stadium"));
const readings_1 = __importDefault(require("./routes/readings"));
const alerts_1 = __importDefault(require("./routes/alerts"));
const dashboard_1 = __importDefault(require("./routes/dashboard"));
const app = (0, express_1.default)();
const PORT = process.env.PORT ?? 3001;
// ── Security headers ──────────────────────────────────────────────────────────
app.use((0, helmet_1.default)());
// ── CORS ──────────────────────────────────────────────────────────────────────
app.use((0, cors_1.default)({
    origin: process.env.NODE_ENV === 'production'
        ? ['https://your-frontend-domain.com'] // lock down in prod
        : '*',
    methods: ['GET', 'POST', 'PATCH', 'DELETE'],
    allowedHeaders: ['Content-Type', 'Authorization'],
}));
// ── Body parsing ──────────────────────────────────────────────────────────────
app.use(express_1.default.json({ limit: '1mb' }));
// ── Rate limiting ─────────────────────────────────────────────────────────────
const limiter = (0, express_rate_limit_1.default)({
    windowMs: 60 * 1000, // 1 minute
    max: 120, // 120 req/min per IP
    standardHeaders: true,
    legacyHeaders: false,
});
app.use(limiter);
// ── Health check ──────────────────────────────────────────────────────────────
app.get('/health', (_req, res) => {
    res.json({ status: 'ok', service: 'crowd-ai-backend-api', ts: new Date().toISOString() });
});
// ── Routes ────────────────────────────────────────────────────────────────────
app.use('/auth', auth_1.default);
app.use('/stadiums', stadium_1.default);
app.use('/readings', readings_1.default);
app.use('/alerts', alerts_1.default);
app.use('/dashboard', dashboard_1.default);
// ── 404 handler ───────────────────────────────────────────────────────────────
app.use((_req, res) => res.status(404).json({ error: 'Not found' }));
// ── Global error handler ──────────────────────────────────────────────────────
app.use((err, _req, res, _next) => {
    console.error('[error]', err.message);
    res.status(500).json({ error: 'Internal server error' });
});
// ── Start ─────────────────────────────────────────────────────────────────────
app.listen(PORT, () => {
    console.log(`[crowd-api] listening on http://localhost:${PORT}`);
});
exports.default = app;
//# sourceMappingURL=app.js.map