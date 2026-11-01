"""
FaultLens Backend — Telemetry Correlation (Phase 11)

Given a trace_id, correlates:
  1. Spans       — all spans in the trace (from the spans table)
  2. Logs        — log records with matching trace_id
  3. Metrics     — metric data points from the same service(s) within the
                   trace's time window ± correlation_window_ns

This is purely read-side logic — no writes.  All functions take an async
DB session and return plain dicts ready for JSON serialisation.

Design decisions:
  - No joins across tables — separate queries per signal type.
    Simple, predictable, easy to debug.
  - Metric correlation uses service_name + time window, not trace_id
    (metrics don't carry trace context in OTLP).
  - All timestamps returned as milliseconds for frontend convenience.
"""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.telemetry import Span, LogRecord, MetricPoint

logger = logging.getLogger(__name__)

_NS_PER_MS = 1_000_000


# ── Helpers ───────────────────────────────────────────────────────────────────

def _span_to_dict(s: Span) -> dict[str, Any]:
    duration_ms = (
        (s.end_time_unix_nano - s.start_time_unix_nano) / _NS_PER_MS
        if s.end_time_unix_nano and s.start_time_unix_nano
        else None
    )
    return {
        "span_id":        s.span_id,
        "parent_span_id": s.parent_span_id,
        "name":           s.name,
        "service_name":   s.service_name,
        "kind":           s.kind,
        "status_code":    s.status_code,
        "status_message": s.status_message,
        "start_ms":       (s.start_time_unix_nano or 0) // _NS_PER_MS,
        "end_ms":         (s.end_time_unix_nano   or 0) // _NS_PER_MS,
        "duration_ms":    duration_ms,
        "span_attributes":     s.span_attributes,
        "resource_attributes": s.resource_attributes,
    }


def _log_to_dict(lr: LogRecord) -> dict[str, Any]:
    return {
        "span_id":        lr.span_id,
        "time_ms":        (lr.time_unix_nano or 0) // _NS_PER_MS,
        "severity_number": lr.severity_number,
        "severity_text":  lr.severity_text,
        "body":           lr.body,
        "service_name":   lr.service_name,
        "log_attributes": lr.log_attributes,
    }


def _metric_to_dict(mp: MetricPoint) -> dict[str, Any]:
    return {
        "metric_name":  mp.metric_name,
        "metric_type":  mp.metric_type,
        "metric_unit":  mp.metric_unit,
        "service_name": mp.service_name,
        "time_ms":      (mp.time_unix_nano or 0) // _NS_PER_MS,
        "value_double": mp.value_double,
        "value_int":    mp.value_int,
        "hist_count":   mp.hist_count,
        "data_point_attributes": mp.data_point_attributes,
    }


# ── Core queries ──────────────────────────────────────────────────────────────

async def get_trace_spans(
    db: AsyncSession,
    trace_id: str,
) -> list[Span]:
    """Fetch all spans for a given trace_id, ordered by start time."""
    result = await db.execute(
        select(Span)
        .where(Span.trace_id == trace_id)
        .order_by(Span.start_time_unix_nano)
    )
    return result.scalars().all()


async def get_correlated_logs(
    db: AsyncSession,
    trace_id: str,
) -> list[LogRecord]:
    """Fetch all log records that carry the given trace_id."""
    result = await db.execute(
        select(LogRecord)
        .where(LogRecord.trace_id == trace_id)
        .order_by(LogRecord.time_unix_nano)
    )
    return result.scalars().all()


async def get_correlated_metrics(
    db: AsyncSession,
    service_names: list[str],
    start_ns: int,
    end_ns: int,
    window_ns: int,
) -> list[MetricPoint]:
    """
    Fetch metric data points from the given services within the time window
    [start_ns - window_ns, end_ns + window_ns].

    Limited to 200 rows to avoid blowing up the response — callers can
    paginate or narrow the window if needed.
    """
    if not service_names:
        return []

    lo = max(0, start_ns - window_ns)
    hi = end_ns + window_ns

    result = await db.execute(
        select(MetricPoint)
        .where(
            MetricPoint.service_name.in_(service_names),
            MetricPoint.time_unix_nano >= lo,
            MetricPoint.time_unix_nano <= hi,
        )
        .order_by(MetricPoint.time_unix_nano)
        .limit(200)
    )
    return result.scalars().all()


# ── High-level correlation ─────────────────────────────────────────────────────

async def correlate_trace(
    db: AsyncSession,
    trace_id: str,
    window_ns: int,
) -> dict[str, Any] | None:
    """
    Returns a complete correlated context for a trace:
      - All spans
      - All logs that share the trace_id
      - Metrics from the same services in the same time window

    Returns None if the trace_id is unknown.
    """
    spans = await get_trace_spans(db, trace_id)
    if not spans:
        return None

    # Compute trace-level time bounds from its spans
    start_ns = min(s.start_time_unix_nano for s in spans if s.start_time_unix_nano)
    end_ns   = max(s.end_time_unix_nano   for s in spans if s.end_time_unix_nano)
    services = list({s.service_name for s in spans if s.service_name})

    logs, metrics = await _fetch_correlated(db, trace_id, services, start_ns, end_ns, window_ns)

    # Build a simple span tree (parent→children map)
    span_dicts = [_span_to_dict(s) for s in spans]
    error_spans = [s for s in span_dicts if s["status_code"] == 2]

    return {
        "trace_id":       trace_id,
        "start_ms":       start_ns // _NS_PER_MS,
        "end_ms":         end_ns   // _NS_PER_MS,
        "duration_ms":    (end_ns - start_ns) // _NS_PER_MS,
        "services":       sorted(services),
        "span_count":     len(spans),
        "error_span_count": len(error_spans),
        "spans":          span_dicts,
        "logs":           [_log_to_dict(lr) for lr in logs],
        "metrics":        [_metric_to_dict(mp) for mp in metrics],
        "log_count":      len(logs),
        "metric_count":   len(metrics),
    }


async def _fetch_correlated(db, trace_id, services, start_ns, end_ns, window_ns):
    """Run log and metric queries concurrently (sequential here — simple & safe)."""
    logs    = await get_correlated_logs(db, trace_id)
    metrics = await get_correlated_metrics(db, services, start_ns, end_ns, window_ns)
    return logs, metrics
