'use strict';
require('./otel');

/**
 * ai-service — AI-powered product recommendations via Ollama.
 *
 * Real failure modes:
 *   - Rate limiting (429) — toggleable for fault injection
 *   - Ollama timeout (model slow to load or inference takes too long)
 *   - Graceful degradation to static "trending" recommendations when Ollama unavailable
 *
 * This is the service most likely to cause AI_RATE_LIMIT_EXCEEDED incidents.
 */

const express = require('express');
const fetch   = require('node-fetch');
const app     = express();
const PORT    = process.env.PORT || 3004;

const OLLAMA_URL   = process.env.OLLAMA_BASE_URL || 'http://localhost:11434';
const OLLAMA_MODEL = process.env.OLLAMA_MODEL    || 'llama3.2';

// ── Rate limiter state ────────────────────────────────────────────────────────
let rateLimitEnabled  = process.env.AI_RATE_LIMIT_ENABLED === 'true';
let rateLimitRpm      = parseInt(process.env.AI_RATE_LIMIT_RPM || '10');
let requestsThisMinute = 0;
let windowStart = Date.now();

setInterval(() => {
  requestsThisMinute = 0;
  windowStart = Date.now();
}, 60_000);

// ── Fallback recommendations ──────────────────────────────────────────────────
const TRENDING = [
  { product_id: 'prod_009', name: 'AirPods Pro 2',        reason: 'Trending in Electronics' },
  { product_id: 'prod_002', name: 'Sony WH-1000XM5',      reason: 'Top rated headphones' },
  { product_id: 'prod_005', name: 'iPhone 15 Pro Max',    reason: 'Best seller this week' },
];

app.use(express.json());
app.use((req, res, next) => {
  res.on('finish', () => console[res.statusCode >= 400 ? 'warn' : 'log'](
    `${req.method} ${req.path} ${res.statusCode}`
  ));
  next();
});

// ── Admin: toggle rate limiting ───────────────────────────────────────────────
app.post('/admin/rate-limit/enable', (req, res) => {
  rateLimitEnabled = true;
  rateLimitRpm = parseInt(req.body.rpm || rateLimitRpm);
  requestsThisMinute = 0;
  console.warn(`[AI] ⚠️  Rate limiting ENABLED: ${rateLimitRpm} RPM`);
  res.json({ enabled: true, rpm: rateLimitRpm });
});
app.post('/admin/rate-limit/disable', (req, res) => {
  rateLimitEnabled = false;
  requestsThisMinute = 0;
  console.log('[AI] Rate limiting DISABLED');
  res.json({ enabled: false });
});

// ── POST /recommend ───────────────────────────────────────────────────────────
app.post('/recommend', async (req, res) => {
  const { product_id, product_name, category, user_history = [] } = req.body;

  // ── Rate limit check ───────────────────────────────────────────────────────
  if (rateLimitEnabled) {
    requestsThisMinute++;
    if (requestsThisMinute > rateLimitRpm) {
      const retryAfter = Math.ceil((60_000 - (Date.now() - windowStart)) / 1000);
      console.error(
        `[AI] 429 — ${requestsThisMinute} req/min exceeds limit of ${rateLimitRpm}. ` +
        `Retry-After: ${retryAfter}s`
      );
      return res.status(429).json({
        error: 'AI rate limit exceeded',
        message: `Too many recommendation requests: ${requestsThisMinute}/${rateLimitRpm} RPM`,
        retry_after: retryAfter,
        fallback: TRENDING,
      });
    }
  }

  // ── Call Ollama ────────────────────────────────────────────────────────────
  const prompt = `You are a product recommendation engine for an e-commerce platform.
A customer is viewing: "${product_name || product_id}" (category: ${category || 'unknown'}).
${user_history.length ? `They recently viewed: ${user_history.slice(0, 3).join(', ')}.` : ''}

Suggest exactly 3 complementary products they might like.
Respond ONLY with a JSON array in this format:
[{"product_name": "...", "reason": "...", "confidence": 0.9}]
Keep each reason under 15 words.`;

  try {
    const ollamaResp = await fetch(`${OLLAMA_URL}/api/generate`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ model: OLLAMA_MODEL, prompt, stream: false }),
      signal:  AbortSignal.timeout(25_000),
    });

    if (!ollamaResp.ok) {
      const errText = await ollamaResp.text();
      console.error(`[AI] Ollama ${ollamaResp.status}: ${errText}`);
      return res.status(200).json({ recommendations: TRENDING, source: 'fallback', ollama_error: ollamaResp.status });
    }

    const data = await ollamaResp.json();
    let recommendations = TRENDING;

    try {
      const jsonMatch = data.response.match(/\[[\s\S]*\]/);
      if (jsonMatch) recommendations = JSON.parse(jsonMatch[0]);
    } catch {
      console.warn('[AI] Could not parse Ollama response as JSON, using fallback');
    }

    res.json({
      product_id,
      recommendations,
      source: 'ollama',
      model: OLLAMA_MODEL,
      latency_ms: Date.now() - windowStart,
    });

  } catch (err) {
    const isTimeout = err.name === 'TimeoutError';
    console.error(`[AI] Ollama ${isTimeout ? 'TIMEOUT' : 'ERROR'}: ${err.message}`);
    // Graceful degradation — return trending products instead of failing
    res.status(200).json({
      recommendations: TRENDING,
      source: 'fallback',
      reason: isTimeout ? 'model_timeout' : 'model_error',
    });
  }
});

app.get('/health', (req, res) => res.json({
  status: 'ok', service: 'ai-service',
  rate_limit: { enabled: rateLimitEnabled, rpm: rateLimitRpm, current: requestsThisMinute },
  ollama: { url: OLLAMA_URL, model: OLLAMA_MODEL },
}));

app.listen(PORT, () => console.log(`[ai-service] :${PORT}`));
