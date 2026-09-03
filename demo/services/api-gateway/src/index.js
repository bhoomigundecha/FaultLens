'use strict';
require('./otel');

const express    = require('express');
const fetch      = require('node-fetch');
const rateLimit  = require('express-rate-limit');
const jwt        = require('jsonwebtoken');

const app  = express();
const PORT = process.env.PORT || 3000;
const ORDER_SVC     = process.env.ORDER_SERVICE_URL     || 'http://localhost:3001';
const INVENTORY_SVC = process.env.INVENTORY_SERVICE_URL || 'http://localhost:3002';
const PAYMENT_SVC   = process.env.PAYMENT_SERVICE_URL   || 'http://localhost:3003';
const AI_SVC        = process.env.AI_SERVICE_URL        || 'http://localhost:3004';
const JWT_SECRET    = process.env.JWT_SECRET            || 'dev-secret';
const DOWNSTREAM_TIMEOUT = parseInt(process.env.DOWNSTREAM_TIMEOUT_MS || '8000');

app.use(express.json());
app.use(require('express').urlencoded({ extended: true }));

// ── Global request logger ─────────────────────────────────────────────────────
app.use((req, res, next) => {
  const start = Date.now();
  res.on('finish', () => {
    const ms = Date.now() - start;
    const level = res.statusCode >= 500 ? 'ERROR' : res.statusCode >= 400 ? 'WARN' : 'INFO';
    console[level === 'INFO' ? 'log' : 'warn'](
      `[${level}] ${req.method} ${req.path} → ${res.statusCode} (${ms}ms)`
    );
  });
  next();
});

// ── Rate limiter (gateway-level) ──────────────────────────────────────────────
const limiter = rateLimit({
  windowMs: 60_000,
  max: parseInt(process.env.RATE_LIMIT_RPM || '600'),
  standardHeaders: true,
  message: { error: 'Gateway rate limit exceeded', retry_after: 60 },
});
app.use('/api/', limiter);

// ── Auth middleware (JWT) ─────────────────────────────────────────────────────
// Issues a demo token so we can test auth flows
app.get('/auth/token', (req, res) => {
  const userId = req.query.user_id || `user_${Math.random().toString(36).slice(2, 8)}`;
  const token  = jwt.sign({ sub: userId, role: 'customer' }, JWT_SECRET, { expiresIn: '1h' });
  res.json({ token, user_id: userId });
});

function authMiddleware(req, res, next) {
  const header = req.headers['authorization'];
  if (!header) return res.status(401).json({ error: 'Missing Authorization header' });
  const token = header.replace('Bearer ', '');
  try {
    req.user = jwt.verify(token, JWT_SECRET);
    next();
  } catch (e) {
    console.error(`[Auth] Invalid token: ${e.message}`);
    return res.status(401).json({ error: 'Invalid or expired token' });
  }
}

// ── Proxy helper ──────────────────────────────────────────────────────────────
async function proxy(targetUrl, req, res) {
  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), DOWNSTREAM_TIMEOUT);

    const upstream = await fetch(targetUrl, {
      method: req.method,
      headers: {
        'Content-Type': 'application/json',
        'X-User-Id':    req.user?.sub || 'anonymous',
        'X-Request-Id': req.headers['x-request-id'] || crypto.randomUUID(),
      },
      body:   ['POST', 'PUT', 'PATCH'].includes(req.method) ? JSON.stringify(req.body) : undefined,
      signal: controller.signal,
    });
    clearTimeout(timer);

    const data = await upstream.json().catch(() => ({}));
    res.status(upstream.status).json(data);

  } catch (err) {
    if (err.name === 'AbortError') {
      console.error(`[Gateway] Upstream timeout: ${targetUrl} (>${DOWNSTREAM_TIMEOUT}ms)`);
      return res.status(504).json({
        error: 'Upstream service timeout',
        service: targetUrl,
        timeout_ms: DOWNSTREAM_TIMEOUT,
      });
    }
    console.error(`[Gateway] Upstream error: ${targetUrl} — ${err.message}`);
    res.status(502).json({ error: 'Bad gateway', detail: err.message });
  }
}

// ── Routes ────────────────────────────────────────────────────────────────────

// Product catalog (public)
app.get('/api/products',      (req, res) => proxy(`${INVENTORY_SVC}/products`, req, res));
app.get('/api/products/:id',  (req, res) => proxy(`${INVENTORY_SVC}/products/${req.params.id}`, req, res));

// Orders (auth required)
app.post('/api/orders',       authMiddleware, (req, res) => proxy(`${ORDER_SVC}/orders`, req, res));
app.get('/api/orders',        authMiddleware, (req, res) => proxy(`${ORDER_SVC}/orders?user_id=${req.user.sub}`, req, res));
app.get('/api/orders/:id',    authMiddleware, (req, res) => proxy(`${ORDER_SVC}/orders/${req.params.id}`, req, res));

// AI recommendations (public)
app.post('/api/recommendations', (req, res) => proxy(`${AI_SVC}/recommend`, req, res));

// Admin endpoints (for fault injector — no auth in demo)
app.post('/admin/payment/set-latency', (req, res) =>
  proxy(`${process.env.PAYMENT_SERVICE_URL || 'http://payment-service:3003'}/admin/set-latency`, req, res));
app.post('/admin/ai/rate-limit/enable', (req, res) =>
  proxy(`${AI_SVC}/admin/rate-limit/enable`, req, res));
app.post('/admin/ai/rate-limit/disable', (req, res) =>
  proxy(`${AI_SVC}/admin/rate-limit/disable`, req, res));
// ── Unified Chaos Control Plane ──────────────────────────────────────────
// Query all subsystem health and active faults in this ONE application
app.get('/chaos/status', async (req, res) => {
  const check = async (url) => {
    try {
      const r = await fetch(url, { signal: AbortSignal.timeout(2000) });
      return await r.json();
    } catch (e) {
      return { status: 'down', error: e.message };
    }
  };

  const [order, inventory, payment, ai] = await Promise.all([
    check(`${ORDER_SVC}/health`),
    check(`${INVENTORY_SVC}/health`),
    check(`${PAYMENT_SVC}/health`),
    check(`${AI_SVC}/health`),
  ]);

  res.json({
    application: 'ShopFlow (Production E-Commerce Platform)',
    services: {
      gateway: { status: 'ok', port: PORT },
      order_service: order,
      inventory_service: inventory,
      payment_service: payment,
      ai_service: ai,
    },
    active_faults: {
      ai_rate_limited: ai?.rate_limit?.enabled || false,
      payment_latency_ms: payment?.latency_ms || 0,
      payment_circuit: payment?.circuit || 'closed',
    },
    timestamp: new Date().toISOString(),
  });
});

// ── Rolling Realistic Chaos Engine ───────────────────────────────────────
// Injects realistic 1-2 fault waves from time to time with quiet periods in between.
let rollingChaosInterval = null;
let currentActiveWave = null;

const CHAOS_WAVES = [
  {
    name: 'payment_slowdown',
    description: 'Payment processor slows down to 5.5s causing checkout 504 timeouts (2 services affected: payment + order)',
    start: async () => {
      await fetch(`${PAYMENT_SVC}/admin/set-latency`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ latency_ms: 5500, failure_rate: 0.15 }),
      }).catch(() => {});
    },
    stop: async () => {
      await fetch(`${PAYMENT_SVC}/admin/set-latency`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ latency_ms: 0, failure_rate: 0.03 }),
      }).catch(() => {});
    },
  },
  {
    name: 'cache_expiry_db_spike',
    description: 'Redis cache flushes during high load, spiking DB query latency (1-2 services affected: inventory + postgres)',
    start: async () => {
      await fetch(`${INVENTORY_SVC}/admin/cache/flush`, { method: 'POST' }).catch(() => {});
      fetch(`${INVENTORY_SVC}/admin/slow-query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ duration_ms: 15000 }),
      }).catch(() => {});
    },
    stop: async () => {},
  },
  {
    name: 'ai_rate_limit_throttle',
    description: 'LLM token rate limit exceeded; returns 429s and falls back to cached trending (1 service affected: ai-service)',
    start: async () => {
      await fetch(`${AI_SVC}/admin/rate-limit/enable`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rpm: 4 }),
      }).catch(() => {});
    },
    stop: async () => {
      await fetch(`${AI_SVC}/admin/rate-limit/disable`, { method: 'POST' }).catch(() => {});
    },
  },
];

async function triggerIncident(waveIndex = null) {
  const wave = waveIndex !== null
    ? CHAOS_WAVES[waveIndex % CHAOS_WAVES.length]
    : CHAOS_WAVES[Math.floor(Math.random() * CHAOS_WAVES.length)];

  currentActiveWave = wave.name;
  console.warn(`[PRODUCTION INCIDENT] ⚠️ Fault active: ${wave.name} — ${wave.description}`);
  console.warn(`[PRODUCTION INCIDENT] ⚠️ System is now degraded and will REMAIN DEGRADED until remediated.`);
  await wave.start();
  return wave;
}

// Trigger a realistic production incident (1-2 services affected).
// REMAINS DOWN until manually resolved so FaultLens can continuously monitor and report!
app.post('/chaos/incident', async (req, res) => {
  const waveName = req.body?.wave;
  const waveIdx = waveName ? CHAOS_WAVES.findIndex(w => w.name === waveName) : null;
  const wave = await triggerIncident(waveIdx !== -1 ? waveIdx : null);
  res.json({
    status: 'INCIDENT_ACTIVE',
    incident: wave.name,
    description: wave.description,
    remediation_command: 'Run `make demo-restore` or POST /chaos/reset after checking FaultLens report',
    auto_heals: false,
    timestamp: new Date().toISOString(),
  });
});

// Trigger random realistic production incident that stays active until resolved
app.post('/chaos/trigger-random', async (req, res) => {
  const wave = await triggerIncident(null);
  res.json({
    status: 'INCIDENT_ACTIVE',
    incident: wave.name,
    description: wave.description,
    message: 'Fault is active in production and will NOT self-heal. Telemetry is streaming into FaultLens for continuous check & analysis.',
    remediation_command: 'Run `make demo-restore` to apply fix after reviewing FaultLens RCA report',
  });
});

// Stop continuous rolling chaos and restore everything to normal
app.post('/chaos/stop-rolling', async (req, res) => {
  if (rollingChaosInterval) {
    clearInterval(rollingChaosInterval);
    rollingChaosInterval = null;
  }
  currentActiveWave = null;
  for (const wave of CHAOS_WAVES) {
    await wave.stop().catch(() => {});
  }
  await fetch(`${PAYMENT_SVC}/admin/circuit/reset`, { method: 'POST' }).catch(() => {});
  console.log('[CHAOS ENGINE] 🛑 Rolling chaos stopped. All services healthy.');
  res.json({ status: 'STOPPED', message: 'Rolling chaos stopped and all subsystems restored to healthy.' });
});

// Reset all faults in this one app back to normal
app.post('/chaos/reset', async (req, res) => {
  if (rollingChaosInterval) {
    clearInterval(rollingChaosInterval);
    rollingChaosInterval = null;
  }
  currentActiveWave = null;
  for (const wave of CHAOS_WAVES) {
    await wave.stop().catch(() => {});
  }
  await fetch(`${PAYMENT_SVC}/admin/circuit/reset`, { method: 'POST' }).catch(() => {});
  console.log('[CHAOS] ✅ All faults reset — ShopFlow running normally');
  res.json({ status: 'HEALTHY', message: 'All injected faults disabled across all services' });
});

// Health
app.get('/health', (req, res) => res.json({
  status: 'ok',
  service: 'api-gateway',
  upstreams: { order: ORDER_SVC, inventory: INVENTORY_SVC, ai: AI_SVC },
  timestamp: new Date().toISOString(),
}));

app.use((err, req, res, next) => {
  console.error('[Gateway] Unhandled:', err);
  res.status(500).json({ error: 'Internal gateway error', detail: err.message });
});

app.listen(PORT, () => console.log(`[api-gateway] Listening on :${PORT}`));
module.exports = app;
