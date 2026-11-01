"""
FaultLens Backend — Phase 16 Tests: Frontend Dashboard API

Tests:
  - GET /api/v1/dashboard: returns all top-level keys, correct counts
  - GET /api/v1/dashboard/incident/{id}: shape + 404
  - _service_health: correct status derivation
  - _incident_dict: with and without RCA
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.api.v1.dashboard import _service_health, _incident_dict


# ─────────────────────────────────────────────────────────────────────────────
# Unit tests — helpers
# ─────────────────────────────────────────────────────────────────────────────

def _mock_svc(name="payment", req=1000, err=50, last_ns=1_000_000_000_000):
    s = MagicMock()
    s.name               = name
    s.request_count      = req
    s.error_count        = err
    s.last_seen_unix_nano = last_ns
    return s


def _mock_inc(id=1, title="payment: down", severity="critical",
              status="open", services=None, rule="SERVICE_DOWN",
              desc="desc", created_ns=1_000_000_000_000):
    inc = MagicMock()
    inc.id                    = id
    inc.title                 = title
    inc.severity              = severity
    inc.status                = status
    inc.affected_services     = services or ["payment"]
    inc.triggered_by_rule     = rule
    inc.description           = desc
    inc.created_at_unix_nano  = created_ns
    inc.resolved_at_unix_nano = None
    return inc


def _mock_rca(root="payment", conf=1.0, path=None):
    r = MagicMock()
    r.root_cause_service = root
    r.confidence         = conf
    r.propagation_path   = path or ["payment"]
    return r


def test_service_health_healthy():
    svc = _mock_svc("frontend")
    assert _service_health(svc, set(), set()) == "healthy"


def test_service_health_degraded():
    svc = _mock_svc("cart")
    assert _service_health(svc, {"cart"}, set()) == "degraded"


def test_service_health_critical():
    svc = _mock_svc("payment")
    assert _service_health(svc, {"payment"}, {"payment"}) == "critical"


def test_incident_dict_with_rca():
    inc = _mock_inc(id=1, severity="critical")
    rca = _mock_rca(root="payment", conf=1.0, path=["payment", "checkout"])
    d = _incident_dict(inc, rca)
    assert d["id"]       == 1
    assert d["severity"] == "critical"
    assert d["rca"]      is not None
    assert d["rca"]["root_cause_service"] == "payment"
    assert d["rca"]["confidence"]         == pytest.approx(1.0)


def test_incident_dict_without_rca():
    inc = _mock_inc(id=2, severity="high")
    d = _incident_dict(inc, None)
    assert d["rca"] is None


# ─────────────────────────────────────────────────────────────────────────────
# API tests
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_dashboard_shape():
    """GET /api/v1/dashboard returns all top-level keys."""
    from app.db.session import get_db

    inc = _mock_inc(id=1, severity="critical", services=["payment"])

    def _scalars_result(items):
        r = MagicMock()
        r.scalars.return_value.all.return_value = items
        return r

    def _scalar_result(val):
        r = MagicMock()
        r.scalar.return_value = val
        return r

    # DB calls in get_dashboard order:
    # 1. open incidents
    # 2. RCA for those incidents
    # 3. services
    # 4. anomaly count
    # 5. dependencies
    side_effects = [
        _scalars_result([inc]),       # open incidents
        _scalars_result([]),          # RCA rows
        _scalars_result([]),          # services
        _scalar_result(3),            # anomaly count
        _scalars_result([]),          # dependencies
    ]
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=side_effects)

    async def override():
        yield mock_db

    app.dependency_overrides[get_db] = override
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/v1/dashboard")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 200
    data = resp.json()

    for key in ("summary", "services", "incidents", "dependency_graph"):
        assert key in data, f"Missing key: {key}"

    s = data["summary"]
    assert s["open_incident_count"]  == 1
    assert s["active_anomaly_count"] == 3
    assert "service_count"           in s
    assert "healthy_count"           in s

    assert isinstance(data["incidents"], list)
    assert len(data["incidents"]) == 1
    assert data["incidents"][0]["severity"] == "critical"

    g = data["dependency_graph"]
    assert "nodes" in g
    assert "edges" in g


@pytest.mark.asyncio
async def test_dashboard_empty():
    """Dashboard works with no services, incidents or anomalies."""
    from app.db.session import get_db

    def _scalars_result(items):
        r = MagicMock()
        r.scalars.return_value.all.return_value = items
        return r

    def _scalar_result(val):
        r = MagicMock()
        r.scalar.return_value = val
        return r

    # When open_inc_ids is empty, the RCA query is SKIPPED (guarded by `if open_inc_ids`).
    # DB call order: incidents → services → anomaly_count → deps  (4 calls, not 5)
    side_effects = [
        _scalars_result([]),   # 1. open incidents → empty
        _scalars_result([]),   # 2. services
        _scalar_result(0),     # 3. anomaly count (scalar())
        _scalars_result([]),   # 4. deps
    ]
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=side_effects)

    async def override():
        yield mock_db

    app.dependency_overrides[get_db] = override
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/v1/dashboard")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 200
    d = resp.json()
    assert d["summary"]["service_count"]        == 0
    assert d["summary"]["open_incident_count"]  == 0
    assert d["summary"]["active_anomaly_count"] == 0


@pytest.mark.asyncio
async def test_dashboard_incident_not_found():
    """GET /api/v1/dashboard/incident/{id} returns 404 for unknown incident."""
    from app.db.session import get_db

    empty = MagicMock(); empty.scalar_one_or_none.return_value = None
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=empty)

    async def override():
        yield mock_db

    app.dependency_overrides[get_db] = override
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/v1/dashboard/incident/999")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_dashboard_incident_has_ai_slot():
    """GET /api/v1/dashboard/incident/{id} always includes ai_explanation key."""
    from app.db.session import get_db

    inc     = _mock_inc(id=1, services=["payment"])
    rca_row = _mock_rca(root="payment")

    def _make(scalar=None, scalars_list=None, all_list=None):
        r = MagicMock()
        r.scalar_one_or_none.return_value = scalar
        if scalars_list is not None:
            r.scalars.return_value.all.return_value = scalars_list
        if all_list is not None:
            r.all.return_value = all_list
        return r

    side_effects = [
        _make(scalar=inc),
        _make(scalar=rca_row),
        _make(scalars_list=[]),
        _make(scalars_list=[]),
        _make(all_list=[]),
        _make(all_list=[]),
        _make(scalar=None),    # AIExplanation lookup → None (not yet generated)
    ]
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=side_effects)

    async def override():
        yield mock_db

    app.dependency_overrides[get_db] = override
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/v1/dashboard/incident/1")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 200
    data = resp.json()
    assert "ai_explanation" in data
    assert data["ai_explanation"] is None
    assert data["ai_available"]   is False
