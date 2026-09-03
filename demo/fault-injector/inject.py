#!/usr/bin/env python3
"""
ShopFlow Fault Injector — triggers production-grade failure scenarios.

Each scenario mirrors a real failure that happens in production at scale.

Usage:
  python inject.py --scenario redis_stampede
  python inject.py --scenario payment_timeout --latency-ms 8000 --duration 120
  python inject.py --scenario ai_rate_limit --rpm 3 --duration 90
  python inject.py --scenario db_pool_exhaustion --duration 60
  python inject.py --scenario inventory_deadlock --duration 45
  python inject.py --scenario cascade_failure --duration 120
  python inject.py --restore

After injection, wait ~60s and run:
  curl http://localhost:8000/v1/incidents | python -m json.tool
"""

import asyncio
import sys
import time
import random
import click
import httpx
import json

GATEWAY = "http://localhost:3000"
FAULTLENS = "http://localhost:8000"


def log(level: str, msg: str):
    icons = {"INFO": "ℹ️ ", "WARN": "⚠️ ", "ERROR": "❌", "OK": "✅", "EVENT": "🔔"}
    click.echo(f"  {icons.get(level, '')} [{level}] {msg}")


async def wait_for_service(url: str, label: str):
    async with httpx.AsyncClient() as c:
        for _ in range(20):
            try:
                r = await c.get(url, timeout=3)
                if r.status_code < 500:
                    log("OK", f"{label} is reachable")
                    return True
            except Exception:
                pass
            await asyncio.sleep(2)
    log("ERROR", f"{label} not reachable after 40s")
    return False


async def get_auth_token(client: httpx.AsyncClient) -> str:
    r = await client.get(f"{GATEWAY}/auth/token", params={"user_id": "fault_injector"})
    return r.json()["token"]


# ─────────────────────────────────────────────────────────────────────────────
# SCENARIO 1: Redis Cache Stampede
# ─────────────────────────────────────────────────────────────────────────────
async def scenario_redis_stampede(duration: int, **kwargs):
    """
    What happens in production:
      A Redis key expires (or gets flushed during a deploy). Hundreds of concurrent
      requests miss the cache simultaneously and all hit the database. The DB connection
      pool is exhausted within seconds. Services start timing out.

    What FaultLens should detect:
      DB_CONNECTION_POOL_EXHAUSTED on inventory-service
      HIGH_LATENCY_SPIKE on api-gateway (product endpoints)
    """
    log("WARN", f"Scenario: REDIS CACHE STAMPEDE — {duration}s")
    log("INFO", "Step 1: Flushing Redis cache (simulating cache expiry / deploy flush) ...")

    async with httpx.AsyncClient() as client:
        r = await client.post(f"{GATEWAY}/admin/redis/flush", timeout=5)
        log("EVENT", f"Redis flush: {r.json()}")

        log("INFO", "Step 2: Flooding product endpoints with 50 concurrent requests ...")
        start = time.time()
        errors = ok = 0
        while time.time() - start < duration:
            tasks = [
                client.get(f"{GATEWAY}/api/products", timeout=5)
                for _ in range(50)
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for r in results:
                if isinstance(r, Exception):
                    errors += 1
                    log("ERROR", f"Request failed: {type(r).__name__}")
                elif r.status_code == 503:
                    errors += 1
                    log("WARN", f"503 Service Unavailable — DB pool exhausted!")
                elif r.status_code == 200:
                    ok += 1

            log("INFO", f"  Round complete: {ok} OK, {errors} errors so far")
            await asyncio.sleep(2)

        log("OK", f"Stampede complete. {ok} OK, {errors} errors.")


# ─────────────────────────────────────────────────────────────────────────────
# SCENARIO 2: Payment Gateway Timeout
# ─────────────────────────────────────────────────────────────────────────────
async def scenario_payment_timeout(duration: int, latency_ms: int, **kwargs):
    """
    What happens in production:
      Stripe/Adyen has an incident. Payment API takes 8-10s. Your order-service
      has a 5s timeout. Orders fail with 504. Users retry. Retry storm makes it worse.

    What FaultLens should detect:
      HIGH_LATENCY_SPIKE on payment-service
      CASCADE_FAILURE on order-service (504s propagating up)
    """
    log("WARN", f"Scenario: PAYMENT GATEWAY TIMEOUT — latency={latency_ms}ms for {duration}s")

    async with httpx.AsyncClient() as client:
        # Enable latency injection
        r = await client.post(f"{GATEWAY}/admin/payment/set-latency",
                              json={"latency_ms": latency_ms, "failure_rate": 0.05},
                              timeout=5)
        log("EVENT", f"Payment config: {r.json()}")
        log("INFO", "Sending concurrent order requests ...")

        token = await get_auth_token(client)
        headers = {"Authorization": f"Bearer {token}"}
        start = time.time()
        timeouts = ok = errors = 0

        while time.time() - start < duration:
            tasks = [
                client.post(
                    f"{GATEWAY}/api/orders",
                    json={"items": [{"product_id": random.choice(["prod_001","prod_002","prod_006"]),
                                     "quantity": 1}]},
                    headers=headers,
                    timeout=15,
                )
                for _ in range(10)
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for r in results:
                if isinstance(r, Exception):
                    timeouts += 1
                    log("WARN", f"Client-side timeout: {type(r).__name__}")
                elif r.status_code == 504:
                    timeouts += 1
                    log("ERROR", f"504 Gateway Timeout — payment cascade!")
                elif r.status_code in (201, 200):
                    ok += 1
                else:
                    errors += 1

            log("INFO", f"  {ok} OK, {timeouts} timeouts, {errors} errors")
            await asyncio.sleep(5)

        # Restore
        await client.post(f"{GATEWAY}/admin/payment/set-latency",
                          json={"latency_ms": 0, "failure_rate": 0.03}, timeout=5)
        log("OK", f"Payment latency cleared. Final: {ok} OK, {timeouts} timeouts.")


# ─────────────────────────────────────────────────────────────────────────────
# SCENARIO 3: AI Rate Limit Exhaustion
# ─────────────────────────────────────────────────────────────────────────────
async def scenario_ai_rate_limit(duration: int, rpm: int, **kwargs):
    """
    What happens in production:
      Your app makes too many LLM API calls (OpenAI/Anthropic rate limits hit).
      Recommendation endpoint gets hammered during a sale. 429s everywhere.

    What FaultLens should detect:
      AI_RATE_LIMIT_EXCEEDED on ai-service
      HTTP error spike visible in logs (429 pattern)
    """
    log("WARN", f"Scenario: AI RATE LIMIT EXCEEDED — {rpm} RPM for {duration}s")

    async with httpx.AsyncClient() as client:
        r = await client.post(f"{GATEWAY}/admin/ai/rate-limit/enable",
                              json={"rpm": rpm}, timeout=5)
        log("EVENT", f"Rate limit enabled: {r.json()}")

        start = time.time()
        ok = rate_limited = 0
        products = ["prod_001", "prod_002", "prod_005", "prod_009", "prod_010"]
        product_names = {
            "prod_001": "MacBook Pro 16\"", "prod_002": "Sony WH-1000XM5",
            "prod_005": "iPhone 15 Pro Max",
        }

        while time.time() - start < duration:
            # Simulate burst of recommendation requests (flash sale traffic)
            tasks = [
                client.post(f"{GATEWAY}/api/recommendations", json={
                    "product_id": random.choice(products),
                    "product_name": product_names.get(random.choice(products), "product"),
                }, timeout=35)
                for _ in range(15)
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for r in results:
                if isinstance(r, Exception):
                    pass
                elif r.status_code == 429:
                    rate_limited += 1
                    log("ERROR", f"429 Too Many Requests ← FaultLens target!")
                elif r.status_code == 200:
                    ok += 1

            log("INFO", f"  {ok} OK, {rate_limited} rate-limited")
            await asyncio.sleep(2)

        await client.post(f"{GATEWAY}/admin/ai/rate-limit/disable", timeout=5)
        log("OK", f"Rate limit cleared. {ok} OK, {rate_limited} rate-limited.")


# ─────────────────────────────────────────────────────────────────────────────
# SCENARIO 4: DB Connection Pool Exhaustion
# ─────────────────────────────────────────────────────────────────────────────
async def scenario_db_pool_exhaustion(duration: int, **kwargs):
    """
    What happens in production:
      An expensive query (report, migration, analytics) runs and holds DB connections.
      Or a traffic spike overwhelms the connection pool (max=10).
      New requests queue up, then timeout after connectionTimeoutMillis.

    What FaultLens should detect:
      DB_CONNECTION_POOL_EXHAUSTED on inventory-service or order-service
    """
    log("WARN", f"Scenario: DB CONNECTION POOL EXHAUSTION — {duration}s")
    log("INFO", "Starting slow queries to hold DB connections (max pool=10) ...")

    async with httpx.AsyncClient() as client:
        # Fire slow queries that each hold a DB connection for 8s
        slow_query_tasks = [
            client.post("http://localhost:3002/admin/slow-query",
                        json={"duration_ms": duration * 1000}, timeout=duration + 5)
            for _ in range(12)  # more than pool max
        ]
        asyncio.gather(*slow_query_tasks, return_exceptions=True)  # don't await, run in bg

        await asyncio.sleep(2)  # let slow queries get connections first

        log("INFO", "Now sending normal requests — they should fail (pool exhausted) ...")
        start = time.time()
        ok = pool_errors = 0

        while time.time() - start < duration:
            tasks = [
                client.get(f"{GATEWAY}/api/products", timeout=5)
                for _ in range(20)
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for r in results:
                if isinstance(r, Exception):
                    pool_errors += 1
                    log("ERROR", f"Request failed: {type(r).__name__}")
                elif r.status_code in (503, 500):
                    pool_errors += 1
                    log("ERROR", f"{r.status_code} — pool exhausted response!")
                else:
                    ok += 1
            log("INFO", f"  {ok} OK, {pool_errors} pool-exhaustion errors")
            await asyncio.sleep(3)

        log("OK", f"Pool exhaustion scenario ended. {ok} OK, {pool_errors} errors.")


# ─────────────────────────────────────────────────────────────────────────────
# SCENARIO 5: Inventory Deadlock
# ─────────────────────────────────────────────────────────────────────────────
async def scenario_inventory_deadlock(duration: int, **kwargs):
    """
    What happens in production:
      Flash sale — thousands of users compete to buy the last units of a hot product.
      Concurrent transactions each try to lock the same product row.
      Postgres detects deadlock, rolls back one transaction.
      The rolled-back request retries, creating more deadlocks.

    What FaultLens should detect:
      DB_QUERY_TIMEOUT / inventory deadlock pattern in logs
      High error rate on inventory-service reserve endpoint
    """
    log("WARN", f"Scenario: INVENTORY DEADLOCK (Flash Sale Simulation) — {duration}s")
    log("INFO", "Bombarding reservation endpoint for same product concurrently ...")

    async with httpx.AsyncClient() as client:
        token = await get_auth_token(client)
        start = time.time()
        ok = deadlocks = errors = 0

        while time.time() - start < duration:
            # All requests compete for the SAME hot product (realistic flash sale)
            tasks = [
                client.post(
                    f"{GATEWAY}/api/orders",
                    json={"items": [{"product_id": "prod_005", "quantity": 1}]},
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=10,
                )
                for _ in range(20)
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for r in results:
                if isinstance(r, Exception):
                    errors += 1
                elif r.status_code == 409:
                    body = r.json()
                    if body.get("detail") == "deadlock":
                        deadlocks += 1
                        log("ERROR", "DEADLOCK detected — Postgres rolled back a transaction!")
                    else:
                        log("WARN", f"Conflict: {body.get('error')}")
                        errors += 1
                elif r.status_code in (201, 200):
                    ok += 1
                else:
                    errors += 1

            log("INFO", f"  {ok} orders OK, {deadlocks} deadlocks, {errors} other errors")
            await asyncio.sleep(1)

        log("OK", f"Deadlock scenario ended. {ok} OK, {deadlocks} deadlocks.")


# ─────────────────────────────────────────────────────────────────────────────
# SCENARIO 6: Cascade Failure
# ─────────────────────────────────────────────────────────────────────────────
async def scenario_cascade_failure(duration: int, **kwargs):
    """
    What happens in production:
      inventory-service goes down (OOM, crash, deploy gone wrong).
      order-service can't validate stock → all new orders fail.
      api-gateway sees 502 Bad Gateway on all order endpoints.
      Users can still browse (product catalog from cache) but can't buy.

    What FaultLens should detect:
      CASCADE_FAILURE on order-service / api-gateway
      UPSTREAM_DEPENDENCY_FAILURE on inventory-service
    """
    log("WARN", f"Scenario: CASCADE FAILURE — {duration}s")
    log("INFO", "Injecting extreme latency on payment AND enabling high failure rate ...")

    async with httpx.AsyncClient() as client:
        # Max out payment latency AND failure rate to cascade through orders
        await client.post(f"{GATEWAY}/admin/payment/set-latency",
                          json={"latency_ms": 10_000, "failure_rate": 0.90}, timeout=5)

        # Also flush Redis so inventory cache misses hit the (now overwhelmed) DB
        await client.post(f"{GATEWAY}/admin/redis/flush", timeout=5)
        log("EVENT", "Payment: 10s latency + 90% failure rate. Redis: flushed.")

        token = await get_auth_token(client)
        headers = {"Authorization": f"Bearer {token}"}

        start = time.time()
        browsing_ok = order_failures = 0

        while time.time() - start < duration:
            # Browse requests still work (cache serves them) — only orders fail
            browse_tasks = [client.get(f"{GATEWAY}/api/products", timeout=5) for _ in range(5)]
            order_tasks  = [
                client.post(f"{GATEWAY}/api/orders",
                            json={"items": [{"product_id": "prod_001", "quantity": 1}]},
                            headers=headers, timeout=15)
                for _ in range(5)
            ]
            all_results = await asyncio.gather(*browse_tasks, *order_tasks, return_exceptions=True)
            for i, r in enumerate(all_results):
                if isinstance(r, Exception):
                    if i >= 5:
                        order_failures += 1
                        log("ERROR", f"Order request failed: {type(r).__name__}")
                elif r.status_code == 200 and i < 5:
                    browsing_ok += 1
                elif r.status_code >= 400 and i >= 5:
                    order_failures += 1
                    log("ERROR", f"Order {r.status_code}: {r.json().get('error', '')[:50]}")

            log("INFO", f"  Browse: {browsing_ok} OK | Orders: {order_failures} failed (cascade)")
            await asyncio.sleep(5)

        # Restore
        await client.post(f"{GATEWAY}/admin/payment/set-latency",
                          json={"latency_ms": 0, "failure_rate": 0.03}, timeout=5)
        log("OK", f"Cascade restored. Orders failed: {order_failures}.")


# ─────────────────────────────────────────────────────────────────────────────
# Restore all
# ─────────────────────────────────────────────────────────────────────────────
async def restore_all():
    log("INFO", "Restoring all injected faults ...")
    async with httpx.AsyncClient() as client:
        await client.post(f"{GATEWAY}/admin/payment/set-latency",
                          json={"latency_ms": 0, "failure_rate": 0.03}, timeout=5)
        await client.post(f"{GATEWAY}/admin/ai/rate-limit/disable", timeout=5)
        log("OK", "All faults cleared.")


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────
async def scenario_rolling_chaos(duration: int, interval: int = 90, **kwargs):
    """
    Realistic continuous incidents: 1-2 faults emerge periodically over time (every ~90s),
    last for 35s, self-heal, and repeat.
    """
    log("WARN", f"Scenario: ROLLING REALISTIC CHAOS (errors emerge time to time, max 2 at once) — {duration}s")
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{GATEWAY}/chaos/start-rolling", json={"interval_seconds": interval}, timeout=10)
        log("EVENT", f"Engine started: {r.json().get('message')}")
        log("INFO", f"ShopFlow will now experience organic, periodic 1-2 fault waves for {duration}s...")
        await asyncio.sleep(duration)
        log("INFO", "Stopping rolling chaos engine...")
        await client.post(f"{GATEWAY}/chaos/stop-rolling", timeout=10)
        log("OK", "Rolling chaos stopped and system restored.")

async def scenario_incident_wave(duration: int = 35, **kwargs):
    """
    Triggers a single realistic incident wave affecting at most 2 services that auto-heals after 35s.
    """
    log("WARN", f"Scenario: SINGLE REALISTIC INCIDENT WAVE (2 services affected, auto-heals in {duration}s)")
    async with httpx.AsyncClient() as client:
        r = await client.post(f"{GATEWAY}/chaos/wave", json={"duration": duration}, timeout=10)
        data = r.json()
        log("EVENT", f"Wave active: {data.get('wave')} — {data.get('description')}")
        log("INFO", f"Observing wave for {duration}s...")
        await asyncio.sleep(duration + 2)
        log("OK", "Wave completed and self-healed automatically.")

SCENARIOS = {
    "rolling_chaos":       scenario_rolling_chaos,
    "incident_wave":       scenario_incident_wave,
    "payment_timeout":     scenario_payment_timeout,
    "redis_stampede":      scenario_redis_stampede,
    "ai_rate_limit":       scenario_ai_rate_limit,
    "inventory_deadlock":  scenario_inventory_deadlock,
    "db_pool_exhaustion":  scenario_db_pool_exhaustion,
}

SCENARIO_DESCRIPTIONS = {
    "rolling_chaos":       "🌊 REALISTIC CONTINUOUS: 1-2 faults emerge periodically over time, self-heal, repeat",
    "incident_wave":       "⚡ SINGLE WAVE: 2 correlated faults hit, system degrades for 35s, then self-heals",
    "payment_timeout":     "Payment processor slow (5.5s) → checkout 504 timeouts (payment + orders)",
    "redis_stampede":      "Cache drop → thundering herd query spike (inventory + postgres)",
    "ai_rate_limit":       "AI recommendation service token quota throttle (ai-service 429s)",
    "inventory_deadlock":  "Flash sale concurrent reservations → Postgres row lock deadlocks",
    "db_pool_exhaustion":  "Slow queries hold connections → pool maxed → 503s",
}


@click.command()
@click.option("--scenario", "-s", type=click.Choice(list(SCENARIOS.keys())),
              help="Fault scenario to inject")
@click.option("--duration", "-d", default=90, show_default=True,
              help="Duration in seconds")
@click.option("--latency-ms", default=8000, show_default=True,
              help="Latency to inject (payment_timeout)")
@click.option("--rpm", default=3, show_default=True,
              help="Rate limit RPM (ai_rate_limit)")
@click.option("--restore", is_flag=True, help="Restore all faults and exit")
@click.option("--list-scenarios", is_flag=True, help="List all available scenarios")
def main(scenario, duration, latency_ms, rpm, restore, list_scenarios):
    """
    ShopFlow Fault Injector — trigger production-grade failure scenarios.

    \b
    After injecting, FaultLens should detect the anomaly within ~60s.
    Check: curl http://localhost:8000/v1/incidents | python -m json.tool
    """
    if list_scenarios:
        click.echo("\nAvailable fault scenarios:\n")
        for name, desc in SCENARIO_DESCRIPTIONS.items():
            click.echo(f"  {name:30s} {desc}")
        click.echo()
        return

    async def _run():
        if restore:
            await restore_all()
            return

        if not scenario:
            click.echo("Error: --scenario required. Use --list-scenarios to see options.", err=True)
            return

        click.echo(f"\n{'='*65}")
        click.echo(f"  ShopFlow Fault Injector")
        click.echo(f"  Scenario : {scenario}")
        click.echo(f"  Duration : {duration}s")
        click.echo(f"  Description: {SCENARIO_DESCRIPTIONS[scenario]}")
        click.echo(f"{'='*65}\n")

        ok = await wait_for_service(f"{GATEWAY}/health", "ShopFlow API Gateway")
        if not ok:
            click.echo("Gateway not reachable. Is the demo running?", err=True)
            return

        fn = SCENARIOS[scenario]
        await fn(duration=duration, latency_ms=latency_ms, rpm=rpm)

        click.echo(f"\n{'='*65}")
        click.echo(f"✅ Scenario complete.")
        click.echo(f"   FaultLens should detect anomalies within ~60s.")
        click.echo(f"   Run: curl {FAULTLENS}/v1/incidents | python -m json.tool")
        click.echo(f"{'='*65}\n")

    asyncio.run(_run())


if __name__ == "__main__":
    main()
