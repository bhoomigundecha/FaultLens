"""
PostgreSQL client — stores:
  1. services    : registered services and their detected environment type
  2. incidents   : completed RCA reports (structured)
  3. agent_runs  : per-run agent execution metadata (for observability)

Note: LangGraph's Postgres checkpointer manages its own tables automatically.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

import asyncpg

from config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        dsn = settings.postgres_sync_url.replace(
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

CREATE_SERVICES_TABLE = """
CREATE TABLE IF NOT EXISTS services (
    service_id      TEXT PRIMARY KEY,
    name            TEXT        NOT NULL,
    env_type        TEXT        NOT NULL DEFAULT 'unknown',
    first_seen      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

CREATE_INCIDENTS_TABLE = """
CREATE TABLE IF NOT EXISTS incidents (
    incident_id     TEXT PRIMARY KEY,
    service_id      TEXT        NOT NULL,
    failure_type    TEXT,
    confidence      REAL,
    ranked_suspects JSONB       DEFAULT '[]',
    environment_type TEXT,
    metric_anomalies JSONB      DEFAULT '[]',
    log_anomalies   JSONB       DEFAULT '[]',
    trace_anomalies JSONB       DEFAULT '[]',
    causal_path     JSONB       DEFAULT '[]',
    rca_report      TEXT,
    team_routing    TEXT,
    status          TEXT        NOT NULL DEFAULT 'open',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at     TIMESTAMPTZ
);
"""

CREATE_AGENT_RUNS_TABLE = """
CREATE TABLE IF NOT EXISTS agent_runs (
    run_id          TEXT PRIMARY KEY,
    service_id      TEXT,
    incident_id     TEXT,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    finished_at     TIMESTAMPTZ,
    status          TEXT        NOT NULL DEFAULT 'running',
    nodes_executed  JSONB       DEFAULT '[]',
    error           TEXT
);
"""


async def init_schema(pool: asyncpg.Pool) -> None:
    async with pool.acquire() as conn:
        await conn.execute(CREATE_SERVICES_TABLE)
        await conn.execute(CREATE_INCIDENTS_TABLE)
        await conn.execute(CREATE_AGENT_RUNS_TABLE)
    logger.info("PostgreSQL schema initialised")


# ─── Services ─────────────────────────────────────────────────────────────────

async def upsert_service(
    service_id: str, name: str, env_type: str = "unknown"
) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO services (service_id, name, env_type, last_seen)
            VALUES ($1, $2, $3, NOW())
            ON CONFLICT (service_id) DO UPDATE
                SET name     = EXCLUDED.name,
                    env_type = EXCLUDED.env_type,
                    last_seen = NOW()
            """,
            service_id,
            name,
            env_type,
        )


async def get_service(service_id: str) -> dict[str, Any] | None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM services WHERE service_id = $1", service_id
        )
    return dict(row) if row else None


async def get_all_services() -> list[dict[str, Any]]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM services ORDER BY last_seen DESC")
    return [dict(r) for r in rows]


# ─── Incidents ────────────────────────────────────────────────────────────────

async def create_incident(incident_id: str, service_id: str) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO incidents (incident_id, service_id) VALUES ($1, $2) ON CONFLICT DO NOTHING",
            incident_id,
            service_id,
        )


async def update_incident(incident_id: str, updates: dict[str, Any]) -> None:
    """Partial update — only sets fields present in `updates`."""
    if not updates:
        return
    pool = await get_pool()

    # Serialise JSONB columns
    jsonb_cols = {
        "ranked_suspects", "metric_anomalies", "log_anomalies",
        "trace_anomalies", "causal_path",
    }
    set_clauses = []
    values = []
    for i, (col, val) in enumerate(updates.items(), start=2):
        if col in jsonb_cols:
            set_clauses.append(f"{col} = ${i}::jsonb")
            values.append(json.dumps(val))
        else:
            set_clauses.append(f"{col} = ${i}")
            values.append(val)

    query = f"UPDATE incidents SET {', '.join(set_clauses)} WHERE incident_id = $1"
    async with pool.acquire() as conn:
        await conn.execute(query, incident_id, *values)


async def get_incident(incident_id: str) -> dict[str, Any] | None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM incidents WHERE incident_id = $1", incident_id
        )
    return dict(row) if row else None


async def list_recent_incidents(
    service_id: str | None = None, limit: int = 20
) -> list[dict[str, Any]]:
    pool = await get_pool()
    if service_id:
        query = (
            "SELECT * FROM incidents WHERE service_id = $1 ORDER BY created_at DESC LIMIT $2"
        )
        args = [service_id, limit]
    else:
        query = "SELECT * FROM incidents ORDER BY created_at DESC LIMIT $1"
        args = [limit]
    async with pool.acquire() as conn:
        rows = await conn.fetch(query, *args)
    return [dict(r) for r in rows]


# ─── Agent Runs ───────────────────────────────────────────────────────────────

async def start_agent_run(service_id: str, incident_id: str) -> str:
    run_id = str(uuid.uuid4())
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO agent_runs (run_id, service_id, incident_id) VALUES ($1, $2, $3)",
            run_id,
            service_id,
            incident_id,
        )
    return run_id


async def finish_agent_run(
    run_id: str,
    status: str,
    nodes_executed: list[str],
    error: str | None = None,
) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE agent_runs
            SET status = $2, finished_at = NOW(),
                nodes_executed = $3::jsonb, error = $4
            WHERE run_id = $1
            """,
            run_id,
            status,
            json.dumps(nodes_executed),
            error,
        )
