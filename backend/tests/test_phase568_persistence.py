"""
FaultLens Backend — Phase 5/6/8 Tests: Telemetry Persistence

Tests that the OTLP ingest endpoints actually write rows to PostgreSQL.

Strategy:
  - We override the ingest `ingest_session` hook with a shared async session.
  - The endpoint writes rows and flushes; the test then queries using the same
    session (within the same transaction) to see the new rows.
  - At the end the session is rolled back so the DB stays clean.

Skip gracefully when PostgreSQL is unreachable.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import MagicMock, AsyncMock

from app.main import app
from app.db.session import get_db  # noqa: F401
from app.api.v1.ingest import ingest_session


# ── DB availability check ─────────────────────────────────────────────────────

async def _db_available() -> bool:
    try:
        from app.db.session import check_db
        return await check_db()
    except Exception:
        return False


# ── Payload builders ──────────────────────────────────────────────────────────

PROTO_CT = "application/x-protobuf"


def _trace_body(num_spans: int = 2) -> bytes:
    from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
        ExportTraceServiceRequest,
    )
    from opentelemetry.proto.trace.v1.trace_pb2 import ResourceSpans, ScopeSpans, Span
    from opentelemetry.proto.resource.v1.resource_pb2 import Resource
    from opentelemetry.proto.common.v1.common_pb2 import AnyValue, KeyValue

    spans = [
        Span(
            trace_id=bytes.fromhex("aabbccdd" * 4),
            span_id=i.to_bytes(8, "big"),
            name=f"op-{i}",
            start_time_unix_nano=i * 1_000_000,
            end_time_unix_nano=(i + 1) * 1_000_000,
        )
        for i in range(1, num_spans + 1)
    ]
    resource = Resource(attributes=[
        KeyValue(key="service.name", value=AnyValue(string_value="test-svc"))
    ])
    req = ExportTraceServiceRequest(
        resource_spans=[ResourceSpans(resource=resource,
                                      scope_spans=[ScopeSpans(spans=spans)])]
    )
    return req.SerializeToString()


def _metrics_body(num_points: int = 3) -> bytes:
    from opentelemetry.proto.collector.metrics.v1.metrics_service_pb2 import (
        ExportMetricsServiceRequest,
    )
    from opentelemetry.proto.metrics.v1.metrics_pb2 import (
        ResourceMetrics, ScopeMetrics, Metric, Gauge, NumberDataPoint,
    )
    from opentelemetry.proto.resource.v1.resource_pb2 import Resource
    from opentelemetry.proto.common.v1.common_pb2 import AnyValue, KeyValue

    dps = [NumberDataPoint(time_unix_nano=i * 1_000, as_double=float(i))
           for i in range(1, num_points + 1)]
    resource = Resource(attributes=[
        KeyValue(key="service.name", value=AnyValue(string_value="test-svc"))
    ])
    req = ExportMetricsServiceRequest(
        resource_metrics=[ResourceMetrics(resource=resource,
            scope_metrics=[ScopeMetrics(
                metrics=[Metric(name="test.gauge", gauge=Gauge(data_points=dps))]
            )]
        )]
    )
    return req.SerializeToString()


def _logs_body(num_records: int = 2) -> bytes:
    from opentelemetry.proto.collector.logs.v1.logs_service_pb2 import (
        ExportLogsServiceRequest,
    )
    from opentelemetry.proto.logs.v1.logs_pb2 import ResourceLogs, ScopeLogs, LogRecord
    from opentelemetry.proto.resource.v1.resource_pb2 import Resource
    from opentelemetry.proto.common.v1.common_pb2 import AnyValue, KeyValue

    records = [
        LogRecord(time_unix_nano=i * 1_000, body=AnyValue(string_value=f"log-{i}"))
        for i in range(1, num_records + 1)
    ]
    resource = Resource(attributes=[
        KeyValue(key="service.name", value=AnyValue(string_value="test-svc"))
    ])
    req = ExportLogsServiceRequest(
        resource_logs=[ResourceLogs(resource=resource,
                                    scope_logs=[ScopeLogs(log_records=records)])]
    )
    return req.SerializeToString()


# ── Persistence helpers ───────────────────────────────────────────────────────

async def _post(path: str, body: bytes) -> int:
    """POST body to path, return status code."""
    async with AsyncClient(transport=ASGITransport(app=app),
                           base_url="http://test") as client:
        r = await client.post(path, content=body,
                              headers={"content-type": PROTO_CT})
    return r.status_code


# ── Persistence tests ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_traces_persisted_to_db():
    """POST /otlp/v1/traces → Span rows appear in the DB (rolled back after)."""
    if not await _db_available():
        pytest.skip("PostgreSQL not reachable")

    from sqlalchemy import text, select, func
    from app.db.session import AsyncSessionLocal
    from app.models.telemetry import Span

    async with AsyncSessionLocal() as session:
        # Inject this session into the endpoint
        async def _override():
            yield session

        app.dependency_overrides[ingest_session] = _override
        try:
            status = await _post("/otlp/v1/traces", _trace_body(num_spans=3))
        finally:
            app.dependency_overrides.clear()

        assert status == 200

        # Flush so the ORM objects are visible within the same session
        await session.flush()

        count = (await session.execute(
            select(func.count()).select_from(Span).where(
                Span.service_name == "test-svc"
            )
        )).scalar()
        assert count == 3

        # Roll back — leave no trace in the DB
        await session.rollback()


@pytest.mark.asyncio
async def test_metrics_persisted_to_db():
    """POST /otlp/v1/metrics → MetricPoint rows appear in the DB."""
    if not await _db_available():
        pytest.skip("PostgreSQL not reachable")

    from sqlalchemy import select, func
    from app.db.session import AsyncSessionLocal
    from app.models.telemetry import MetricPoint

    async with AsyncSessionLocal() as session:
        async def _override():
            yield session

        app.dependency_overrides[ingest_session] = _override
        try:
            status = await _post("/otlp/v1/metrics", _metrics_body(num_points=4))
        finally:
            app.dependency_overrides.clear()

        assert status == 200
        await session.flush()

        count = (await session.execute(
            select(func.count()).select_from(MetricPoint).where(
                MetricPoint.service_name == "test-svc"
            )
        )).scalar()
        assert count == 4

        await session.rollback()


@pytest.mark.asyncio
async def test_logs_persisted_to_db():
    """POST /otlp/v1/logs → LogRecord rows appear in the DB."""
    if not await _db_available():
        pytest.skip("PostgreSQL not reachable")

    from sqlalchemy import select, func
    from app.db.session import AsyncSessionLocal
    from app.models.telemetry import LogRecord

    async with AsyncSessionLocal() as session:
        async def _override():
            yield session

        app.dependency_overrides[ingest_session] = _override
        try:
            status = await _post("/otlp/v1/logs", _logs_body(num_records=5))
        finally:
            app.dependency_overrides.clear()

        assert status == 200
        await session.flush()

        count = (await session.execute(
            select(func.count()).select_from(LogRecord).where(
                LogRecord.service_name == "test-svc"
            )
        )).scalar()
        assert count == 5

        await session.rollback()


# ── Unit-level: endpoints still 200 with no real DB ──────────────────────────

@pytest.mark.asyncio
async def test_ingest_returns_200_with_mocked_db():
    """Even with a no-op DB session all three endpoints return 200."""
    # Fake session: records the rows passed to each bulk INSERT, ignores upserts.
    from contextlib import asynccontextmanager
    from sqlalchemy.sql.dml import Insert
    collected: list = []

    class _FakeSession:
        @asynccontextmanager
        async def begin_nested(self):
            yield
        async def execute(self, stmt, params=None):
            if isinstance(stmt, Insert):
                collected.extend(params or [])
        async def rollback(self): pass

    async def _override():
        yield _FakeSession()

    app.dependency_overrides[ingest_session] = _override
    try:
        async with AsyncClient(transport=ASGITransport(app=app),
                               base_url="http://test") as client:
            r_traces  = await client.post("/otlp/v1/traces",
                            content=_trace_body(1),
                            headers={"content-type": PROTO_CT})
            r_metrics = await client.post("/otlp/v1/metrics",
                            content=_metrics_body(1),
                            headers={"content-type": PROTO_CT})
            r_logs    = await client.post("/otlp/v1/logs",
                            content=_logs_body(1),
                            headers={"content-type": PROTO_CT})
    finally:
        app.dependency_overrides.clear()

    assert r_traces.status_code  == 200
    assert r_metrics.status_code == 200
    assert r_logs.status_code    == 200
    # bulk INSERT received normalised rows for every signal
    assert len(collected) == 3  # 1 span + 1 metric_point + 1 log_record
