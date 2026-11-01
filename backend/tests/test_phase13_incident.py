"""
FaultLens Backend — Phase 13 Tests: Incident Engine

Tests:
  - _is_error_metric / _is_latency_metric: keyword matching
  - evaluate_rules: all 6 rules — pure Python, no DB
  - run_incident_engine: mocked DB
  - GET /api/v1/incidents: shape + severity ordering
  - GET /api/v1/incidents/{id}: detail + 404
  - POST /api/v1/incidents/run: route exists
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.services.incident import (
    evaluate_rules,
    _is_error_metric,
    _is_latency_metric,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helper — build mock Anomaly objects
# ─────────────────────────────────────────────────────────────────────────────

def _anomaly(id=1, service="payment", metric="http.error_rate",
             z=5.0, direction="spike", active=True,
             desc="payment: http.error_rate spike"):
    a = MagicMock()
    a.id           = id
    a.service_name = service
    a.metric_name  = metric
    a.z_score      = z
    a.direction    = direction
    a.is_active    = active
    a.description  = desc
    a.current_value   = 0.5
    a.baseline_mean   = 0.01
    a.baseline_stddev = 0.005
    return a


# ─────────────────────────────────────────────────────────────────────────────
# Unit tests — keyword helpers
# ─────────────────────────────────────────────────────────────────────────────

def test_is_error_metric_matches():
    assert _is_error_metric("http.server.error_rate")  is True
    assert _is_error_metric("rpc.failed_requests")     is True
    assert _is_error_metric("exception.count")         is True


def test_is_error_metric_no_match():
    assert _is_error_metric("http.server.duration") is False
    assert _is_error_metric("cpu.utilization")      is False


def test_is_latency_metric_matches():
    assert _is_latency_metric("http.server.duration")  is True
    assert _is_latency_metric("p99_latency")           is True
    assert _is_latency_metric("response_time_ms")      is True


def test_is_latency_metric_no_match():
    assert _is_latency_metric("error_rate")     is False
    assert _is_latency_metric("cpu_usage")      is False


# ─────────────────────────────────────────────────────────────────────────────
# Unit tests — evaluate_rules (pure Python, no DB)
# ─────────────────────────────────────────────────────────────────────────────

def test_rule_service_down():
    """Z ≥ 8 on error metric → SERVICE_DOWN / critical."""
    a = _anomaly(metric="http.error_rate", z=8.5)
    match = evaluate_rules("payment", [a])
    assert match is not None
    assert match.rule     == "SERVICE_DOWN"
    assert match.severity == "critical"
    assert "payment" in match.title


def test_rule_latency_spike_critical():
    """Z ≥ 8 on latency metric → LATENCY_SPIKE_CRITICAL / critical."""
    a = _anomaly(metric="http.server.duration", z=9.0)
    match = evaluate_rules("cart", [a])
    assert match.rule     == "LATENCY_SPIKE_CRITICAL"
    assert match.severity == "critical"


def test_rule_high_error_rate():
    """Z 3–8 on error metric → HIGH_ERROR_RATE / high."""
    a = _anomaly(metric="rpc.errors", z=4.2)
    match = evaluate_rules("checkout", [a])
    assert match.rule     == "HIGH_ERROR_RATE"
    assert match.severity == "high"


def test_rule_latency_spike_high():
    """Z 3–8 on latency metric → LATENCY_SPIKE_HIGH / high."""
    a = _anomaly(metric="response_time", z=5.0)
    match = evaluate_rules("frontend", [a])
    assert match.rule     == "LATENCY_SPIKE_HIGH"
    assert match.severity == "high"


def test_rule_multi_signal():
    """2+ non-error, non-latency anomalies → MULTI_SIGNAL / high."""
    a1 = _anomaly(id=1, metric="cpu.usage",    z=4.0)
    a2 = _anomaly(id=2, metric="memory.usage", z=3.5)
    match = evaluate_rules("inventory", [a1, a2])
    assert match.rule     == "MULTI_SIGNAL"
    assert match.severity == "high"


def test_rule_single_anomaly():
    """Single non-error, non-latency anomaly → SINGLE_ANOMALY / medium."""
    a = _anomaly(metric="cpu.usage", z=3.2)
    match = evaluate_rules("currency", [a])
    assert match.rule     == "SINGLE_ANOMALY"
    assert match.severity == "medium"


def test_no_anomalies_returns_none():
    assert evaluate_rules("payment", []) is None


def test_rule_priority_error_beats_latency():
    """Error rule fires before latency rule at same Z-score."""
    a_error   = _anomaly(id=1, metric="http.error_rate", z=8.5)
    a_latency = _anomaly(id=2, metric="http.duration",   z=8.5)
    match = evaluate_rules("payment", [a_error, a_latency])
    assert match.rule == "SERVICE_DOWN"   # error rule fires first


def test_description_contains_service_name():
    a = _anomaly(metric="http.error_rate", z=4.0)
    match = evaluate_rules("payment", [a])
    assert "payment" in match.description


# ─────────────────────────────────────────────────────────────────────────────
# API tests — mocked DB
# ─────────────────────────────────────────────────────────────────────────────

def _mock_incident(id=1, title="payment: down", severity="critical",
                   status="open", services=None, anomaly_ids=None,
                   rule="SERVICE_DOWN", created_ns=1_000_000_000_000):
    inc = MagicMock()
    inc.id                    = id
    inc.title                 = title
    inc.severity              = severity
    inc.status                = status
    inc.affected_services     = services or ["payment"]
    inc.anomaly_ids           = anomaly_ids or [1]
    inc.triggered_by_rule     = rule
    inc.description           = f"Incident: {title}"
    inc.created_at_unix_nano  = created_ns
    inc.resolved_at_unix_nano = None
    return inc


@pytest.mark.asyncio
async def test_list_incidents_severity_order():
    """GET /api/v1/incidents returns incidents sorted critical → high → medium."""
    from app.db.session import get_db

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [
        _mock_incident(id=1, severity="medium"),
        _mock_incident(id=2, severity="critical"),
        _mock_incident(id=3, severity="high"),
    ]
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)

    async def override():
        yield mock_db

    app.dependency_overrides[get_db] = override
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/v1/incidents")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 3
    severities = [i["severity"] for i in data["incidents"]]
    assert severities == ["critical", "high", "medium"]


@pytest.mark.asyncio
async def test_get_incident_detail():
    """GET /api/v1/incidents/{id} returns full detail."""
    from app.db.session import get_db

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = _mock_incident(
        id=42, severity="high", services=["checkout"], anomaly_ids=[7, 8]
    )
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)

    async def override():
        yield mock_db

    app.dependency_overrides[get_db] = override
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/v1/incidents/42")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 200
    data = resp.json()
    assert data["id"]                == 42
    assert data["severity"]          == "high"
    assert data["affected_services"] == ["checkout"]
    assert data["anomaly_ids"]       == [7, 8]


@pytest.mark.asyncio
async def test_get_incident_not_found():
    from app.db.session import get_db

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)

    async def override():
        yield mock_db

    app.dependency_overrides[get_db] = override
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/v1/incidents/999")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_run_incidents_endpoint():
    """POST /api/v1/incidents/run returns summary when no anomalies exist."""
    from app.db.session import get_db

    empty = MagicMock()
    empty.scalars.return_value.all.return_value = []
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=empty)
    mock_db.commit  = AsyncMock()

    async def override():
        yield mock_db

    app.dependency_overrides[get_db] = override
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post("/api/v1/incidents/run")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 200
    data = resp.json()
    assert data["incidents_created"]  == 0
    assert data["incidents_resolved"] == 0
