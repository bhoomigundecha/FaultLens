"""
FaultLens Backend — Phase 10 Tests: Dependency Graph

Tests:
  - extract_dependencies: pure-Python edge detection (no DB)
  - upsert_dependencies: mocked DB session
  - GET /api/v1/dependencies: response shape with mocked DB
  - GET /api/v1/dependencies/{source}/{target}: detail + 404
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.services.graph import extract_dependencies, _Edge


# ─────────────────────────────────────────────────────────────────────────────
# Unit tests — extract_dependencies (pure Python, no DB)
# ─────────────────────────────────────────────────────────────────────────────

def _span(span_id, parent_span_id, service, status_code=1, ts=1000):
    return {
        "span_id":               span_id,
        "parent_span_id":        parent_span_id,
        "service_name":          service,
        "status_code":           status_code,
        "start_time_unix_nano":  ts,
    }


def test_extract_finds_cross_service_edge():
    rows = [
        _span("aaa", None,   "frontend"),           # root span
        _span("bbb", "aaa",  "cart",     ts=2000),  # frontend → cart
    ]
    edges = extract_dependencies(rows)
    assert len(edges) == 1
    assert edges[0].source == "frontend"
    assert edges[0].target == "cart"


def test_extract_ignores_same_service_parent():
    """Same-service parent→child spans are NOT a dependency edge."""
    rows = [
        _span("aaa", None,  "cart"),
        _span("bbb", "aaa", "cart"),  # same service — skip
    ]
    assert extract_dependencies(rows) == []


def test_extract_ignores_missing_parent():
    """Parent span not in batch — skip gracefully."""
    rows = [
        _span("bbb", "DEADBEEF", "payment"),  # parent not in batch
    ]
    assert extract_dependencies(rows) == []


def test_extract_counts_requests():
    rows = [
        _span("a1", None,  "checkout"),
        _span("b1", "a1", "payment", ts=1000),
        _span("b2", "a1", "payment", ts=2000),
    ]
    edges = extract_dependencies(rows)
    assert len(edges) == 1
    assert edges[0].requests == 2


def test_extract_counts_errors():
    rows = [
        _span("a1", None,  "checkout"),
        _span("b1", "a1", "payment", status_code=2, ts=1000),  # ERROR
        _span("b2", "a1", "payment", status_code=1, ts=2000),  # OK
    ]
    edges = extract_dependencies(rows)
    assert edges[0].errors   == 1
    assert edges[0].requests == 2


def test_extract_tracks_timestamps():
    rows = [
        _span("a1", None,  "frontend"),
        _span("b1", "a1", "cart", ts=5000),
        _span("b2", "a1", "cart", ts=1000),
        _span("b3", "a1", "cart", ts=9000),
    ]
    edges = extract_dependencies(rows)
    assert edges[0].min_ns == 1000
    assert edges[0].max_ns == 9000


def test_extract_multiple_edges():
    """Several cross-service pairs in one batch."""
    rows = [
        _span("r1", None,  "api-gateway"),
        _span("s1", "r1", "cart"),
        _span("s2", "r1", "inventory"),
        _span("s3", "r1", "payment"),
    ]
    edges = extract_dependencies(rows)
    pairs = {(e.source, e.target) for e in edges}
    assert ("api-gateway", "cart")      in pairs
    assert ("api-gateway", "inventory") in pairs
    assert ("api-gateway", "payment")   in pairs


def test_extract_empty_returns_empty():
    assert extract_dependencies([]) == []


def test_extract_no_parent_span_ids():
    """All root spans — no edges."""
    rows = [
        _span("a", None, "svc-a"),
        _span("b", None, "svc-b"),
    ]
    assert extract_dependencies(rows) == []


# ─────────────────────────────────────────────────────────────────────────────
# API tests — mocked DB via dependency_overrides
# ─────────────────────────────────────────────────────────────────────────────

def _make_dep(source, target, req=100, err=5,
              first_ns=1_000_000_000, last_ns=9_000_000_000):
    d = MagicMock()
    d.source_service      = source
    d.target_service      = target
    d.request_count       = req
    d.error_count         = err
    d.first_seen_unix_nano = first_ns
    d.last_seen_unix_nano  = last_ns
    return d


@pytest.mark.asyncio
async def test_get_dependencies_shape():
    """GET /api/v1/dependencies returns nodes + edges."""
    from app.db.session import get_db

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [
        _make_dep("frontend", "cart"),
        _make_dep("frontend", "payment"),
        _make_dep("cart",     "inventory"),
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
            resp = await client.get("/api/v1/dependencies")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 200
    data = resp.json()
    assert data["edge_count"] == 3
    # unique nodes: frontend, cart, payment, inventory = 4
    assert data["node_count"] == 4
    assert "frontend"  in data["nodes"]
    assert "inventory" in data["nodes"]
    edges = data["edges"]
    assert len(edges) == 3
    assert all("source" in e and "target" in e for e in edges)
    assert all("error_rate" in e for e in edges)


@pytest.mark.asyncio
async def test_get_dependencies_empty():
    """Empty graph returns correct shape."""
    from app.db.session import get_db

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)

    async def override():
        yield mock_db

    app.dependency_overrides[get_db] = override
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/v1/dependencies")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 200
    data = resp.json()
    assert data["edge_count"] == 0
    assert data["node_count"] == 0
    assert data["nodes"] == []
    assert data["edges"] == []


@pytest.mark.asyncio
async def test_get_dependency_detail():
    """GET /api/v1/dependencies/{source}/{target} returns edge detail."""
    from app.db.session import get_db

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = _make_dep(
        "checkout", "payment", req=500, err=25
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
            resp = await client.get("/api/v1/dependencies/checkout/payment")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 200
    data = resp.json()
    assert data["source"]        == "checkout"
    assert data["target"]        == "payment"
    assert data["request_count"] == 500
    assert data["error_count"]   == 25
    assert data["error_rate"]    == pytest.approx(25 / 500, rel=1e-3)


@pytest.mark.asyncio
async def test_get_dependency_not_found():
    """Returns 404 when pair has never been seen."""
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
            resp = await client.get("/api/v1/dependencies/ghost/nowhere")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 404
    assert "ghost" in resp.json()["detail"]
