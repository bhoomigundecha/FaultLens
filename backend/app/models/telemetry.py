"""
FaultLens Backend — ORM Models (Phase 8)

Three tables that mirror the OTLP signal hierarchy:

  spans      — one row per span (traces signal)
  metric_points — one row per data point (metrics signal)
  log_records   — one row per log record (logs signal)

All timestamps are stored as UTC epoch nanoseconds (int) matching
the native OTLP wire format to avoid floating-point precision loss.
"""
from __future__ import annotations

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Double,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB

from app.db.session import Base


class Span(Base):
    """
    One row per OTel span.

    Columns derived from the OTLP ExportTraceServiceRequest proto:
      ResourceSpans → ScopeSpans → Span
    """
    __tablename__ = "spans"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # ── Trace / span identifiers ──────────────────────────────────────────────
    trace_id = Column(String(32), nullable=False, index=True)   # hex, 16 bytes
    span_id  = Column(String(16), nullable=False, index=True)   # hex,  8 bytes
    parent_span_id = Column(String(16), nullable=True)           # null for root spans

    # ── Timing (UTC epoch nanoseconds) ────────────────────────────────────────
    start_time_unix_nano = Column(BigInteger, nullable=False)
    end_time_unix_nano   = Column(BigInteger, nullable=False)

    # ── Span metadata ─────────────────────────────────────────────────────────
    name         = Column(String(512), nullable=False)
    kind         = Column(Integer, nullable=True)   # SpanKind enum value
    status_code  = Column(Integer, nullable=True)   # StatusCode enum value (0=unset,1=ok,2=error)
    status_message = Column(Text, nullable=True)

    # ── Resource / scope ─────────────────────────────────────────────────────
    service_name  = Column(String(256), nullable=True, index=True)
    scope_name    = Column(String(256), nullable=True)
    scope_version = Column(String(64),  nullable=True)

    # ── Flexible attribute bags (JSONB for efficient querying) ─────────────────
    span_attributes     = Column(JSONB, nullable=True)
    resource_attributes = Column(JSONB, nullable=True)

    __table_args__ = (
        # Fast look-ups by service + time window (used by correlation / RCA)
        Index("ix_spans_service_start", "service_name", "start_time_unix_nano"),
        Index("ix_spans_start", "start_time_unix_nano"),          # RED windows + retention
        # Fast look-up for child spans given a parent
        Index("ix_spans_parent", "parent_span_id"),
    )


class MetricPoint(Base):
    """
    One row per OTLP metric data point.

    A Metric can have one of several data types (Gauge, Sum, Histogram, …).
    We store them in a single table and use `metric_type` + nullable columns to
    handle the union.  Only the fields relevant to each type are populated.
    """
    __tablename__ = "metric_points"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # ── Identity ──────────────────────────────────────────────────────────────
    metric_name        = Column(String(512), nullable=False, index=True)
    metric_description = Column(Text, nullable=True)
    metric_unit        = Column(String(128), nullable=True)
    metric_type        = Column(String(32), nullable=False)  # gauge|sum|histogram|…

    # ── Resource / scope ─────────────────────────────────────────────────────
    service_name  = Column(String(256), nullable=True, index=True)
    scope_name    = Column(String(256), nullable=True)
    scope_version = Column(String(64),  nullable=True)

    # ── Timing (UTC epoch nanoseconds) ────────────────────────────────────────
    start_time_unix_nano = Column(BigInteger, nullable=True)  # absent on gauge
    time_unix_nano       = Column(BigInteger, nullable=False)

    # ── Numeric values ────────────────────────────────────────────────────────
    value_double = Column(Double, nullable=True)   # Gauge / Sum as_double
    value_int    = Column(BigInteger, nullable=True)  # Gauge / Sum as_int

    # ── Histogram buckets (stored as JSON arrays) ─────────────────────────────
    hist_count  = Column(BigInteger, nullable=True)
    hist_sum    = Column(Double, nullable=True)
    hist_bucket_counts = Column(JSONB, nullable=True)  # list[int]
    hist_explicit_bounds = Column(JSONB, nullable=True) # list[float]

    # ── Flexible attribute bags ───────────────────────────────────────────────
    data_point_attributes = Column(JSONB, nullable=True)
    resource_attributes   = Column(JSONB, nullable=True)

    # ── Sum-specific ─────────────────────────────────────────────────────────
    is_monotonic = Column(Boolean, nullable=True)

    __table_args__ = (
        Index("ix_metric_points_service_time", "service_name", "time_unix_nano"),
        Index("ix_metric_points_name_time", "metric_name", "time_unix_nano"),
        Index("ix_metric_points_time", "time_unix_nano"),          # retention
    )


class LogRecord(Base):
    """
    One row per OTLP log record.
    """
    __tablename__ = "log_records"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # ── Trace context (optional — correlates log to a span) ───────────────────
    trace_id = Column(String(32), nullable=True, index=True)
    span_id  = Column(String(16), nullable=True)

    # ── Timing ────────────────────────────────────────────────────────────────
    time_unix_nano         = Column(BigInteger, nullable=True)
    observed_time_unix_nano = Column(BigInteger, nullable=True)

    # ── Severity ──────────────────────────────────────────────────────────────
    severity_number = Column(Integer, nullable=True)   # 0 = unspecified
    severity_text   = Column(String(64), nullable=True)

    # ── Body ──────────────────────────────────────────────────────────────────
    body = Column(Text, nullable=True)

    # ── Resource / scope ─────────────────────────────────────────────────────
    service_name  = Column(String(256), nullable=True, index=True)
    scope_name    = Column(String(256), nullable=True)
    scope_version = Column(String(64),  nullable=True)

    # ── Flexible attribute bags ───────────────────────────────────────────────
    log_attributes      = Column(JSONB, nullable=True)
    resource_attributes = Column(JSONB, nullable=True)

    __table_args__ = (
        Index("ix_log_records_service_time", "service_name", "time_unix_nano"),
        Index("ix_log_records_time", "time_unix_nano"),            # retention
    )
