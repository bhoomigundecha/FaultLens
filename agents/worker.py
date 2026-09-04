"""
Agent Worker — the scheduled process that drives the LangGraph workflow.

Runs as a long-lived process (python -m agents.worker).
Every AGENT_POLL_INTERVAL_SECONDS:
  1. Query TimescaleDB for services that pushed metrics recently
  2. For each service, fuse available signals to get a candidate score
  3. If fused_score >= threshold → trigger the full LangGraph workflow
  4. Persist run metadata to PostgreSQL

Uses LangGraph's AsyncPostgresSaver for state checkpointing.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone

import psycopg
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

import storage.timescale as ts_store
import storage.elasticsearch_client as es_store
import storage.postgres_client as pg_store
import storage.neo4j_client as neo4j_store
from agents.graph import build_graph
from agents.state import initial_state, FaultLensState
from ml.anomaly_detection import run_zscore
from ml.fusion import fuse_scores, ANOMALY_THRESHOLD
from config.settings import get_settings
from pipeline.producer import ensure_topics_exist
from storage.init_schemas import init_all as init_schemas

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)
settings = get_settings()


# ─── Quick anomaly pre-screen ─────────────────────────────────────────────────

async def _quick_screen(service_id: str) -> float:
    """
    Fast pre-screening before triggering full agent workflow.
    Returns a fused anomaly score [0, 1].
    Avoids running the full graph for healthy services.
    """
    metric_score: float | None = None
    log_score:    float | None = None

    # Metric Z-score on most recent values
    try:
        all_metrics = await ts_store.get_all_metrics_for_service(
            service_id, window_minutes=settings.metric_window_minutes
        )
        scores = []
        for mname, values in all_metrics.items():
            if len(values) < 3:
                continue
            results = run_zscore(service_id, mname, values[-20:])  # last 20 points
            worst = max((r.score for r in results if r.is_anomaly), default=0.0)
            scores.append(worst)
        metric_score = max(scores) if scores else 0.0
    except Exception:
        pass

    # Error log count as proxy
    try:
        err_count = await es_store.get_error_log_count(
            service_id, window_minutes=settings.metric_window_minutes
        )
        log_score = min(1.0, err_count / 10.0)  # >10 errors in window → score=1.0
    except Exception:
        pass

    svc = await pg_store.get_service(service_id)
    env_type = svc["env_type"] if svc else "unknown"

    fused = fuse_scores(service_id, env_type, metric_score, log_score, None)
    return fused.fused_score


# ─── Main polling loop ────────────────────────────────────────────────────────

async def run_worker() -> None:
    logger.info("FaultLens Agent Worker starting …")

    # ── One-time setup ────────────────────────────────────────────────────────
    try:
        await init_schemas()
    except Exception as e:
        logger.warning(f"Schema init warning (may already exist): {e}")

    try:
        ensure_topics_exist()
    except Exception as e:
        logger.warning(f"Topic creation warning: {e}")

    # ── Build graph with Postgres checkpointer ────────────────────────────────
    # autocommit=True is required: LangGraph's checkpointer.setup() runs
    # `CREATE INDEX CONCURRENTLY` which PostgreSQL forbids inside a transaction.
    conn_string = settings.postgres_sync_url
    conn = await psycopg.AsyncConnection.connect(conn_string, autocommit=True)
    try:
        checkpointer = AsyncPostgresSaver(conn)
        await checkpointer.setup()  # creates langgraph checkpoint tables
        graph = build_graph(checkpointer=checkpointer)

        logger.info(
            f"Worker ready. Polling every {settings.agent_poll_interval_seconds}s, "
            f"anomaly threshold={ANOMALY_THRESHOLD}"
        )

        while True:
            try:
                await _poll_cycle(graph)
            except Exception as e:
                logger.exception(f"Poll cycle error: {e}")

            await asyncio.sleep(settings.agent_poll_interval_seconds)
    finally:
        await conn.close()


async def _poll_cycle(graph) -> None:
    """One poll cycle: screen all active services, trigger workflows for anomalous ones."""
    # Get services active in the last N seconds
    active_services = await ts_store.get_services_with_recent_metrics(
        lookback_seconds=settings.anomaly_lookback_seconds
    )

    # Also include services registered in PG that may only have logs (thin env)
    pg_services = await pg_store.get_all_services()
    thin_services = [s["service_id"] for s in pg_services if s["env_type"] == "thin"]
    all_services = list(set(active_services + thin_services))

    if not all_services:
        logger.debug("No active services in current window, sleeping …")
        return

    logger.info(f"Screening {len(all_services)} active service(s) …")

    for service_id in all_services:
        try:
            score = await _quick_screen(service_id)
            logger.debug(f"  {service_id}: pre-screen score={score:.3f}")

            if score >= ANOMALY_THRESHOLD:
                logger.info(
                    f"🚨 ANOMALY DETECTED: {service_id} (score={score:.3f}) — triggering workflow"
                )
                await _trigger_workflow(graph, service_id)
            else:
                logger.debug(f"  {service_id}: healthy (score={score:.3f} < threshold)")

        except Exception as e:
            logger.exception(f"Error screening {service_id}: {e}")


async def _trigger_workflow(graph, service_id: str) -> None:
    """Create an incident record and invoke the LangGraph graph for the service."""
    incident_id = str(uuid.uuid4())

    # Create skeleton incident in PG
    await pg_store.create_incident(incident_id, service_id)
    run_id = await pg_store.start_agent_run(service_id, incident_id)

    start_state = initial_state(service_id=service_id, incident_id=incident_id)
    config = {"configurable": {"thread_id": incident_id}}

    nodes_executed: list[str] = []
    error: str | None = None

    try:
        async for event in graph.astream(start_state, config=config):
            for node_name, node_output in event.items():
                nodes_executed.append(node_name)
                if isinstance(node_output, dict):
                    executed = node_output.get("nodes_executed", [])
                    logger.info(f"  ✓ {node_name} completed (executed={executed})")

        logger.info(f"✅ Workflow complete for incident {incident_id}")
        await pg_store.finish_agent_run(run_id, "success", nodes_executed)

    except Exception as e:
        error = str(e)
        logger.exception(f"Workflow failed for incident {incident_id}: {e}")
        await pg_store.finish_agent_run(run_id, "failed", nodes_executed, error=error)
        await pg_store.update_incident(incident_id, {"status": "error"})


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    asyncio.run(run_worker())
