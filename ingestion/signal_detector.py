"""
Signal Detector — determines the environment type for each service
based on what signals have actually been received.

Logic:
  - If traces are present in Neo4j AND metrics in TimescaleDB → RICH
  - If logs in ES AND traces in Neo4j, but no custom metrics    → MEDIUM
  - If only logs (no traces, no metrics)                        → THIN

The result is persisted in PostgreSQL so agents can read it without
recomputing on every run.
"""

from __future__ import annotations

import logging

from ingestion.models import EnvironmentType
from config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Rolling window for signal presence detection (seconds)
DETECTION_WINDOW = 300  # 5 minutes


async def detect_and_persist(service_id: str) -> EnvironmentType:
    """
    Probe all storage backends to see what signals are present for a service,
    classify the environment, and persist the result to PostgreSQL.
    """
    import storage.timescale as ts_store
    import storage.elasticsearch_client as es_store
    import storage.neo4j_client as neo4j_store
    import storage.postgres_client as pg_store

    has_metrics = False
    has_logs = False
    has_traces = False

    # ── Metrics probe ─────────────────────────────────────────────────────────
    try:
        recent = await ts_store.get_all_metrics_for_service(
            service_id, window_minutes=DETECTION_WINDOW // 60
        )
        has_metrics = len(recent) > 0
    except Exception as e:
        logger.warning(f"Metrics probe failed for {service_id}: {e}")

    # ── Logs probe ────────────────────────────────────────────────────────────
    try:
        count = await es_store.get_error_log_count(
            service_id, window_minutes=DETECTION_WINDOW // 60
        )
        # Also check for any log (not just errors)
        all_logs = await es_store.get_logs_window(
            service_id, window_minutes=DETECTION_WINDOW // 60
        )
        has_logs = len(all_logs) > 0
    except Exception as e:
        logger.warning(f"Logs probe failed for {service_id}: {e}")

    # ── Traces probe ──────────────────────────────────────────────────────────
    try:
        all_services = neo4j_store.get_all_services()
        service_ids = [s["id"] for s in all_services]
        has_traces = service_id in service_ids
    except Exception as e:
        logger.warning(f"Traces probe failed for {service_id}: {e}")

    # ── Classify ──────────────────────────────────────────────────────────────
    if has_metrics and has_traces:
        env_type = EnvironmentType.RICH
    elif has_traces and has_logs:
        env_type = EnvironmentType.MEDIUM
    elif has_logs:
        env_type = EnvironmentType.THIN
    else:
        env_type = EnvironmentType.UNKNOWN

    logger.info(
        f"[SignalDetector] {service_id}: metrics={has_metrics}, "
        f"logs={has_logs}, traces={has_traces} → {env_type}"
    )

    # ── Persist ───────────────────────────────────────────────────────────────
    await pg_store.upsert_service(service_id, name=service_id, env_type=env_type.value)

    return env_type
