"""
OTLP/HTTP JSON receiver.

Parses the OTLP JSON format that the OTel Collector sends when configured
with the `otlphttp` exporter (encoding: json).

Produces lists of NormalizedMetric / NormalizedLog / NormalizedTrace.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from ingestion.models import NormalizedMetric, NormalizedLog, NormalizedSpan, NormalizedTrace

logger = logging.getLogger(__name__)


def _get_string_attr(attributes: list[dict], key: str, default: str = "") -> str:
    for attr in attributes:
        if attr.get("key") == key:
            val = attr.get("value", {})
            return (
                val.get("stringValue")
                or val.get("intValue", "")
                or val.get("doubleValue", "")
                or default
            )
    return default


def _nanos_to_datetime(nano_str: str | int) -> datetime:
    ns = int(nano_str)
    return datetime.fromtimestamp(ns / 1e9, tz=timezone.utc)


def _flatten_attributes(attributes: list[dict]) -> dict[str, Any]:
    result = {}
    for attr in attributes:
        key = attr.get("key", "")
        val = attr.get("value", {})
        result[key] = (
            val.get("stringValue")
            or val.get("intValue")
            or val.get("doubleValue")
            or val.get("boolValue")
            or val.get("arrayValue")
            or ""
        )
    return result


# ─── Metrics Parser ───────────────────────────────────────────────────────────

def parse_otlp_metrics(payload: dict[str, Any]) -> list[NormalizedMetric]:
    """
    OTLP metrics payload → list of NormalizedMetric.
    Handles gauge, sum, and histogram (extracts sum/count).
    """
    results: list[NormalizedMetric] = []

    for resource_metric in payload.get("resourceMetrics", []):
        resource_attrs = resource_metric.get("resource", {}).get("attributes", [])
        service_id = _get_string_attr(resource_attrs, "service.name", default="unknown")

        for scope_metric in resource_metric.get("scopeMetrics", []):
            for metric in scope_metric.get("metrics", []):
                metric_name = metric.get("name", "unknown")
                unit = metric.get("unit", "")

                # Gauge
                for dp in metric.get("gauge", {}).get("dataPoints", []):
                    value = dp.get("asDouble") or dp.get("asInt") or 0.0
                    ts = _nanos_to_datetime(dp.get("timeUnixNano", 0))
                    labels = _flatten_attributes(dp.get("attributes", []))
                    results.append(NormalizedMetric(
                        service_id=service_id, metric_name=metric_name,
                        value=float(value), unit=unit, labels=labels, timestamp=ts,
                    ))

                # Sum (counter / updown counter)
                for dp in metric.get("sum", {}).get("dataPoints", []):
                    value = dp.get("asDouble") or dp.get("asInt") or 0.0
                    ts = _nanos_to_datetime(dp.get("timeUnixNano", 0))
                    labels = _flatten_attributes(dp.get("attributes", []))
                    results.append(NormalizedMetric(
                        service_id=service_id, metric_name=metric_name,
                        value=float(value), unit=unit, labels=labels, timestamp=ts,
                    ))

                # Histogram — store sum and count as separate metrics
                for dp in metric.get("histogram", {}).get("dataPoints", []):
                    ts = _nanos_to_datetime(dp.get("timeUnixNano", 0))
                    labels = _flatten_attributes(dp.get("attributes", []))
                    count = dp.get("count", 0)
                    s = dp.get("sum", 0.0)
                    if count and s:
                        results.append(NormalizedMetric(
                            service_id=service_id,
                            metric_name=f"{metric_name}.avg",
                            value=float(s) / float(count),
                            unit=unit, labels=labels, timestamp=ts,
                        ))
                    results.append(NormalizedMetric(
                        service_id=service_id, metric_name=f"{metric_name}.count",
                        value=float(count), unit="", labels=labels, timestamp=ts,
                    ))

    return results


# ─── Logs Parser ──────────────────────────────────────────────────────────────

def parse_otlp_logs(payload: dict[str, Any]) -> list[NormalizedLog]:
    results: list[NormalizedLog] = []

    for resource_log in payload.get("resourceLogs", []):
        resource_attrs = resource_log.get("resource", {}).get("attributes", [])
        service_id = _get_string_attr(resource_attrs, "service.name", default="unknown")

        for scope_log in resource_log.get("scopeLogs", []):
            for record in scope_log.get("logRecords", []):
                ts_nano = record.get("timeUnixNano") or record.get("observedTimeUnixNano", 0)
                body_val = record.get("body", {})
                body = body_val.get("stringValue", "") if isinstance(body_val, dict) else str(body_val)
                severity = record.get("severityText", "INFO")

                results.append(NormalizedLog(
                    service_id=service_id,
                    level=severity,
                    body=body,
                    timestamp=_nanos_to_datetime(ts_nano) if ts_nano else None,
                    trace_id=record.get("traceId", ""),
                    span_id=record.get("spanId", ""),
                    attributes=_flatten_attributes(record.get("attributes", [])),
                ))

    return results


# ─── Traces Parser ────────────────────────────────────────────────────────────

def parse_otlp_traces(payload: dict[str, Any]) -> list[NormalizedTrace]:
    """
    Group spans by trace_id → NormalizedTrace objects.
    Identifies root span service as the trace's service_id.
    """
    from collections import defaultdict

    span_groups: dict[str, list[NormalizedSpan]] = defaultdict(list)

    for resource_span in payload.get("resourceSpans", []):
        resource_attrs = resource_span.get("resource", {}).get("attributes", [])
        service_id = _get_string_attr(resource_attrs, "service.name", default="unknown")

        for scope_span in resource_span.get("scopeSpans", []):
            for span in scope_span.get("spans", []):
                trace_id = span.get("traceId", "")
                start = _nanos_to_datetime(span.get("startTimeUnixNano", 0))
                end   = _nanos_to_datetime(span.get("endTimeUnixNano", 0))
                status = span.get("status", {})
                status_code = "ERROR" if status.get("code") == 2 else "OK"

                norm_span = NormalizedSpan(
                    trace_id=trace_id,
                    span_id=span.get("spanId", ""),
                    parent_span_id=span.get("parentSpanId", ""),
                    service_id=service_id,
                    operation_name=span.get("name", ""),
                    start_time=start,
                    end_time=end,
                    status_code=status_code,
                    attributes=_flatten_attributes(span.get("attributes", [])),
                )
                span_groups[trace_id].append(norm_span)

    traces = []
    for trace_id, spans in span_groups.items():
        # Root span = the one with no parent
        root_spans = [s for s in spans if not s.parent_span_id]
        root_service = root_spans[0].service_id if root_spans else spans[0].service_id
        traces.append(NormalizedTrace(
            trace_id=trace_id, service_id=root_service, spans=spans
        ))

    return traces
