#!/usr/bin/env python3
"""
ShopFlow Traffic Generator — sends realistic continuous load to build baseline telemetry.

Runs as a sidecar container (or standalone). Mimics real e-commerce traffic patterns:
  - 60% product browsing (GET /api/products)
  - 20% product detail (GET /api/products/:id)
  - 15% checkout flow (POST /api/orders, preceded by auth)
  - 5%  AI recommendations (POST /api/recommendations)

Continuously runs so FaultLens has baseline data for Z-score normalization.
"""

import asyncio
import random
import time
import logging
import os
import json
import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost:3000")
RPS         = float(os.getenv("REQUESTS_PER_SECOND", "2"))

PRODUCTS = [f"prod_{i:03d}" for i in range(1, 16)]
PRODUCT_NAMES = {
    "prod_001": "MacBook Pro 16\"", "prod_002": "Sony WH-1000XM5",
    "prod_003": "Ergonomic Office Chair", "prod_004": "Standing Desk 160cm",
    "prod_005": "iPhone 15 Pro Max", "prod_006": "Nike Air Max 270",
}

# Tokens cache: {user_id: token}
_tokens: dict[str, str] = {}


async def get_token(client: httpx.AsyncClient, user_id: str) -> str:
    if user_id not in _tokens:
        try:
            r = await client.get(f"{GATEWAY_URL}/auth/token", params={"user_id": user_id}, timeout=5)
            _tokens[user_id] = r.json()["token"]
        except Exception:
            _tokens[user_id] = ""
    return _tokens[user_id]


async def browse_products(client: httpx.AsyncClient):
    await client.get(f"{GATEWAY_URL}/api/products", timeout=5)


async def view_product(client: httpx.AsyncClient):
    pid = random.choice(PRODUCTS)
    await client.get(f"{GATEWAY_URL}/api/products/{pid}", timeout=5)


async def place_order(client: httpx.AsyncClient):
    user_id = f"user_{random.randint(1, 200):04d}"
    token   = await get_token(client, user_id)
    if not token:
        return

    products = random.sample(PRODUCTS, k=random.randint(1, 3))
    items = [{"product_id": p, "quantity": random.randint(1, 2)} for p in products]
    try:
        await client.post(
            f"{GATEWAY_URL}/api/orders",
            json={"items": items},
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
    except httpx.TimeoutException:
        logger.warning("Order request timed out (expected under fault injection)")


async def get_recommendation(client: httpx.AsyncClient):
    pid  = random.choice(list(PRODUCT_NAMES.keys()))
    name = PRODUCT_NAMES.get(pid, pid)
    try:
        await client.post(
            f"{GATEWAY_URL}/api/recommendations",
            json={"product_id": pid, "product_name": name},
            timeout=30,
        )
    except httpx.TimeoutException:
        logger.warning("AI recommendation timed out")


ACTIONS = [
    (browse_products,     60),
    (view_product,        20),
    (place_order,         15),
    (get_recommendation,   5),
]


def pick_action():
    total = sum(w for _, w in ACTIONS)
    r = random.uniform(0, total)
    cumulative = 0
    for action, weight in ACTIONS:
        cumulative += weight
        if r <= cumulative:
            return action
    return ACTIONS[0][0]


async def worker(worker_id: int):
    """Runs traffic in a loop with jitter."""
    async with httpx.AsyncClient(
        base_url=GATEWAY_URL,
        timeout=httpx.Timeout(15.0),
        limits=httpx.Limits(max_connections=20),
    ) as client:
        while True:
            action = pick_action()
            try:
                await action(client)
            except Exception as e:
                logger.debug(f"Worker {worker_id} error ({action.__name__}): {e}")
            await asyncio.sleep(1.0 / RPS + random.uniform(-0.1, 0.3))


async def main():
    logger.info(f"Traffic generator starting → {GATEWAY_URL} at ~{RPS} RPS")

    # Wait for gateway to be ready
    for attempt in range(30):
        try:
            async with httpx.AsyncClient() as c:
                r = await c.get(f"{GATEWAY_URL}/health", timeout=3)
                if r.status_code == 200:
                    logger.info("Gateway is ready ✓")
                    break
        except Exception:
            pass
        logger.info(f"Waiting for gateway... ({attempt+1}/30)")
        await asyncio.sleep(5)

    # Run N workers concurrently to simulate multiple users
    num_workers = max(1, int(RPS * 2))
    logger.info(f"Starting {num_workers} concurrent workers")
    await asyncio.gather(*[worker(i) for i in range(num_workers)])


if __name__ == "__main__":
    asyncio.run(main())
