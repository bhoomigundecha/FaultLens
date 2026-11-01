"""
FaultLens Backend — Phase 11 Tests: Telemetry Correlation

Tests:
  - correlation helpers: _span_to_dict, _log_to_dict, _metric_to_dict
  - correlate_trace returns None for unknown trace
  - correlate_trace aggregates spans correctly
  - GET /api/v1/traces: list shape with mocked DB
  - GET /api/v1/traces/{trace_id}: correlated context + 404
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.services.correlation import (
    _span_to_dict,
    _log_to_dict,
    _metric_to_dict,
    correlate_trace,
)

_NS_PER_MS = 1_000_000


# ─────────────────────────────────────────────────────────────────────────────
# Helper factories
# ─────────────────────────────────────────────────────────────────────────────

def _mock_span(span_id="abc", parent_span_id=None, service="frontend",
               name="GET /", kind=2, status_code=1, status_msg=None,
               start_ns=1_000_000_000, end_ns=2_000_000_000):
    s = MagicMock()
    s.span_id              = span_id
    s.parent_span_id       = parent_span_id
    s.name                 = name
    s.service_name         = service
    s.kind                 = kind
    s.status_code          = status_code
    s.status_message       = status_msg
    s.start_time_unix_nano = start_ns
    s.end_time_unix_nano   = end_ns
    s.span_attributes      = {}
    s.resource_attributes  = {}
    return s


def _mock_log(trace_id="tid", span_id="abc", service="frontend",
              body="hello", sev_num=9, sev_text="INFO",
              time_ns=1_500_000_000):
    lr = MagicMock()
    lr.trace_id        = trace_id
    lr.span_id         = span_id
    lr.service_name    = service
    lr.body            = body
    lr.severity_number = sev_num
    lr.severity_text   = sev_text
    lr.time_unix_nano  = time_ns
    lr.log_attributes  = {}
    return lr


def _mock_metric(name="http.request.duration", svc="frontend",
                 metric_type="histogram", time_ns=1_500_000_000):
    mp = MagicMock()
    mp.metric_name           = name
    mp.metric_type           = metric_type
    mp.metric_unit           = "ms"
    mp.service_name          = svc
    mp.time_unix_nano        = time_ns
    mp.value_double          = None
    mp.value_int             = None
    mp.hist_count            = 42
    mp.data_point_attributes = {}
    return mp


# ─────────────────────────────────────────────────────────────────────────────
# Unit tests — dict serialisation helpers
# ─────────────────────────────────────────────────────────────────────────────

def test_span_to_dict_fields():
    s = _mock_span(start_ns=1_000_000_000, end_ns=3_000_000_000)
    d = _span_to_dict(s)
    assert d["span_id"]     == "abc"
    assert d["service_name"] == "frontend"
    assert d["start_ms"]    == 1_000       # 1_000_000_000 ns / 1_000_000
    assert d["end_ms"]      == 3_000
    assert d["duration_ms"] == pytest.approx(2_000.0)


def test_span_to_dict_error_status():
    s = _mock_span(status_code=2, status_msg="connection timeout")
    d = _span_to_dict(s)
    assert d["status_code"]    == 2
    assert d["status_message"] == "connection timeout"


def test_log_to_dict_fields():
    lr = _mock_log(body="order placed", time_ns=5_000_000_000)
    d = _log_to_dict(lr)
    assert d["body"]     == "order placed"
    assert d["time_ms"]  == 5_000
    assert d["severity_text"] == "INFO"


def test_metric_to_dict_fields():
    mp = _mock_metric(name="http.server.request.duration", time_ns=2_000_000_000)
    d = _metric_to_dict(mp)
    assert d["metric_name"] == "http.server.request.duration"
    assert d["time_ms"]     == 2_000
    assert d["hist_count"]  == 42


# ─────────────────────────────────────────────────────────────────────────────
# Unit tests — correlate_trace (mocked DB)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_correlate_trace_unknown_returns_none():
    """Unknown trace_id → None."""
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    db = AsyncMock()
    db.execute = AsyncMock(return_value=mock_result)

    result = await correlate_trace(db, "deadbeef", window_ns=1_000)
    assert result is None


@pytest.mark.asyncio
async def test_correlate_trace_returns_context():
    """Known trace returns all three signal types."""
    span     = _mock_span(span_id="s1", start_ns=1_000_000_000, end_ns=2_000_000_000)
    log      = _mock_log(time_ns=1_500_000_000)
    metric   = _mock_metric(time_ns=1_500_000_000)

    spans_result  = MagicMock(); spans_result.scalars.return_value.all.return_value  = [span]
    logs_result   = MagicMock(); logs_result.scalars.return_value.all.return_value   = [log]
    metrics_result = MagicMock(); metrics_result.scalars.return_value.all.return_value = [metric]

    db = AsyncMock()
    db.execute = AsyncMock(side_effect=[spans_result, logs_result, metrics_result])

    ctx = await correlate_trace(db, "tid", window_ns=30_000_000_000)

    assert ctx is not None
    assert ctx["trace_id"]    == "tid"
    assert ctx["span_count"]  == 1
    assert ctx["log_count"]   == 1
    assert ctx["metric_count"] == 1
    assert ctx["services"]    == ["frontend"]
    assert ctx["duration_ms"] == pytest.approx(1_000.0)


@pytest.mark.asyncio
async def test_correlate_trace_error_count():
    """error_span_count reflects spans with status_code == 2."""
    span_ok  = _mock_span(span_id="ok",  status_code=1)
    span_err = _mock_span(span_id="err", status_code=2)

    spans_r  = MagicMock(); spans_r.scalars.return_value.all.return_value  = [span_ok, span_err]
    logs_r   = MagicMock(); logs_r.scalars.return_value.all.return_value   = []
    metrics_r = MagicMock(); metrics_r.scalars.return_value.all.return_value = []

    db = AsyncMock()
    db.execute = AsyncMock(side_effect=[spans_r, logs_r, metrics_r])

    ctx = await correlate_trace(db, "tid", window_ns=1_000)
    assert ctx["error_span_count"] == 1
    assert ctx["span_count"]       == 2


# ─────────────────────────────────────────────────────────────────────────────
# API tests — mocked via dependency_overrides
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_traces_shape():
    """GET /api/v1/traces returns list with correct fields."""
    from app.db.session import get_db

    row = MagicMock()
    row.trace_id   = "abc123"
    row.start_ns   = 1_000_000_000
    row.end_ns     = 3_000_000_000
    row.span_count = 5
    row.has_error  = False

    mock_result = MagicMock()
    mock_result.all.return_value = [row]
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)

    async def override():
        yield mock_db

    app.dependency_overrides[get_db] = override
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/v1/traces")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 1
    t = data["traces"][0]
    assert t["trace_id"]    == "abc123"
    assert t["span_count"]  == 5
    assert t["has_error"]   is False
    assert t["duration_ms"] == pytest.approx(2_000.0)


@pytest.mark.asyncio
async def test_list_traces_empty():
    """Empty spans table returns empty list."""
    from app.db.session import get_db

    mock_result = MagicMock()
    mock_result.all.return_value = []
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)

    async def override():
        yield mock_db

    app.dependency_overrides[get_db] = override
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/v1/traces")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 200
    assert resp.json()["count"] == 0


@pytest.mark.asyncio
async def test_get_trace_not_found():
    """Unknown trace returns 404."""
    from app.db.session import get_db

    # First execute call (get_trace_spans) returns no spans → correlate returns None
    empty = MagicMock(); empty.scalars.return_value.all.return_value = []
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=empty)

    async def override():
        yield mock_db

    app.dependency_overrides[get_db] = override
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/v1/traces/nonexistent-trace-id")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 404
    assert "nonexistent-trace-id" in resp.json()["detail"]
