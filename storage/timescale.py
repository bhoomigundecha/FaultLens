"""
TimescaleDB client — stores normalized metrics as a hypertable.

All writes go through `insert_metric()`.
Reads (for anomaly detection) go through `get_metric_window()` and
`get_baseline_stats()`.
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

import asyncpg

from config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Module-level connection pool (lazily initialised)
_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        # Strip the SQLAlchemy dialect prefix so asyncpg is happy
        dsn = settings.timescale_sync_url.replace(
            "postgresql+asyncpg://", "postgresql://"
        ).replace("postgresql+psycopg2://", "postgresql://")
        _pool = await asyncpg.create_pool(dsn, min_size=2, max_size=10)
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


# ─── Schema ───────────────────────────────────────────────────────────────────

CREATE_METRICS_TABLE = """
CREATE TABLE IF NOT EXISTS metrics (
    time            TIMESTAMPTZ     NOT NULL,
    service_id      TEXT            NOT NULL,
    metric_name     TEXT            NOT NULL,
    value           DOUBLE PRECISION NOT NULL,
    unit            TEXT,
    labels          JSONB           DEFAULT '{}'
);
"""

CREATE_HYPERTABLE = """
SELECT create_hypertable('metrics', 'time', if_not_exists => TRUE);
"""

CREATE_METRICS_INDEX = """
CREATE INDEX IF NOT EXISTS idx_metrics_service_metric
    ON metrics (service_id, metric_name, time DESC);
"""

COMPRESSION_POLICY = """
SELECT add_compression_policy('metrics', INTERVAL '7 days', if_not_exists => TRUE);
"""


async def init_schema(pool: asyncpg.Pool) -> None:
    """Create hypertable and indexes. Idempotent."""
    async with pool.acquire() as conn:
        await conn.execute(CREATE_METRICS_TABLE)
        await conn.execute(CREATE_HYPERTABLE)
        await conn.execute(CREATE_METRICS_INDEX)
        try:
            await conn.execute(COMPRESSION_POLICY)
        except Exception:
            # Compression requires TimescaleDB enterprise on some versions; skip gracefully
            logger.warning("Skipping compression policy (may require TimescaleDB licence)")
    logger.info("TimescaleDB schema initialised")


# ─── Writes ───────────────────────────────────────────────────────────────────

async def insert_metric(
    service_id: str,
    metric_name: str,
    value: float,
    *,
    unit: str = "",
    labels: dict[str, Any] | None = None,
    timestamp: datetime | None = None,
) -> None:
    """Insert a single metric data point."""
    import json

    pool = await get_pool()
    ts = timestamp or datetime.now(timezone.utc)
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO metrics (time, service_id, metric_name, value, unit, labels)
            VALUES ($1, $2, $3, $4, $5, $6::jsonb)
            """,
            ts,
            service_id,
            metric_name,
            value,
            unit,
            json.dumps(labels or {}),
        )


async def insert_metrics_batch(rows: list[dict[str, Any]]) -> None:
    """Bulk-insert a list of metric dicts for efficiency."""
    import json

    pool = await get_pool()
    records = [
        (
            r.get("timestamp") or datetime.now(timezone.utc),
            r["service_id"],
            r["metric_name"],
            float(r["value"]),
            r.get("unit", ""),
            json.dumps(r.get("labels", {})),
        )
        for r in rows
    ]
    async with pool.acquire() as conn:
        await conn.executemany(
            """
            INSERT INTO metrics (time, service_id, metric_name, value, unit, labels)
            VALUES ($1, $2, $3, $4, $5, $6::jsonb)
            """,
            records,
        )


# ─── Reads ────────────────────────────────────────────────────────────────────

async def get_metric_window(
    service_id: str,
    metric_name: str,
    window_minutes: int = 15,
) -> list[dict[str, Any]]:
    """Return all data points for a metric in the last `window_minutes`."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT time, value, labels
            FROM   metrics
            WHERE  service_id  = $1
              AND  metric_name = $2
              AND  time        > NOW() - ($3 || ' minutes')::INTERVAL
            ORDER  BY time ASC
            """,
            service_id,
            metric_name,
            str(window_minutes),
        )
    return [dict(r) for r in rows]


async def get_baseline_stats(
    service_id: str,
    metric_name: str,
    baseline_hours: int = 24,
) -> dict[str, float]:
    """Return mean and stddev over the last `baseline_hours` as the normal baseline."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT
                AVG(value)    AS mean,
                STDDEV(value) AS stddev,
                MIN(value)    AS min,
                MAX(value)    AS max,
                COUNT(*)      AS count
            FROM   metrics
            WHERE  service_id  = $1
              AND  metric_name = $2
              AND  time        > NOW() - ($3 || ' hours')::INTERVAL
            """,
            service_id,
            metric_name,
            str(baseline_hours),
        )
    if row is None or row["count"] == 0:
        return {"mean": 0.0, "stddev": 0.0, "min": 0.0, "max": 0.0, "count": 0}
    return {k: float(v or 0) for k, v in dict(row).items()}


async def get_services_with_recent_metrics(lookback_seconds: int = 120) -> list[str]:
    """Return service IDs that have pushed metrics recently (for the agent worker)."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT DISTINCT service_id
            FROM   metrics
            WHERE  time > NOW() - ($1 || ' seconds')::INTERVAL
            """,
            str(lookback_seconds),
        )
    return [r["service_id"] for r in rows]


async def get_all_metrics_for_service(
    service_id: str, window_minutes: int = 15
) -> dict[str, list[float]]:
    """Return all metric names → value lists for a service in the time window."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT metric_name, value
            FROM   metrics
            WHERE  service_id = $1
              AND  time > NOW() - ($2 || ' minutes')::INTERVAL
            ORDER  BY time ASC
            """,
            service_id,
            str(window_minutes),
        )
    result: dict[str, list[float]] = {}
    for r in rows:
        result.setdefault(r["metric_name"], []).append(r["value"])
    return result
