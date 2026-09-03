'use strict';
require('./otel');

/**
 * payment-service — simulates a payment processor gateway.
 *
 * Real production failures modeled:
 *   - Configurable processing latency (Stripe/Adyen slowdowns)
 *   - Configurable failure rate (payment declines, processor errors)
 *   - Idempotency key tracking (duplicate charge prevention)
 *   - Circuit breaker state (too many failures → open circuit)
 */

const express = require('express');
const { v4: uuidv4 } = require('uuid');
const app  = express();
const PORT = process.env.PORT || 3003;

// ── Fault injection state ─────────────────────────────────────────────────────
let latencyMs     = parseInt(process.env.PAYMENT_LATENCY_MS    || '0');
let failureRate   = parseFloat(process.env.PAYMENT_FAILURE_RATE || '0.03');
let circuitOpen   = false;
let failureCount  = 0;
const CIRCUIT_THRESHOLD = 5;  // open circuit after N failures in 1 minute
let failureWindow = [];

// Idempotency cache (in-memory — use Redis in real production)
const idempotencyCache = new Map();

app.use(express.json());
app.use((req, res, next) => {
  res.on('finish', () => console[res.statusCode >= 500 ? 'error' : 'log'](
    `${req.method} ${req.path} ${res.statusCode}`
  ));
  next();
});

// ── Circuit breaker ───────────────────────────────────────────────────────────
function recordFailure() {
  const now = Date.now();
  failureWindow = failureWindow.filter(t => now - t < 60_000);
  failureWindow.push(now);
  if (failureWindow.length >= CIRCUIT_THRESHOLD && !circuitOpen) {
    circuitOpen = true;
    console.error(`[Payment] ⚡ Circuit OPENED after ${failureWindow.length} failures in 60s`);
    // Auto-reset after 30s
    setTimeout(() => {
      circuitOpen = false;
      failureWindow = [];
      console.log('[Payment] Circuit CLOSED (auto-reset)');
    }, 30_000);
  }
}

// ── POST /charge ──────────────────────────────────────────────────────────────
app.post('/charge', async (req, res) => {
  const { order_id, amount, currency = 'USD', idempotency_key } = req.body;
  if (!order_id || !amount) return res.status(400).json({ error: 'order_id and amount required' });

  // Check idempotency
  if (idempotency_key && idempotencyCache.has(idempotency_key)) {
    console.log(`[Payment] Idempotent replay: ${idempotency_key}`);
    return res.json(idempotencyCache.get(idempotency_key));
  }

  // Circuit breaker
  if (circuitOpen) {
    console.error('[Payment] Circuit OPEN — rejecting charge request');
    return res.status(503).json({
      error: 'Payment processor circuit open — too many recent failures',
      retry_after: 30,
    });
  }

  // ── Injected latency (simulates slow payment processor) ───────────────────
  if (latencyMs > 0) {
    console.warn(`[Payment] Injected latency: ${latencyMs}ms`);
    await new Promise(r => setTimeout(r, latencyMs));
  }

  // ── Simulated failure ─────────────────────────────────────────────────────
  if (Math.random() < failureRate) {
    const codes = ['card_declined', 'insufficient_funds', 'do_not_honor', 'lost_card'];
    const code  = codes[Math.floor(Math.random() * codes.length)];
    console.error(`[Payment] Charge DECLINED for order ${order_id}: ${code}`);
    recordFailure();
    return res.status(402).json({ error: 'Payment declined', failure_code: code, order_id });
  }

  // ── Success ───────────────────────────────────────────────────────────────
  const paymentId = `pay_${uuidv4().replace(/-/g, '').slice(0, 24)}`;
  const result = {
    payment_id: paymentId,
    order_id,
    amount: parseFloat(amount).toFixed(2),
    currency,
    status: 'captured',
    processor: 'shopflow-simulator',
    created_at: new Date().toISOString(),
  };

  if (idempotency_key) idempotencyCache.set(idempotency_key, result);
  res.json(result);
});

// ── POST /refund ──────────────────────────────────────────────────────────────
app.post('/refund', async (req, res) => {
  const { payment_id, amount } = req.body;
  if (!payment_id) return res.status(400).json({ error: 'payment_id required' });
  if (latencyMs > 0) await new Promise(r => setTimeout(r, latencyMs / 2));
  res.json({
    refund_id: `refund_${uuidv4().slice(0, 8)}`,
    payment_id, amount: amount || 'full',
    status: 'refunded',
  });
});

// ── Admin endpoints ───────────────────────────────────────────────────────────
app.post('/admin/set-latency', (req, res) => {
  latencyMs   = parseInt(req.body.latency_ms   || '0');
  failureRate = parseFloat(req.body.failure_rate ?? failureRate);
  console.warn(`[Payment] Config updated: latency=${latencyMs}ms, failure_rate=${failureRate}`);
  res.json({ latency_ms: latencyMs, failure_rate: failureRate });
});

app.post('/admin/circuit/reset', (req, res) => {
  circuitOpen  = false;
  failureWindow = [];
  console.log('[Payment] Circuit manually reset');
  res.json({ circuit: 'closed' });
});

app.get('/health', (req, res) => res.json({
  status: circuitOpen ? 'degraded' : 'ok',
  service: 'payment-service',
  circuit: circuitOpen ? 'open' : 'closed',
  latency_ms: latencyMs,
  failure_rate: failureRate,
}));

app.listen(PORT, () => console.log(`[payment-service] :${PORT}`));
