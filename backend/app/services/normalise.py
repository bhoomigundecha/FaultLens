"""
FaultLens Backend — Telemetry Normalisation (Phase 7)

Converts raw opentelemetry-proto objects into plain Python dicts whose keys
match the ORM model column names exactly.  The ingest layer calls these
functions after parsing the protobuf payload; the results are passed straight
to the ORM constructors.

Design decisions:
  - All timestamps are kept as UTC epoch nanoseconds (int) — no conversion to
    datetime, which would lose sub-millisecond precision.
  - trace_id and span_id are stored as lowercase hex strings (no hyphens).
  - Attribute values are JSON-serialisable Python primitives (str/int/float/bool/None).
  - Protobuf AnyValue is recursively flattened; unsupported types fall back to str().
  - resource_attributes are extracted once per ResourceSpans / ResourceMetrics /
    ResourceLogs and stamped onto every child row.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Attribute helpers
# ─────────────────────────────────────────────────────────────────────────────

def _any_value(av) -> Any:
    """
    Recursively convert a protobuf AnyValue to a plain Python value.
    AnyValue is a oneof; only one field is set at a time.
    """
    kind = av.WhichOneof("value")
    if kind == "string_value":
        return av.string_value
    if kind == "bool_value":
        return av.bool_value
    if kind == "int_value":
        return av.int_value
    if kind == "double_value":
        return av.double_value
    if kind == "array_value":
        return [_any_value(v) for v in av.array_value.values]
    if kind == "kvlist_value":
        return {kv.key: _any_value(kv.value) for kv in av.kvlist_value.values}
    if kind == "bytes_value":
        return av.bytes_value.hex()
    return None


def _attrs(kv_list) -> dict[str, Any]:
    """Convert a repeated KeyValue field into a plain dict."""
    return {kv.key: _any_value(kv.value) for kv in kv_list}


def _service_name(resource_attrs: dict) -> str | None:
    return resource_attrs.get("service.name")


def _hex(b: bytes) -> str:
    return b.hex() if b else ""


def _s(value, max_len: int):
    """
    Clamp a string to its DB column length (VARCHAR(n)).
    Real SDKs send surprises — e.g. .NET scope versions carry a git SHA
    ("1.12.0-beta.1+<40 hex chars>") that overflows VARCHAR(64) and used to
    abort the whole batch.
    """
    if value is None:
        return None
    value = str(value)
    return value if len(value) <= max_len else value[:max_len]


# ─────────────────────────────────────────────────────────────────────────────
# Phase 7 — Trace normalisation
# ─────────────────────────────────────────────────────────────────────────────

def normalise_traces(resource_spans_list) -> list[dict]:
    """
    Flatten an iterable of ResourceSpans proto objects into a list of dicts,
    one dict per span, ready for bulk ORM insertion.

    Args:
        resource_spans_list: the ``resource_spans`` repeated field from an
            ExportTraceServiceRequest.

    Returns:
        List of dicts with keys matching ``Span`` column names.
    """
    rows: list[dict] = []

    for rs in resource_spans_list:
        resource_attrs = _attrs(rs.resource.attributes) if rs.HasField("resource") else {}
        svc = _service_name(resource_attrs)

        for ss in rs.scope_spans:
            scope_name    = ss.scope.name    if ss.HasField("scope") else None
            scope_version = ss.scope.version if ss.HasField("scope") else None

            for span in ss.spans:
                rows.append({
                    "trace_id":              _hex(span.trace_id),
                    "span_id":               _hex(span.span_id),
                    "parent_span_id":        _hex(span.parent_span_id) or None,
                    "name":                  _s(span.name, 512),
                    "kind":                  int(span.kind),
                    "start_time_unix_nano":  span.start_time_unix_nano,
                    "end_time_unix_nano":    span.end_time_unix_nano,
                    "status_code":           int(span.status.code) if span.HasField("status") else None,
                    "status_message":        span.status.message   if span.HasField("status") else None,
                    "service_name":          _s(svc, 256),
                    "scope_name":            _s(scope_name, 256),
                    "scope_version":         _s(scope_version, 64),
                    "span_attributes":       _attrs(span.attributes) or None,
                    "resource_attributes":   resource_attrs or None,
                })

    return rows


# ─────────────────────────────────────────────────────────────────────────────
# Phase 7 — Metrics normalisation
# ─────────────────────────────────────────────────────────────────────────────

def _normalise_gauge_or_sum(metric, metric_type: str, resource_attrs: dict,
                             svc, scope_name, scope_version) -> list[dict]:
    rows = []
    data = metric.gauge if metric_type == "gauge" else metric.sum
    is_monotonic = metric.sum.is_monotonic if metric_type == "sum" else None
    for dp in data.data_points:
        val_double = val_int = None
        kind = dp.WhichOneof("value")
        if kind == "as_double":
            val_double = dp.as_double
        elif kind == "as_int":
            val_int = dp.as_int
        rows.append({
            "metric_name":            _s(metric.name, 512),
            "metric_description":     metric.description or None,
            "metric_unit":            _s(metric.unit or None, 128),
            "metric_type":            metric_type,
            "service_name":           _s(svc, 256),
            "scope_name":             _s(scope_name, 256),
            "scope_version":          _s(scope_version, 64),
            "start_time_unix_nano":   dp.start_time_unix_nano or None,
            "time_unix_nano":         dp.time_unix_nano,
            "value_double":           val_double,
            "value_int":              val_int,
            "hist_count":             None,
            "hist_sum":               None,
            "hist_bucket_counts":     None,
            "hist_explicit_bounds":   None,
            "is_monotonic":           is_monotonic,
            "data_point_attributes":  _attrs(dp.attributes) or None,
            "resource_attributes":    resource_attrs or None,
        })
    return rows


def _normalise_histogram(metric, resource_attrs: dict,
                          svc, scope_name, scope_version) -> list[dict]:
    rows = []
    for dp in metric.histogram.data_points:
        rows.append({
            "metric_name":            _s(metric.name, 512),
            "metric_description":     metric.description or None,
            "metric_unit":            _s(metric.unit or None, 128),
            "metric_type":            "histogram",
            "service_name":           _s(svc, 256),
            "scope_name":             _s(scope_name, 256),
            "scope_version":          _s(scope_version, 64),
            "start_time_unix_nano":   dp.start_time_unix_nano or None,
            "time_unix_nano":         dp.time_unix_nano,
            "value_double":           None,
            "value_int":              None,
            "hist_count":             dp.count,
            "hist_sum":               dp.sum if dp.HasField("sum") else None,
            "hist_bucket_counts":     list(dp.bucket_counts) or None,
            "hist_explicit_bounds":   list(dp.explicit_bounds) or None,
            "is_monotonic":           None,
            "data_point_attributes":  _attrs(dp.attributes) or None,
            "resource_attributes":    resource_attrs or None,
        })
    return rows


def normalise_metrics(resource_metrics_list) -> list[dict]:
    """
    Flatten an iterable of ResourceMetrics proto objects into a list of dicts,
    one dict per data point, ready for bulk ORM insertion.

    Args:
        resource_metrics_list: the ``resource_metrics`` repeated field from an
            ExportMetricsServiceRequest.

    Returns:
        List of dicts with keys matching ``MetricPoint`` column names.
    """
    rows: list[dict] = []

    for rm in resource_metrics_list:
        resource_attrs = _attrs(rm.resource.attributes) if rm.HasField("resource") else {}
        svc = _service_name(resource_attrs)

        for sm in rm.scope_metrics:
            scope_name    = sm.scope.name    if sm.HasField("scope") else None
            scope_version = sm.scope.version if sm.HasField("scope") else None

            for metric in sm.metrics:
                mtype = metric.WhichOneof("data")
                try:
                    if mtype in ("gauge", "sum"):
                        rows.extend(_normalise_gauge_or_sum(
                            metric, mtype, resource_attrs, svc, scope_name, scope_version))
                    elif mtype == "histogram":
                        rows.extend(_normalise_histogram(
                            metric, resource_attrs, svc, scope_name, scope_version))
                    else:
                        # exponential_histogram, summary — not yet supported
                        logger.debug("Skipping unsupported metric type: %s", mtype)
                except Exception as exc:
                    logger.warning("Error normalising metric %s: %s", metric.name, exc)

    return rows


# ─────────────────────────────────────────────────────────────────────────────
# Phase 7 — Log normalisation
# ─────────────────────────────────────────────────────────────────────────────

def _body_to_str(body_av) -> str | None:
    """Extract a plain string from a log body AnyValue."""
    try:
        kind = body_av.WhichOneof("value")
        if kind == "string_value":
            return body_av.string_value
        if kind is None:
            return None
        return str(_any_value(body_av))
    except Exception:
        return None


def normalise_logs(resource_logs_list) -> list[dict]:
    """
    Flatten an iterable of ResourceLogs proto objects into a list of dicts,
    one dict per log record, ready for bulk ORM insertion.

    Args:
        resource_logs_list: the ``resource_logs`` repeated field from an
            ExportLogsServiceRequest.

    Returns:
        List of dicts with keys matching ``LogRecord`` column names.
    """
    rows: list[dict] = []

    for rl in resource_logs_list:
        resource_attrs = _attrs(rl.resource.attributes) if rl.HasField("resource") else {}
        svc = _service_name(resource_attrs)

        for sl in rl.scope_logs:
            scope_name    = sl.scope.name    if sl.HasField("scope") else None
            scope_version = sl.scope.version if sl.HasField("scope") else None

            for lr in sl.log_records:
                rows.append({
                    "trace_id":               _hex(lr.trace_id) or None,
                    "span_id":                _hex(lr.span_id)  or None,
                    "time_unix_nano":         lr.time_unix_nano or None,
                    "observed_time_unix_nano": lr.observed_time_unix_nano or None,
                    "severity_number":        int(lr.severity_number) or None,
                    "severity_text":          _s(lr.severity_text or None, 64),
                    "body":                   _body_to_str(lr.body),
                    "service_name":           _s(svc, 256),
                    "scope_name":             _s(scope_name, 256),
                    "scope_version":          _s(scope_version, 64),
                    "log_attributes":         _attrs(lr.attributes) or None,
                    "resource_attributes":    resource_attrs or None,
                })

    return rows
