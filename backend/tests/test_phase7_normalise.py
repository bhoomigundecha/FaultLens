"""
FaultLens Backend — Phase 7 Tests: Telemetry Normalisation

Tests the normalise_traces / normalise_metrics / normalise_logs functions
in isolation using minimal protobuf objects.  No database required.
"""
import pytest

from opentelemetry.proto.trace.v1.trace_pb2 import (
    ResourceSpans, ScopeSpans, Span, Status,
)
from opentelemetry.proto.metrics.v1.metrics_pb2 import (
    ResourceMetrics, ScopeMetrics, Metric, Gauge, Sum, Histogram,
    NumberDataPoint, HistogramDataPoint,
)
from opentelemetry.proto.logs.v1.logs_pb2 import (
    ResourceLogs, ScopeLogs, LogRecord,
)
from opentelemetry.proto.common.v1.common_pb2 import (
    AnyValue, KeyValue, InstrumentationScope,
)
from opentelemetry.proto.resource.v1.resource_pb2 import Resource

from app.services.normalise import normalise_traces, normalise_metrics, normalise_logs


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _kv(key: str, value: str) -> KeyValue:
    return KeyValue(key=key, value=AnyValue(string_value=value))


def _resource(service_name: str) -> Resource:
    return Resource(attributes=[_kv("service.name", service_name)])


def _scope(name: str, version: str = "1.0") -> InstrumentationScope:
    return InstrumentationScope(name=name, version=version)


# ─────────────────────────────────────────────────────────────────────────────
# normalise_traces
# ─────────────────────────────────────────────────────────────────────────────

def test_normalise_traces_basic():
    """Two spans produce two rows with correct field values."""
    span1 = Span(
        trace_id=bytes.fromhex("aabbccdd" * 4),
        span_id=bytes.fromhex("11223344" * 2),
        name="GET /cart",
        kind=2,
        start_time_unix_nano=1_000_000,
        end_time_unix_nano=2_000_000,
    )
    span2 = Span(
        trace_id=bytes.fromhex("aabbccdd" * 4),
        span_id=bytes.fromhex("55667788" * 2),
        parent_span_id=bytes.fromhex("11223344" * 2),
        name="cartservice.GetCart",
        kind=3,
        start_time_unix_nano=1_100_000,
        end_time_unix_nano=1_900_000,
    )
    rs = ResourceSpans(
        resource=_resource("frontend"),
        scope_spans=[ScopeSpans(scope=_scope("go.opentelemetry.io"), spans=[span1, span2])],
    )

    rows = normalise_traces([rs])

    assert len(rows) == 2
    assert rows[0]["name"] == "GET /cart"
    assert rows[0]["service_name"] == "frontend"
    assert rows[0]["scope_name"] == "go.opentelemetry.io"
    assert rows[0]["trace_id"] == "aabbccdd" * 4
    assert rows[0]["parent_span_id"] is None   # root span
    assert rows[1]["parent_span_id"] == "11223344" * 2


def test_normalise_traces_with_status():
    """status_code and status_message are extracted from the Status field."""
    span = Span(
        trace_id=b"\x00" * 16,
        span_id=b"\x01" * 8,
        name="checkout",
        start_time_unix_nano=0,
        end_time_unix_nano=1,
        status=Status(code=2, message="payment failed"),
    )
    rs = ResourceSpans(scope_spans=[ScopeSpans(spans=[span])])
    rows = normalise_traces([rs])

    assert rows[0]["status_code"] == 2
    assert rows[0]["status_message"] == "payment failed"


def test_normalise_traces_attributes():
    """span_attributes and resource_attributes are dicts, not None."""
    span = Span(
        trace_id=b"\x00" * 16,
        span_id=b"\x02" * 8,
        name="db.query",
        start_time_unix_nano=0,
        end_time_unix_nano=1,
        attributes=[_kv("db.system", "postgresql")],
    )
    rs = ResourceSpans(
        resource=_resource("order-service"),
        scope_spans=[ScopeSpans(spans=[span])],
    )
    rows = normalise_traces([rs])

    assert rows[0]["span_attributes"] == {"db.system": "postgresql"}
    assert rows[0]["resource_attributes"]["service.name"] == "order-service"


def test_normalise_traces_empty_returns_empty():
    assert normalise_traces([]) == []


# ─────────────────────────────────────────────────────────────────────────────
# normalise_metrics
# ─────────────────────────────────────────────────────────────────────────────

def test_normalise_metrics_gauge():
    """Gauge data point is stored with value_double set."""
    dp = NumberDataPoint(time_unix_nano=5_000, as_double=3.14)
    metric = Metric(name="cpu.usage", unit="%", gauge=Gauge(data_points=[dp]))
    rm = ResourceMetrics(
        resource=_resource("loadgen"),
        scope_metrics=[ScopeMetrics(scope=_scope("otel"), metrics=[metric])],
    )

    rows = normalise_metrics([rm])

    assert len(rows) == 1
    r = rows[0]
    assert r["metric_name"] == "cpu.usage"
    assert r["metric_type"] == "gauge"
    assert r["value_double"] == pytest.approx(3.14)
    assert r["value_int"] is None
    assert r["service_name"] == "loadgen"


def test_normalise_metrics_sum_int():
    """Sum data point with as_int stores value_int."""
    dp = NumberDataPoint(time_unix_nano=1_000, as_int=42)
    metric = Metric(
        name="requests.total",
        sum=Sum(data_points=[dp], is_monotonic=True),
    )
    rm = ResourceMetrics(
        resource=_resource("frontend"),
        scope_metrics=[ScopeMetrics(scope=_scope("http"), metrics=[metric])],
    )

    rows = normalise_metrics([rm])
    r = rows[0]

    assert r["metric_type"] == "sum"
    assert r["value_int"] == 42
    assert r["is_monotonic"] is True


def test_normalise_metrics_histogram():
    """Histogram data point populates hist_* columns."""
    dp = HistogramDataPoint(
        time_unix_nano=2_000,
        count=10,
        sum=55.5,
        bucket_counts=[2, 5, 3],
        explicit_bounds=[10.0, 50.0],
    )
    metric = Metric(name="http.duration", histogram=Histogram(data_points=[dp]))
    rm = ResourceMetrics(
        resource=_resource("checkout"),
        scope_metrics=[ScopeMetrics(scope=_scope("http"), metrics=[metric])],
    )

    rows = normalise_metrics([rm])
    r = rows[0]

    assert r["metric_type"] == "histogram"
    assert r["hist_count"] == 10
    assert r["hist_sum"] == pytest.approx(55.5)
    assert r["hist_bucket_counts"] == [2, 5, 3]
    assert r["hist_explicit_bounds"] == [10.0, 50.0]


def test_normalise_metrics_empty_returns_empty():
    assert normalise_metrics([]) == []


# ─────────────────────────────────────────────────────────────────────────────
# normalise_logs
# ─────────────────────────────────────────────────────────────────────────────

def test_normalise_logs_basic():
    """Log record fields are correctly mapped."""
    lr = LogRecord(
        time_unix_nano=9_000,
        severity_number=9,
        severity_text="INFO",
        body=AnyValue(string_value="cart items fetched"),
        trace_id=bytes.fromhex("aabbccdd" * 4),
        span_id=bytes.fromhex("11223344" * 2),
        attributes=[_kv("http.method", "GET")],
    )
    rl = ResourceLogs(
        resource=_resource("cart"),
        scope_logs=[ScopeLogs(scope=_scope("cartservice"), log_records=[lr])],
    )

    rows = normalise_logs([rl])

    assert len(rows) == 1
    r = rows[0]
    assert r["body"] == "cart items fetched"
    assert r["severity_number"] == 9
    assert r["severity_text"] == "INFO"
    assert r["service_name"] == "cart"
    assert r["scope_name"] == "cartservice"
    assert r["trace_id"] == "aabbccdd" * 4
    assert r["log_attributes"] == {"http.method": "GET"}


def test_normalise_logs_no_trace_context():
    """Logs without trace context store None for trace_id and span_id."""
    lr = LogRecord(time_unix_nano=1, body=AnyValue(string_value="hello"))
    rl = ResourceLogs(scope_logs=[ScopeLogs(log_records=[lr])])

    rows = normalise_logs([rl])
    r = rows[0]

    assert r["trace_id"] is None
    assert r["span_id"] is None


def test_normalise_logs_empty_returns_empty():
    assert normalise_logs([]) == []
