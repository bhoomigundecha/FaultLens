'use strict';
require('./otel');

/**
 * inventory-service — the most interesting service for fault injection.
 *
 * Production patterns implemented:
 *   1. Redis cache-aside for product reads (TTL = CACHE_TTL_SECONDS)
 *   2. Stampede protection via per-key mutex (only one DB query per key)
 *   3. Optimistic locking on stock reservations (prevents overselling)
 *   4. Advisory locks on concurrent updates (triggers deadlock detection)
 *
 * Fault scenarios this service supports:
 *   - REDIS_CACHE_STAMPEDE: flush Redis + concurrent requests → DB overload
 *   - DB_CONNECTION_POOL_EXHAUSTED: hold connections with slow queries
 *   - INVENTORY_DEADLOCK: concurrent reservations for same product
 */

const express = require('express');
const { Pool }   = require('pg');
const Redis      = require('ioredis');

const app  = express();
const PORT = process.env.PORT || 3002;

// ── DB pool ───────────────────────────────────────────────────────────────────
const pool = new Pool({
  host: process.env.DB_HOST, port: process.env.DB_PORT || 5432,
  user: process.env.DB_USER, password: process.env.DB_PASSWORD, database: process.env.DB_NAME,
  max: parseInt(process.env.DB_POOL_MAX || '10'),
  idleTimeoutMillis: 30_000,
  connectionTimeoutMillis: 3_000,
});
pool.on('error', err => console.error('[InventoryDB] Pool error:', err.message));

// ── Redis ─────────────────────────────────────────────────────────────────────
const redis = new Redis(process.env.REDIS_URL || 'redis://localhost:6379', {
  lazyConnect: true,
  retryStrategy: (times) => Math.min(times * 100, 3000),
});
redis.on('error', err => console.error('[Redis] Error:', err.message));
redis.on('connect', () => console.log('[Redis] Connected'));

const CACHE_TTL = parseInt(process.env.CACHE_TTL_SECONDS || '30');

// ── In-flight mutex to prevent cache stampede ─────────────────────────────────
// When key is missing, only one request fetches from DB; others wait on the promise.
const inflightRequests = new Map();

async function getProductCached(productId) {
  const cacheKey = `product:${productId}`;

  // 1. Try cache
  try {
    const cached = await redis.get(cacheKey);
    if (cached) {
      return { source: 'cache', product: JSON.parse(cached) };
    }
  } catch (e) {
    console.warn('[Redis] Cache read failed:', e.message);
  }

  // 2. Stampede protection: deduplicate concurrent DB fetches for same key
  if (inflightRequests.has(cacheKey)) {
    console.warn(`[Inventory] Cache miss — waiting on in-flight request for ${productId}`);
    return inflightRequests.get(cacheKey);
  }

  const dbPromise = (async () => {
    console.log(`[Inventory] Cache MISS — fetching ${productId} from DB`);
    const { rows } = await pool.query(
      'SELECT * FROM products WHERE id = $1 AND is_active = TRUE', [productId]
    );
    const product = rows[0] || null;
    if (product) {
      await redis.setex(cacheKey, CACHE_TTL, JSON.stringify(product)).catch(() => {});
    }
    return { source: 'db', product };
  })();

  inflightRequests.set(cacheKey, dbPromise);
  try {
    return await dbPromise;
  } finally {
    inflightRequests.delete(cacheKey);
  }
}

app.use(express.json());
app.use((req, res, next) => {
  res.on('finish', () => {
    const level = res.statusCode >= 500 ? 'error' : 'log';
    console[level](`${req.method} ${req.path} ${res.statusCode}`);
  });
  next();
});

// ── GET /products ─────────────────────────────────────────────────────────────
app.get('/products', async (req, res) => {
  try {
    const cacheKey = 'products:all';
    const cached = await redis.get(cacheKey).catch(() => null);
    if (cached) return res.json({ source: 'cache', products: JSON.parse(cached) });

    const { rows } = await pool.query(
      'SELECT * FROM products WHERE is_active = TRUE ORDER BY category, name'
    );
    await redis.setex(cacheKey, CACHE_TTL, JSON.stringify(rows)).catch(() => {});
    res.json({ source: 'db', products: rows });
  } catch (err) {
    console.error('[Inventory] List products error:', err.message);
    res.status(500).json({ error: 'Database error', detail: err.message });
  }
});

// ── GET /products/:id ─────────────────────────────────────────────────────────
app.get('/products/:id', async (req, res) => {
  try {
    const { source, product } = await getProductCached(req.params.id);
    if (!product) return res.status(404).json({ error: 'Product not found' });
    res.json({ source, ...product });
  } catch (err) {
    console.error('[Inventory] Get product error:', err.message);
    const isPoolExhausted = err.message?.includes('timeout') || err.message?.includes('pool');
    res.status(isPoolExhausted ? 503 : 500).json({ error: err.message });
  }
});

// ── POST /products/:id/reserve — CRITICAL PATH ────────────────────────────────
// Uses advisory lock to prevent concurrent reservations from overselling.
// This is where deadlocks happen under load (two concurrent requests for same product).
app.post('/products/:id/reserve', async (req, res) => {
  const productId = req.params.id;
  const { order_id, quantity } = req.body;
  if (!quantity || quantity < 1) return res.status(400).json({ error: 'quantity required' });

  const client = await pool.connect().catch(err => {
    console.error('[InventoryDB] Connection pool exhausted on reserve:', err.message);
    return res.status(503).json({ error: 'Inventory temporarily unavailable — DB pool exhausted' });
  });
  if (!client) return; // error already sent

  try {
    await client.query('BEGIN');

    // Advisory lock on product — prevents concurrent oversells
    // hashtext is deterministic: same product → same lock key
    await client.query(`SELECT pg_advisory_xact_lock(hashtext($1))`, [productId]);

    const { rows } = await client.query(
      `SELECT id, name, base_price as unit_price, sku, stock_qty, reserved_qty
       FROM products WHERE id = $1 AND is_active = TRUE FOR UPDATE`,
      [productId]
    );

    if (!rows.length) {
      await client.query('ROLLBACK');
      return res.status(404).json({ error: 'Product not found' });
    }

    const product = rows[0];
    const available = product.stock_qty - product.reserved_qty;
    if (available < quantity) {
      await client.query('ROLLBACK');
      return res.status(409).json({
        error: 'Insufficient stock',
        available, requested: quantity, product_id: productId,
      });
    }

    // Reserve
    await client.query(
      `UPDATE products SET reserved_qty = reserved_qty + $1, updated_at = NOW() WHERE id = $2`,
      [quantity, productId]
    );
    await client.query(
      `INSERT INTO stock_reservations (order_id, product_id, quantity, status)
       VALUES ($1, $2, $3, 'held')`,
      [order_id || 'unknown', productId, quantity]
    );

    await client.query('COMMIT');

    // Invalidate cache
    await redis.del(`product:${productId}`, 'products:all').catch(() => {});

    res.json({ reserved: true, product_id: productId, unit_price: product.unit_price,
               sku: product.sku, available_after: available - quantity });
  } catch (err) {
    await client.query('ROLLBACK').catch(() => {});
    const isDeadlock = err.code === '40P01';
    if (isDeadlock) {
      console.error(`[Inventory] DEADLOCK detected on product ${productId}:`, err.message);
      return res.status(409).json({ error: 'Concurrent reservation conflict — please retry', detail: 'deadlock' });
    }
    console.error('[Inventory] Reserve error:', err.message);
    res.status(500).json({ error: err.message });
  } finally {
    client.release();
  }
});

// ── POST /products/:id/release ────────────────────────────────────────────────
app.post('/products/:id/release', async (req, res) => {
  const { order_id, quantity } = req.body;
  try {
    await pool.query(
      `UPDATE products SET reserved_qty = GREATEST(0, reserved_qty - $1), updated_at = NOW() WHERE id = $2`,
      [quantity, req.params.id]
    );
    await pool.query(
      `UPDATE stock_reservations SET status = 'released' WHERE order_id = $1 AND product_id = $2`,
      [order_id, req.params.id]
    );
    await redis.del(`product:${req.params.id}`, 'products:all').catch(() => {});
    res.json({ released: true });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// ── Admin: flush Redis cache (triggers stampede scenario) ─────────────────────
app.post('/admin/cache/flush', async (req, res) => {
  try {
    await redis.flushdb();
    console.warn('[Inventory] ⚠️  Redis cache FLUSHED — all keys expired');
    res.json({ flushed: true, message: 'All Redis keys cleared — next requests will hit DB' });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// ── Admin: simulate slow DB queries (holds connections) ───────────────────────
app.post('/admin/slow-query', async (req, res) => {
  const durationMs = parseInt(req.body.duration_ms || '5000');
  try {
    // pg_sleep holds the connection for durationMs — use to exhaust pool
    pool.query(`SELECT pg_sleep($1)`, [durationMs / 1000]);
    res.json({ message: `Slow query started (${durationMs}ms), connection held` });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

app.get('/health', (req, res) => res.json({ status: 'ok', service: 'inventory-service' }));

app.listen(PORT, () => console.log(`[inventory-service] :${PORT}`));
