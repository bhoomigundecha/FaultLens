-- ShopFlow production schema
-- All services share one Postgres instance (separate schemas)
-- This is realistic — most startups do this before moving to per-service DBs

-- ── Orders (owned by order-service) ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS orders (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      TEXT        NOT NULL,
    status       TEXT        NOT NULL DEFAULT 'pending'
                             CHECK (status IN ('pending', 'reserved', 'paid', 'failed', 'cancelled', 'refunded')),
    total_amount NUMERIC(12,2) NOT NULL,
    currency     TEXT        NOT NULL DEFAULT 'USD',
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    payment_id   TEXT,
    failure_reason TEXT
);
CREATE INDEX IF NOT EXISTS idx_orders_user_id    ON orders(user_id);
CREATE INDEX IF NOT EXISTS idx_orders_status     ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at DESC);

CREATE TABLE IF NOT EXISTS order_items (
    id          SERIAL      PRIMARY KEY,
    order_id    UUID        NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id  TEXT        NOT NULL,
    sku         TEXT        NOT NULL,
    quantity    INT         NOT NULL CHECK (quantity > 0),
    unit_price  NUMERIC(10,2) NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items(order_id);

-- ── Inventory (owned by inventory-service) ────────────────────────────────────
CREATE TABLE IF NOT EXISTS products (
    id           TEXT        PRIMARY KEY,  -- e.g. "prod_001"
    name         TEXT        NOT NULL,
    category     TEXT        NOT NULL,
    description  TEXT,
    base_price   NUMERIC(10,2) NOT NULL,
    sku          TEXT        NOT NULL UNIQUE,
    stock_qty    INT         NOT NULL DEFAULT 0 CHECK (stock_qty >= 0),
    reserved_qty INT         NOT NULL DEFAULT 0,
    weight_kg    NUMERIC(6,3),
    is_active    BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS stock_reservations (
    id           SERIAL      PRIMARY KEY,
    order_id     UUID        NOT NULL,
    product_id   TEXT        NOT NULL REFERENCES products(id),
    quantity     INT         NOT NULL,
    status       TEXT        NOT NULL DEFAULT 'held'
                             CHECK (status IN ('held', 'confirmed', 'released')),
    expires_at   TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '15 minutes'),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_reservations_order_id   ON stock_reservations(order_id);
CREATE INDEX IF NOT EXISTS idx_reservations_expires_at ON stock_reservations(expires_at);

CREATE TABLE IF NOT EXISTS payments (
    id              TEXT        PRIMARY KEY,   -- from payment processor
    order_id        UUID        NOT NULL REFERENCES orders(id),
    amount          NUMERIC(12,2) NOT NULL,
    currency        TEXT        NOT NULL DEFAULT 'USD',
    status          TEXT        NOT NULL DEFAULT 'pending'
                                CHECK (status IN ('pending','authorised','captured','failed','refunded')),
    processor_ref   TEXT,
    failure_code    TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_payments_order_id ON payments(order_id);

-- ── Seed realistic product catalog ────────────────────────────────────────────
INSERT INTO products (id, name, category, description, base_price, sku, stock_qty, weight_kg) VALUES
    ('prod_001', 'MacBook Pro 16"',           'electronics', 'M3 Pro chip, 18GB RAM',            2499.00, 'MBP16-M3P-18',  150, 2.15),
    ('prod_002', 'Sony WH-1000XM5',           'electronics', 'Noise cancelling headphones',        349.99, 'SONY-WH1K-XM5',  800, 0.25),
    ('prod_003', 'Ergonomic Office Chair',     'furniture',   'Lumbar support, adjustable',        699.00, 'CHAIR-ERG-001',  200, 18.00),
    ('prod_004', 'Standing Desk 160cm',        'furniture',   'Electric height adjustment',        899.00, 'DESK-SIT-160',   100, 35.00),
    ('prod_005', 'iPhone 15 Pro Max',          'electronics', '256GB, Natural Titanium',          1199.00, 'IPH15PM-256-NT', 500, 0.22),
    ('prod_006', 'Nike Air Max 270',           'apparel',     'Running shoes, various sizes',       149.99, 'NK-AM270-BLK',  2000, 0.65),
    ('prod_007', 'Protein Powder 2kg',         'health',      'Whey isolate, chocolate',            49.99, 'WHEY-ISO-2KG',  5000, 2.10),
    ('prod_008', 'Dyson V15 Detect',           'appliances',  'Cordless vacuum, laser dust',       749.99, 'DYS-V15-DET',    300, 3.05),
    ('prod_009', 'AirPods Pro 2',              'electronics', 'USB-C, Active noise cancellation',  249.99, 'APP2-USBC-WHT', 1200, 0.06),
    ('prod_010', 'Samsung 4K Monitor 32"',     'electronics', 'IPS, 144Hz, HDR600',               599.99, 'SAM-4K32-IPS',   400, 6.80),
    ('prod_011', 'Levi''s 501 Jeans',          'apparel',     'Classic straight fit',               89.99, 'LEV-501-32W32L',3000, 0.55),
    ('prod_012', 'Instant Pot Duo 7-in-1',     'appliances',  '6 Quart pressure cooker',            99.99, 'IP-DUO-6QT',    1500, 4.76),
    ('prod_013', 'Kindle Paperwhite 11th Gen', 'electronics', '8GB, Waterproof, 6.8"',             139.99, 'KIN-PW11-8GB',   900, 0.21),
    ('prod_014', 'Yoga Mat Premium',           'health',      'Non-slip, 6mm thick',                39.99, 'YOGA-MAT-6MM', 10000, 1.00),
    ('prod_015', 'Coffee Grinder Baratza',     'appliances',  'Conical burr, 40 grind settings',  179.99, 'BAR-ENK-GRD',    250, 1.63)
ON CONFLICT (id) DO NOTHING;
