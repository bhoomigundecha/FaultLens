"""
Anomaly Hunter Agent — Node 2 in the LangGraph workflow (rich/medium path).

Responsibilities:
  1. Pull metrics window from TimescaleDB
  2. Run Z-score per metric
  3. Run multivariate Isolation Forest across all metrics
  4. Pull log window from Elasticsearch
  5. Run DRAIN3 + frequency anomaly detection on logs
  6. Fuse scores using environment-aware weights
  7. Update state with metric_anomalies, log_anomalies, fused_score
"""

from __future__ import annotations

import logging
from typing import Any

import storage.timescale as ts_store
import storage.elasticsearch_client as es_store
from agents.state import FaultLensState
from ml.anomaly_detection import run_zscore, run_isolation_forest
from ml.log_clustering import parse_logs_batch, detect_log_anomalies
from ml.fusion import fuse_scores
from config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def anomaly_hunter_node(state: FaultLensState) -> dict[str, Any]:
    """LangGraph node: detect metric and log anomalies."""
    service_id = state["service_id"]
    env_type   = state["environment_type"]
    logger.info(f"[AnomalyHunter] Running for {service_id} (env={env_type})")

    metric_anomalies: list[dict] = []
    log_anomalies:    list[dict] = []
    metric_score: float | None = None
    log_score:    float | None = None

    # ── Metrics analysis ──────────────────────────────────────────────────────
    try:
        all_metrics = await ts_store.get_all_metrics_for_service(
            service_id, window_minutes=settings.metric_window_minutes
        )

        if all_metrics:
            per_metric_max_scores: list[float] = []

            for metric_name, values in all_metrics.items():
                if len(values) < 3:
                    continue
                results = run_zscore(service_id, metric_name, values)
                anomalous = [r for r in results if r.is_anomaly]
                if anomalous:
                    worst = max(anomalous, key=lambda r: r.score)
                    metric_anomalies.append({
                        "metric_name":   worst.metric_name,
                        "value":         worst.value,
                        "score":         worst.score,
                        "z_score":       worst.z_score,
                        "baseline_mean": worst.baseline_mean,
                        "evidence":      worst.evidence,
                    })
                    per_metric_max_scores.append(worst.score)

            # Multivariate Isolation Forest
            metric_names = list(all_metrics.keys())
            # Build feature matrix: each row = one time step's values across all metrics
            max_len = max(len(v) for v in all_metrics.values())
            feature_matrix = []
            for i in range(max_len):
                row = [all_metrics[m][i] if i < len(all_metrics[m]) else 0.0 for m in metric_names]
                feature_matrix.append(row)

            if_result = run_isolation_forest(service_id, metric_names, feature_matrix)
            if if_result and if_result.is_anomaly:
                metric_anomalies.append({
                    "type":           "multivariate_isolation_forest",
                    "score":          if_result.score,
                    "anomalous_dims": if_result.anomalous_dims,
                    "evidence":       if_result.evidence,
                })
                per_metric_max_scores.append(if_result.score)

            metric_score = max(per_metric_max_scores) if per_metric_max_scores else 0.0

    except Exception as e:
        logger.exception(f"[AnomalyHunter] Metrics analysis failed for {service_id}: {e}")

    # ── Log anomaly analysis ───────────────────────────────────────────────────
    try:
        raw_logs = await es_store.get_logs_window(
            service_id, window_minutes=settings.metric_window_minutes
        )
        if raw_logs:
            bodies = [log.get("body", "") for log in raw_logs]
            parsed = parse_logs_batch(bodies)
            log_anom_results = detect_log_anomalies(service_id, parsed)

            for r in log_anom_results:
                log_anomalies.append({
                    "template_id": r.template_id,
                    "template":    r.template,
                    "count":       r.count,
                    "score":       r.score,
                    "reason":      r.reason,
                })

            log_score = max((r.score for r in log_anom_results), default=0.0) if log_anom_results else 0.0

    except Exception as e:
        logger.exception(f"[AnomalyHunter] Log analysis failed for {service_id}: {e}")

    # ── Fuse ──────────────────────────────────────────────────────────────────
    fused = fuse_scores(
        service_id=service_id,
        env_type=env_type,
        metric_score=metric_score,
        log_score=log_score,
        trace_score=None,   # trace anomalies added by GraphWeaver
    )

    logger.info(
        f"[AnomalyHunter] {service_id}: {len(metric_anomalies)} metric anomalies, "
        f"{len(log_anomalies)} log anomalies, fused={fused.fused_score:.3f}"
    )

    return {
        "metric_anomalies": metric_anomalies,
        "log_anomalies":    log_anomalies,
        "fused_score":      fused.fused_score,
        "fused_evidence":   fused.evidence_summary,
        "nodes_executed":   ["anomaly_hunter"],
    }
