"""
FaultLens Backend — Phase 9 Tests: Service Discovery

Tests:
  - _aggregate_spans correctly groups and counts spans
  - upsert logic (mocked DB) — services are registered from span batches
  - GET /api/v1/services returns discovered services
  - GET /api/v1/services/{name} returns detail / 404
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.services.discovery import _aggregate_spans, _service_names_from_rows


# ─────────────────────────────────────────────────────────────────────────────
# Unit tests — pure Python, no DB
# ─────────────────────────────────────────────────────────────────────────────

def test_aggregate_spans_counts_requests():
    rows = [
        {"service_name": "checkout", "start_time_unix_nano": 1000, "status_code": 1},
        {"service_name": "checkout", "start_time_unix_nano": 2000, "status_code": 1},
        {"service_name": "payment",  "start_time_unix_nano": 1500, "status_code": 1},
    ]
    agg = _aggregate_spans(rows)
    assert agg["checkout"]["requests"] == 2
    assert agg["checkout"]["errors"]   == 0
    assert agg["payment"]["requests"]  == 1


def test_aggregate_spans_counts_errors():
    rows = [
        {"service_name": "payment", "start_time_unix_nano": 1000, "status_code": 2},  # ERROR
        {"service_name": "payment", "start_time_unix_nano": 2000, "status_code": 1},
    ]
    agg = _aggregate_spans(rows)
    assert agg["payment"]["errors"]   == 1
    assert agg["payment"]["requests"] == 2


def test_aggregate_spans_tracks_timestamps():
    rows = [
        {"service_name": "cart", "start_time_unix_nano": 500,  "status_code": 1},
        {"service_name": "cart", "start_time_unix_nano": 9000, "status_code": 1},
        {"service_name": "cart", "start_time_unix_nano": 3000, "status_code": 1},
    ]
    agg = _aggregate_spans(rows)
    assert agg["cart"]["min_nano"] == 500
    assert agg["cart"]["max_nano"] == 9000


def test_aggregate_spans_skips_missing_service():
    rows = [
        {"service_name": None,      "start_time_unix_nano": 1000, "status_code": 1},
        {"service_name": "",        "start_time_unix_nano": 1000, "status_code": 1},
        {"start_time_unix_nano": 1000, "status_code": 1},  # no key at all
    ]
    agg = _aggregate_spans(rows)
    assert len(agg) == 0


def test_aggregate_spans_empty():
    assert _aggregate_spans([]) == {}


def test_service_names_from_rows_extracts_latest():
    rows = [
        {"service_name": "frontend", "time_unix_nano": 1000},
        {"service_name": "frontend", "time_unix_nano": 5000},
        {"service_name": "ad",       "time_unix_nano": 2000},
    ]
    seen = _service_names_from_rows(rows)
    assert seen["frontend"] == 5000
    assert seen["ad"]       == 2000


# ─────────────────────────────────────────────────────────────────────────────
# API tests — mock DB
# ─────────────────────────────────────────────────────────────────────────────

def _make_service(name, request_count=100, error_count=5,
                  first_ns=1_000_000_000, last_ns=9_000_000_000):
    """Build a mock Service ORM object."""
    svc = MagicMock()
    svc.name              = name
    svc.request_count     = request_count
    svc.error_count       = error_count
    svc.first_seen_unix_nano = first_ns
    svc.last_seen_unix_nano  = last_ns
    return svc


@pytest.mark.asyncio
async def test_list_services_returns_all():
    """GET /api/v1/services returns list with correct shape."""
    from app.db.session import get_db

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [
        _make_service("frontend"),
        _make_service("cart"),
    ]
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/v1/services")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    names = [s["name"] for s in data["services"]]
    assert "frontend" in names
    assert "cart" in names


@pytest.mark.asyncio
async def test_list_services_shape():
    """Test response shape with mocked dependency."""
    from app.api.v1.services import _service_to_dict
    svc = _make_service("payment", request_count=200, error_count=10)
    d = _service_to_dict(svc)

    assert d["name"]          == "payment"
    assert d["request_count"] == 200
    assert d["error_count"]   == 10
    assert d["error_rate"]    == pytest.approx(10 / 200, rel=1e-3)
    assert "first_seen_ms" in d
    assert "last_seen_ms"  in d


@pytest.mark.asyncio
async def test_service_to_dict_zero_requests():
    """error_rate must be 0.0 when there are no requests (avoid division by zero)."""
    from app.api.v1.services import _service_to_dict
    svc = _make_service("empty-service", request_count=0, error_count=0)
    d = _service_to_dict(svc)
    assert d["error_rate"] == 0.0


@pytest.mark.asyncio
async def test_services_endpoint_exists():
    """GET /api/v1/services returns 200 with empty list when no services exist."""
    from app.db.session import get_db

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/v1/services")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 200
    assert resp.json()["total"] == 0
    assert resp.json()["services"] == []


@pytest.mark.asyncio
async def test_service_detail_endpoint_exists():
    """GET /api/v1/services/{name} returns 404 when service is unknown (no DB data)."""
    from app.db.session import get_db

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None  # service not found
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/v1/services/nonexistent")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 404
    assert "nonexistent" in resp.json()["detail"]
