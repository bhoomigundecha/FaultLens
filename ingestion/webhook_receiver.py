"""
Webhook receivers for thin environments (Vercel, Render).

Both convert platform-native log formats into NormalizedLog objects
and extract HTTP response metrics from log text patterns.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from typing import Any

from ingestion.models import NormalizedLog, NormalizedMetric

logger = logging.getLogger(__name__)

# Matches lines like: "GET /api/orders 500 2134ms" or "POST /api/orders 200 45ms"
HTTP_PATTERN = re.compile(
    r"(?P<method>GET|POST|PUT|DELETE|PATCH)\s+(?P<path>/\S*)\s+(?P<status>\d{3})\s+(?P<duration>\d+)ms",
    re.IGNORECASE,
)


def _extract_http_metrics(
    body: str, service_id: str, timestamp: datetime
) -> list[NormalizedMetric]:
    """Extract structured HTTP metrics from a plain-text log line."""
    match = HTTP_PATTERN.search(body)
    if not match:
        return []

    status = int(match.group("status"))
    duration = float(match.group("duration"))
    path = match.group("path")
    method = match.group("method")
    labels = {"http.method": method, "http.path": path, "http.status": str(status)}

    metrics = [
        NormalizedMetric(
            service_id=service_id,
            metric_name="http.request.duration_ms",
            value=duration,
            unit="ms",
            labels=labels,
            timestamp=timestamp,
        ),
        NormalizedMetric(
            service_id=service_id,
            metric_name="http.request.count",
            value=1.0,
            unit="",
            labels=labels,
            timestamp=timestamp,
        ),
    ]

    if status >= 500:
        metrics.append(NormalizedMetric(
            service_id=service_id,
            metric_name="http.request.error_count",
            value=1.0,
            unit="",
            labels=labels,
            timestamp=timestamp,
        ))

    return metrics


# ─── Vercel ───────────────────────────────────────────────────────────────────

def parse_vercel_payload(
    payload: list[dict[str, Any]], service_id: str
) -> tuple[list[NormalizedLog], list[NormalizedMetric]]:
    """
    Parse a Vercel Log Drain POST body.
    Returns (logs, derived_metrics).
    Ref: https://vercel.com/docs/observability/log-drains
    """
    from ingestion.models import VercelLogEntry

    logs: list[NormalizedLog] = []
    metrics: list[NormalizedMetric] = []

    for raw in payload:
        try:
            entry = VercelLogEntry(**raw)
            norm_log = entry.to_normalized_log(service_id)
            logs.append(norm_log)
            metrics.extend(
                _extract_http_metrics(entry.message, service_id, norm_log.timestamp)
            )
        except Exception as e:
            logger.warning(f"Could not parse Vercel log entry: {e} — raw={raw}")

    return logs, metrics


# ─── Render ───────────────────────────────────────────────────────────────────

def parse_render_payload(
    payload: list[dict[str, Any]], service_id: str
) -> tuple[list[NormalizedLog], list[NormalizedMetric]]:
    """
    Parse a Render log stream payload.
    Render sends NDJSON: each line is a JSON object.
    """
    from ingestion.models import RenderLogEntry

    logs: list[NormalizedLog] = []
    metrics: list[NormalizedMetric] = []

    for raw in payload:
        try:
            entry = RenderLogEntry(**raw)
            norm_log = entry.to_normalized_log(service_id)
            logs.append(norm_log)
            metrics.extend(
                _extract_http_metrics(entry.message, service_id, norm_log.timestamp)
            )
        except Exception as e:
            logger.warning(f"Could not parse Render log entry: {e} — raw={raw}")

    return logs, metrics
