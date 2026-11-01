"""
FaultLens Backend — Phase 15 Tests: Evidence Assembler

Tests:
  - _build_graph_dict: edge and node construction, error_rate calculation
  - _build_anomaly_list: field mapping
  - assemble_evidence: unknown incident returns None
  - GET /api/v1/evidence/{id}: shape and 404
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.services.evidence import _build_graph_dict, _build_anomaly_list


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _mock_dep(src="frontend", tgt="cart", req=1000, err=50):
    d = MagicMock()
    d.source_service = src
    d.target_service = tgt
    d.request_count  = req
    d.error_count    = err
    return d


def _mock_anomaly(svc="payment", metric="http.duration", z=5.2,
                  direction="spike", current=150.0, mean=100.0,
                  desc="payment: spike"):
    a = MagicMock()
    a.service_name   = svc
    a.metric_name    = metric
    a.z_score        = z
    a.direction      = direction
    a.current_value  = current
    a.baseline_mean  = mean
    a.description    = desc
    return a


# ─────────────────────────────────────────────────────────────────────────────
# Unit tests — _build_graph_dict
# ─────────────────────────────────────────────────────────────────────────────

def test_build_graph_dict_basic():
    deps = [_mock_dep("frontend", "cart", req=1000, err=50)]
    g = _build_graph_dict(deps, ["frontend", "cart"])
    assert "frontend" in g["nodes"]
    assert "cart"     in g["nodes"]
    assert len(g["edges"]) == 1
    edge = g["edges"][0]
    assert edge["source"]        == "frontend"
    assert edge["target"]        == "cart"
    assert edge["request_count"] == 1000
    assert edge["error_rate"]    == pytest.approx(0.05)


def test_build_graph_dict_zero_requests():
    """Zero request_count → error_rate = 0.0 (no division by zero)."""
    deps = [_mock_dep("A", "B", req=0, err=0)]
    g = _build_graph_dict(deps, ["A", "B"])
    assert g["edges"][0]["error_rate"] == 0.0


def test_build_graph_dict_nodes_include_affected():
    """Nodes always include the explicitly passed affected services."""
    deps = []
    g = _build_graph_dict(deps, ["payment", "checkout"])
    assert "payment"  in g["nodes"]
    assert "checkout" in g["nodes"]


def test_build_graph_dict_no_deps():
    """Empty deps list → only affected services as nodes, no edges."""
    g = _build_graph_dict([], ["frontend"])
    assert g["nodes"] == ["frontend"]
    assert g["edges"] == []


def test_build_graph_dict_adds_dep_nodes():
    """Nodes from deps that aren't in affected are still added."""
    deps = [_mock_dep("A", "B", req=100, err=0)]
    g = _build_graph_dict(deps, ["A"])   # "B" not in affected
    assert "B" in g["nodes"]


# ─────────────────────────────────────────────────────────────────────────────
# Unit tests — _build_anomaly_list
# ─────────────────────────────────────────────────────────────────────────────

def test_build_anomaly_list_fields():
    anomalies = [_mock_anomaly("payment", "http.errors", z=8.1, direction="spike")]
    result = _build_anomaly_list(anomalies)
    assert len(result) == 1
    a = result[0]
    assert a["service_name"]  == "payment"
    assert a["metric_name"]   == "http.errors"
    assert a["z_score"]       == pytest.approx(8.1)
    assert a["direction"]     == "spike"
    assert "current_value"    in a
    assert "baseline_mean"    in a
    assert "description"      in a


def test_build_anomaly_list_empty():
    assert _build_anomaly_list([]) == []


def test_build_anomaly_list_multiple():
    anomalies = [
        _mock_anomaly("payment", "errors", z=8.0),
        _mock_anomaly("cart",    "latency", z=5.0),
    ]
    result = _build_anomaly_list(anomalies)
    assert len(result) == 2
    assert result[0]["service_name"] == "payment"
    assert result[1]["service_name"] == "cart"


# ─────────────────────────────────────────────────────────────────────────────
# API tests
# ─────────────────────────────────────────────────────────────────────────────

def _mock_incident(id=1, title="payment: down", severity="critical",
                   status="open", services=None, rule="SERVICE_DOWN", desc="desc"):
    inc = MagicMock()
    inc.id                    = id
    inc.title                 = title
    inc.severity              = severity
    inc.status                = status
    inc.affected_services     = services or ["payment"]
    inc.triggered_by_rule     = rule
    inc.description           = desc
    inc.anomaly_ids           = [1]
    inc.created_at_unix_nano  = 1_000_000_000_000
    inc.resolved_at_unix_nano = None
    return inc


def _mock_rca_row(root="payment", conf=1.0, path=None, scores=None):
    r = MagicMock()
    r.root_cause_service = root
    r.confidence         = conf
    r.propagation_path   = path or ["payment"]
    r.candidate_scores   = scores or {"payment": 1.0}
    return r


@pytest.mark.asyncio
async def test_get_evidence_not_found():
    """GET /api/v1/evidence/{id} returns 404 for unknown incident."""
    from app.db.session import get_db

    # First query in assemble_evidence is _load_incident
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
            resp = await client.get("/api/v1/evidence/999")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_evidence_shape():
    """GET /api/v1/evidence/{id} returns all top-level keys."""
    from app.db.session import get_db

    inc     = _mock_incident(id=1, services=["payment"])
    rca_row = _mock_rca_row(root="payment", conf=1.0, path=["payment"])

    # assemble_evidence makes 5 DB calls in order:
    # 1. _load_incident
    # 2. _load_rca
    # 3. _load_anomalies
    # 4. _load_graph_subgraph
    # 5. _load_error_spans
    # 6. _load_error_logs

    def _make_result(scalar=None, scalars_list=None, all_list=None):
        r = MagicMock()
        r.scalar_one_or_none.return_value = scalar
        if scalars_list is not None:
            r.scalars.return_value.all.return_value = scalars_list
        if all_list is not None:
            r.all.return_value = all_list
        return r

    side_effects = [
        _make_result(scalar=inc),           # _load_incident
        _make_result(scalar=rca_row),       # _load_rca
        _make_result(scalars_list=[]),      # _load_anomalies
        _make_result(scalars_list=[]),      # _load_graph_subgraph
        _make_result(all_list=[]),          # _load_error_spans
        _make_result(all_list=[]),          # _load_error_logs
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
            resp = await client.get("/api/v1/evidence/1")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 200
    data = resp.json()

    # All top-level keys must be present
    for key in ("incident", "rca", "anomalies", "service_graph",
                "error_spans", "error_logs", "_meta"):
        assert key in data, f"Missing key: {key}"

    assert data["incident"]["id"]               == 1
    assert data["incident"]["severity"]         == "critical"
    assert data["rca"]["root_cause_service"]    == "payment"
    assert data["rca"]["confidence"]            == pytest.approx(1.0)
    assert data["_meta"]["rca_available"]       is True
    assert isinstance(data["service_graph"]["nodes"], list)
    assert isinstance(data["service_graph"]["edges"], list)
