'use strict';
require('./otel');

const express = require('express');
const fetch   = require('node-fetch');
const { Pool } = require('pg');
const { v4: uuidv4 } = require('uuid');

const app  = express();
const PORT = process.env.PORT || 3001;

const INVENTORY_SVC = process.env.INVENTORY_SERVICE_URL || 'http://localhost:3002';
const PAYMENT_SVC   = process.env.PAYMENT_SERVICE_URL   || 'http://localhost:3003';
const TIMEOUT_MS    = parseInt(process.env.DOWNSTREAM_TIMEOUT_MS || '5000');

// ── DB pool — max intentionally low for fault scenario ────────────────────────
const pool = new Pool({
  host: process.env.DB_HOST, port: process.env.DB_PORT || 5432,
  user: process.env.DB_USER, password: process.env.DB_PASSWORD, database: process.env.DB_NAME,
  max: parseInt(process.env.DB_POOL_MAX || '10'),
  idleTimeoutMillis: 30_000,
  connectionTimeoutMillis: 3_000,   // tight — will surface pool exhaustion fast
});
pool.on('error', err => console.error('[OrderDB] Pool error:', err.message));

app.use(express.json());
app.use((req, res, next) => {
  res.on('finish', () => {
    const level = res.statusCode >= 500 ? 'error' : 'log';
    console[level](`${req.method} ${req.path} ${res.statusCode}`);
  });
  next();
});

// ── Helpers ───────────────────────────────────────────────────────────────────
async function callService(url, method = 'GET', body) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), TIMEOUT_MS);
  try {
    const resp = await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: body ? JSON.stringify(body) : undefined,
      signal: ctrl.signal,
    });
    clearTimeout(timer);
    return { ok: resp.ok, status: resp.status, data: await resp.json().catch(() => ({})) };
  } catch (err) {
    clearTimeout(timer);
    if (err.name === 'AbortError')
      throw Object.assign(new Error(`Timeout calling ${url} (>${TIMEOUT_MS}ms)`), { code: 'ETIMEOUT' });
    throw err;
  }
}

// ── POST /orders ──────────────────────────────────────────────────────────────
app.post('/orders', async (req, res) => {
  const { items, currency = 'USD' } = req.body;
  const userId = req.headers['x-user-id'] || 'anonymous';

  if (!items?.length) return res.status(400).json({ error: 'items[] required' });

  const client = await pool.connect().catch(err => {
    console.error('[OrderDB] Connection pool exhausted:', err.message);
    throw Object.assign(err, { poolExhausted: true });
  });

  try {
    await client.query('BEGIN');

    // 1. Validate + reserve stock at inventory-service
    let total = 0;
    const reservations = [];
    for (const item of items) {
      const inv = await callService(
        `${INVENTORY_SVC}/products/${item.product_id}/reserve`,
        'POST', { order_id: 'pending', quantity: item.quantity }
      );
      if (!inv.ok) {
        await client.query('ROLLBACK');
        return res.status(inv.status).json({
          error: 'Stock reservation failed',
          product_id: item.product_id,
          detail: inv.data,
        });
      }
      total += inv.data.unit_price * item.quantity;
      reservations.push({ ...item, unit_price: inv.data.unit_price });
    }

    // 2. Create order record
    const orderId = uuidv4();
    await client.query(
      `INSERT INTO orders (id, user_id, status, total_amount, currency)
       VALUES ($1, $2, 'reserved', $3, $4)`,
      [orderId, userId, total.toFixed(2), currency]
    );
    for (const item of reservations) {
      await client.query(
        `INSERT INTO order_items (order_id, product_id, sku, quantity, unit_price)
         VALUES ($1, $2, $3, $4, $5)`,
        [orderId, item.product_id, item.sku || item.product_id, item.quantity, item.unit_price]
      );
    }

    // 3. Charge payment
    let payResp;
    try {
      payResp = await callService(`${PAYMENT_SVC}/charge`, 'POST', {
        order_id: orderId, amount: total.toFixed(2), currency,
      });
    } catch (err) {
      // Payment timeout — mark order as failed, release stock
      await client.query(`UPDATE orders SET status='failed', failure_reason=$2 WHERE id=$1`,
        [orderId, err.message]);
      await client.query('COMMIT');
      console.error('[Order] Payment service error:', err.message);
      return res.status(err.code === 'ETIMEOUT' ? 504 : 502).json({
        error: 'Payment failed', detail: err.message, order_id: orderId,
      });
    }

    if (!payResp.ok) {
      await client.query(`UPDATE orders SET status='failed', failure_reason=$2, payment_id=$3 WHERE id=$1`,
        [orderId, payResp.data.error || 'Payment declined', payResp.data.payment_id]);
      await client.query('COMMIT');
      return res.status(402).json({ error: 'Payment declined', detail: payResp.data, order_id: orderId });
    }

    // 4. Confirm
    await client.query(
      `UPDATE orders SET status='paid', payment_id=$2, updated_at=NOW() WHERE id=$1`,
      [orderId, payResp.data.payment_id]
    );
    await client.query('COMMIT');

    res.status(201).json({ order_id: orderId, status: 'paid', total, payment: payResp.data });

  } catch (err) {
    await client.query('ROLLBACK').catch(() => {});
    console.error('[Order] Transaction error:', err.message);
    if (err.poolExhausted) return res.status(503).json({ error: 'Service temporarily unavailable — DB pool exhausted' });
    res.status(500).json({ error: 'Order processing failed', detail: err.message });
  } finally {
    client.release();
  }
});

// ── GET /orders ───────────────────────────────────────────────────────────────
app.get('/orders', async (req, res) => {
  const userId = req.query.user_id;
  try {
    const { rows } = await pool.query(
      `SELECT o.*, json_agg(json_build_object(
         'product_id', oi.product_id, 'quantity', oi.quantity, 'unit_price', oi.unit_price
       )) AS items
       FROM orders o
       LEFT JOIN order_items oi ON oi.order_id = o.id
       ${userId ? 'WHERE o.user_id = $1' : ''}
       GROUP BY o.id
       ORDER BY o.created_at DESC LIMIT 50`,
      userId ? [userId] : []
    );
    res.json(rows);
  } catch (err) {
    console.error('[Order] List error:', err.message);
    res.status(500).json({ error: err.message });
  }
});

// ── GET /orders/:id ───────────────────────────────────────────────────────────
app.get('/orders/:id', async (req, res) => {
  try {
    const { rows } = await pool.query('SELECT * FROM orders WHERE id = $1', [req.params.id]);
    if (!rows.length) return res.status(404).json({ error: 'Order not found' });
    res.json(rows[0]);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.get('/health', (req, res) => res.json({ status: 'ok', service: 'order-service' }));

app.listen(PORT, () => console.log(`[order-service] :${PORT}`));
