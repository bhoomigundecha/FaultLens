"""
FaultLens Backend — Phase 3 & 4 Tests

Tests OTLP ingestion endpoint behaviour:
  Phase 3: endpoints respond 200 with correct headers (without a live collector)
  Phase 4: protobuf payloads are parsed and span/metric/log counts extracted

All tests are self-contained — they build minimal protobuf payloads from the
opentelemetry-proto library and post them to the ASGI app.
The DB dependency (get_db) is mocked so no live PostgreSQL is required.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.db.session import get_db


# ── DB mock fixture ───────────────────────────────────────────────────────────

def _mock_db_session():
    """Return an async-context-manager-compatible mock DB session."""
    session = MagicMock()
    session.add_all = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


async def _noop_get_db():
    """Dependency override: yield a no-op session (no DB needed)."""
    yield _mock_db_session()


# ── Helpers — build minimal OTLP protobuf request bodies ──────────────────────

def _build_trace_request(num_spans: int = 3) -> bytes:
    from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
        ExportTraceServiceRequest,
    )
    from opentelemetry.proto.trace.v1.trace_pb2 import (
        ResourceSpans, ScopeSpans, Span,
    )
    spans = [Span(
        trace_id=b"\x00" * 16,
        span_id=i.to_bytes(8, "big"),
        name=f"span-{i}",
        start_time_unix_nano=i * 1_000,
        end_time_unix_nano=(i + 1) * 1_000,
    ) for i in range(1, num_spans + 1)]
    req = ExportTraceServiceRequest(
        resource_spans=[
            ResourceSpans(scope_spans=[ScopeSpans(spans=spans)])
        ]
    )
    return req.SerializeToString()


def _build_metrics_request(num_data_points: int = 5) -> bytes:
    from opentelemetry.proto.collector.metrics.v1.metrics_service_pb2 import (
        ExportMetricsServiceRequest,
    )
    from opentelemetry.proto.metrics.v1.metrics_pb2 import (
        ResourceMetrics, ScopeMetrics, Metric, Gauge, NumberDataPoint,
    )
    data_points = [NumberDataPoint(time_unix_nano=i * 1_000, as_double=float(i))
                   for i in range(1, num_data_points + 1)]
    metric = Metric(name="test.metric", gauge=Gauge(data_points=data_points))
    req = ExportMetricsServiceRequest(
        resource_metrics=[
            ResourceMetrics(scope_metrics=[ScopeMetrics(metrics=[metric])])
        ]
    )
    return req.SerializeToString()


def _build_logs_request(num_records: int = 4) -> bytes:
    from opentelemetry.proto.collector.logs.v1.logs_service_pb2 import (
        ExportLogsServiceRequest,
    )
    from opentelemetry.proto.logs.v1.logs_pb2 import (
        ResourceLogs, ScopeLogs, LogRecord,
    )
    from opentelemetry.proto.common.v1.common_pb2 import AnyValue
    records = [LogRecord(time_unix_nano=i * 1_000,
                         body=AnyValue(string_value=f"log-{i}"))
               for i in range(num_records)]
    req = ExportLogsServiceRequest(
        resource_logs=[
            ResourceLogs(scope_logs=[ScopeLogs(log_records=records)])
        ]
    )
    return req.SerializeToString()


PROTO_CONTENT_TYPE = "application/x-protobuf"


# ── Phase 3 tests — endpoints are alive and return 200 ───────────────────────

@pytest.mark.asyncio
async def test_traces_endpoint_returns_200():
    """POST /otlp/v1/traces with protobuf body → 200"""
    app.dependency_overrides[get_db] = _noop_get_db
    try:
        body = _build_trace_request(num_spans=1)
        async with AsyncClient(transport=ASGITransport(app=app),
                               base_url="http://test") as client:
            response = await client.post(
                "/otlp/v1/traces",
                content=body,
                headers={"content-type": PROTO_CONTENT_TYPE},
            )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_metrics_endpoint_returns_200():
    """POST /otlp/v1/metrics with protobuf body → 200"""
    app.dependency_overrides[get_db] = _noop_get_db
    try:
        body = _build_metrics_request(num_data_points=2)
        async with AsyncClient(transport=ASGITransport(app=app),
                               base_url="http://test") as client:
            response = await client.post(
                "/otlp/v1/metrics",
                content=body,
                headers={"content-type": PROTO_CONTENT_TYPE},
            )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_logs_endpoint_returns_200():
    """POST /otlp/v1/logs with protobuf body → 200"""
    app.dependency_overrides[get_db] = _noop_get_db
    try:
        body = _build_logs_request(num_records=2)
        async with AsyncClient(transport=ASGITransport(app=app),
                               base_url="http://test") as client:
            response = await client.post(
                "/otlp/v1/logs",
                content=body,
                headers={"content-type": PROTO_CONTENT_TYPE},
            )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_traces_endpoint_rejects_empty_body():
    """POST /otlp/v1/traces with no body → 400"""
    app.dependency_overrides[get_db] = _noop_get_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app),
                               base_url="http://test") as client:
            response = await client.post(
                "/otlp/v1/traces",
                content=b"",
                headers={"content-type": PROTO_CONTENT_TYPE},
            )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 400


# ── Phase 4 tests — span / metric / log counting works correctly ──────────────

def test_count_spans_correct():
    """_count_spans extracts the right number of spans from a serialised request."""
    from app.api.v1.ingest import _count_spans
    body = _build_trace_request(num_spans=7)
    assert _count_spans(body) == 7


def test_count_spans_empty_body_returns_zero():
    """_count_spans returns 0 for garbage input without raising."""
    from app.api.v1.ingest import _count_spans
    assert _count_spans(b"not-a-proto") == 0


def test_count_metric_data_points_correct():
    """_count_metric_data_points extracts the right number of data points."""
    from app.api.v1.ingest import _count_metric_data_points
    body = _build_metrics_request(num_data_points=5)
    assert _count_metric_data_points(body) == 5


def test_count_log_records_correct():
    """_count_log_records extracts the right number of log records."""
    from app.api.v1.ingest import _count_log_records
    body = _build_logs_request(num_records=4)
    assert _count_log_records(body) == 4
