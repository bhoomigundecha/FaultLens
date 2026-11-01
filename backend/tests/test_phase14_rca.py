"""
FaultLens Backend — Phase 14 Tests: Root Cause Analysis

Tests:
  - backward_graph_traversal: pure function, all cases
  - _build_propagation_path: correct BFS ordering
  - GET /api/v1/rca/{id}: shape + 404
  - POST /api/v1/rca/run: endpoint exists + returns empty when no incidents
  - POST /api/v1/rca/{id}/run: 404 for unknown incident
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.services.rca import (
    backward_graph_traversal,
    _build_propagation_path,
    _Graph,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helper — build a _Graph from edge list
# ─────────────────────────────────────────────────────────────────────────────

def _make_graph(edges: list[tuple[str, str]]) -> _Graph:
    g = _Graph()
    for src, tgt in edges:
        g.add_edge(src, tgt)
    return g


# ─────────────────────────────────────────────────────────────────────────────
# Unit tests — backward_graph_traversal (pure Python)
# ─────────────────────────────────────────────────────────────────────────────

def test_rca_no_anomalies_returns_none():
    """Empty anomalous_services → None."""
    g = _make_graph([("frontend", "cart"), ("cart", "payment")])
    assert backward_graph_traversal(["payment"], set(), g) is None


def test_rca_single_service_no_graph():
    """Single anomalous service, no graph → score 1.0 (no callers)."""
    g = _Graph()   # empty graph
    result = backward_graph_traversal(["payment"], {"payment"}, g)
    assert result is not None
    assert result.root_cause_service == "payment"
    assert result.confidence         == 1.0


def test_rca_root_cause_at_leaf():
    """
    Graph: frontend → cart → payment
    Anomalies: all three.
    payment has no anomalous callers (cart calls payment, not the other way).
    Wait — callers of payment = cart. cart IS anomalous → payment scores 0.5.
    callers of cart = frontend → frontend IS anomalous → cart scores 0.5.
    callers of frontend = none → frontend scores 1.0 → root cause.
    """
    g = _make_graph([
        ("frontend", "cart"),
        ("cart",     "payment"),
    ])
    anomalous = {"frontend", "cart", "payment"}
    result = backward_graph_traversal(["payment"], anomalous, g)
    assert result is not None
    assert result.root_cause_service == "frontend"
    assert result.confidence         == 1.0


def test_rca_isolated_anomalous_service_scores_1():
    """
    Graph: frontend → cart → payment
    Anomalies: payment only.
    payment's caller (cart) is NOT anomalous → payment scores 1.0.
    """
    g = _make_graph([
        ("frontend", "cart"),
        ("cart",     "payment"),
    ])
    result = backward_graph_traversal(["payment"], {"payment"}, g)
    assert result is not None
    assert result.root_cause_service == "payment"
    assert result.confidence         == 1.0


def test_rca_victim_scores_lower():
    """
    Graph: payment → checkout
    Anomalies: payment, checkout.
    checkout's caller (payment) IS anomalous → checkout scores 0.5.
    payment's callers: none → payment scores 1.0.
    """
    g = _make_graph([("payment", "checkout")])
    result = backward_graph_traversal(["checkout"], {"payment", "checkout"}, g)
    assert result is not None
    assert result.root_cause_service == "payment"
    assert result.candidate_scores["payment"]  == 1.0
    assert result.candidate_scores["checkout"] == 0.5


def test_rca_propagation_path_ordered():
    """
    Graph: A → B → C, all anomalous.
    Root = A. Path should start with A.
    """
    g = _make_graph([("A", "B"), ("B", "C")])
    result = backward_graph_traversal(["C"], {"A", "B", "C"}, g)
    assert result is not None
    assert result.propagation_path[0] == "A"   # root cause first
    assert "B" in result.propagation_path
    assert "C" in result.propagation_path


def test_rca_candidate_scores_present():
    """candidate_scores contains entries for all anomalous services."""
    g = _make_graph([("X", "Y")])
    result = backward_graph_traversal(["Y"], {"X", "Y"}, g)
    assert result is not None
    assert "X" in result.candidate_scores
    assert "Y" in result.candidate_scores


def test_rca_disjoint_anomalies_both_score_1():
    """
    Two anomalous services with no graph connection → both score 1.0.
    First alphabetically is picked.
    """
    g = _Graph()  # no edges
    result = backward_graph_traversal(["alpha", "beta"], {"alpha", "beta"}, g)
    assert result is not None
    # Both score 1.0; alphabetically "alpha" wins
    assert result.confidence == 1.0


# ── _build_propagation_path ───────────────────────────────────────────────────

def test_propagation_path_linear():
    g = _make_graph([("A", "B"), ("B", "C")])
    path = _build_propagation_path("A", ["C"], g, {"A", "B", "C"})
    assert path == ["A", "B", "C"]


def test_propagation_path_includes_unconnected_affected():
    """Affected services not reachable via graph still appear in path."""
    g = _Graph()   # no edges
    path = _build_propagation_path("X", ["Y"], g, {"X", "Y"})
    assert "X" in path
    assert "Y" in path


# ─────────────────────────────────────────────────────────────────────────────
# API tests — mocked DB
# ─────────────────────────────────────────────────────────────────────────────

def _mock_rca(incident_id=1, root="payment", confidence=1.0,
              path=None, scores=None):
    r = MagicMock()
    r.id                  = 1
    r.incident_id         = incident_id
    r.root_cause_service  = root
    r.confidence          = confidence
    r.propagation_path    = path or ["payment"]
    r.candidate_scores    = scores or {"payment": 1.0}
    r.algorithm           = "backward_graph_traversal"
    r.created_at_unix_nano = 1_000_000_000_000
    return r


@pytest.mark.asyncio
async def test_get_rca_shape():
    """GET /api/v1/rca/{id} returns correct fields."""
    from app.db.session import get_db

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = _mock_rca(
        incident_id=42,
        root="payment",
        confidence=1.0,
        path=["payment", "checkout"],
        scores={"payment": 1.0, "checkout": 0.5},
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
            resp = await client.get("/api/v1/rca/42")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 200
    data = resp.json()
    assert data["incident_id"]        == 42
    assert data["root_cause_service"] == "payment"
    assert data["confidence"]         == pytest.approx(1.0)
    assert data["propagation_path"]   == ["payment", "checkout"]
    assert "candidate_scores"         in data
    assert "created_at_ms"            in data


@pytest.mark.asyncio
async def test_get_rca_not_found():
    """GET /api/v1/rca/{id} returns 404 if no RCA run yet."""
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
            resp = await client.get("/api/v1/rca/999")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 404
    assert "999" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_rca_run_all_no_incidents():
    """POST /api/v1/rca/run returns processed=0 when no open incidents."""
    from app.db.session import get_db

    # run_rca_for_all_open: queries open incidents → empty
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
            resp = await client.post("/api/v1/rca/run")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 200
    data = resp.json()
    assert data["processed"] == 0
    assert data["results"]   == []


@pytest.mark.asyncio
async def test_rca_run_single_not_found():
    """POST /api/v1/rca/{id}/run returns 404 for unknown incident."""
    from app.db.session import get_db

    # run_rca_for_incident: first query is for the Incident → not found
    empty = MagicMock()
    empty.scalar_one_or_none.return_value = None
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
            resp = await client.post("/api/v1/rca/999/run")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 404
