"""
FaultLens Backend — Phase 12 Tests: Statistical Anomaly Detection

Tests:
  - compute_z_score: pure Python, no DB — all edge cases
  - make_description: formatting
  - run_anomaly_scan: mocked DB session
  - GET /api/v1/anomalies: shape with mocked DB
  - POST /api/v1/anomalies/scan: route exists
"""
from __future__ import annotations

import math
import pytest
from unittest.mock import AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.services.anomaly import (
    compute_z_score,
    make_description,
    AnomalyResult,
    Z_THRESHOLD,
    MIN_SAMPLES,
)


# ─────────────────────────────────────────────────────────────────────────────
# Unit tests — compute_z_score (pure Python, no DB, no mocks)
# ─────────────────────────────────────────────────────────────────────────────

def _baseline(n=20, mean=100.0, stddev=5.0) -> list[float]:
    """Generate a synthetic baseline of n values with given mean and stddev."""
    import random
    random.seed(42)
    return [mean + random.gauss(0, stddev) for _ in range(n)]


def test_z_score_normal_returns_tuple():
    baseline = _baseline(n=20, mean=100.0, stddev=5.0)
    result = compute_z_score(baseline, current_mean=100.0)
    assert result is not None
    z, mean, stddev = result
    assert isinstance(z, float)
    assert abs(mean - 100.0) < 2.0   # should be close to 100
    assert stddev > 0


def test_z_score_spike_detected():
    """A value far above baseline gives a large positive Z."""
    baseline = [100.0] * 20
    result = compute_z_score([100.0 + i * 0.01 for i in range(20)], current_mean=150.0)
    assert result is not None
    z, _, _ = result
    assert z > Z_THRESHOLD


def test_z_score_drop_detected():
    """A value far below baseline gives a large negative Z."""
    baseline = [100.0] * 20
    result = compute_z_score([100.0 - i * 0.01 for i in range(20)], current_mean=50.0)
    assert result is not None
    z, _, _ = result
    assert z < -Z_THRESHOLD


def test_z_score_no_anomaly_for_normal_value():
    """A value within 1 sigma of baseline gives |Z| < threshold."""
    baseline = [100.0] * 30  # perfect constant → stddev will be 0-ish via slight jitter
    # Use a non-constant baseline to avoid stddev=0
    baseline = [100.0 + (i % 3) * 0.1 for i in range(30)]
    result = compute_z_score(baseline, current_mean=100.1)
    assert result is not None
    z, _, _ = result
    assert abs(z) < Z_THRESHOLD


def test_z_score_returns_none_if_too_few_samples():
    """Returns None when baseline has fewer than MIN_SAMPLES points."""
    baseline = [100.0] * (MIN_SAMPLES - 1)
    assert compute_z_score(baseline, current_mean=200.0) is None


def test_z_score_returns_none_for_constant_baseline():
    """Returns None when stddev == 0 (constant metric — no anomaly possible)."""
    baseline = [42.0] * 30
    assert compute_z_score(baseline, current_mean=42.0) is None


def test_z_score_empty_baseline():
    """Returns None for empty baseline."""
    assert compute_z_score([], current_mean=100.0) is None


def test_z_score_formula_correctness():
    """Manually verify Z = (current - mean) / stddev."""
    baseline = [10.0] * 20  # mean=10, but we need non-zero stddev
    # Use a baseline with known stddev
    vals = [8.0, 9.0, 10.0, 11.0, 12.0] * 4   # mean=10, variance=2, stddev=sqrt(2)
    result = compute_z_score(vals, current_mean=14.0)
    assert result is not None
    z, mean, stddev = result
    assert abs(mean - 10.0) < 0.01
    assert abs(stddev - math.sqrt(2)) < 0.1
    expected_z = (14.0 - mean) / stddev
    assert abs(z - expected_z) < 0.01


# ─────────────────────────────────────────────────────────────────────────────
# Unit tests — make_description
# ─────────────────────────────────────────────────────────────────────────────

def test_make_description_spike():
    r = AnomalyResult(
        service_name="payment", metric_name="http.duration",
        z_score=5.2, baseline_mean=100.0, baseline_stddev=10.0,
        current_value=152.0, direction="spike", description=""
    )
    r.description = make_description(r)
    assert "payment" in r.description
    assert "spike" in r.description
    assert "5.2" in r.description


def test_make_description_drop():
    r = AnomalyResult(
        service_name="cart", metric_name="request_count",
        z_score=-4.1, baseline_mean=500.0, baseline_stddev=20.0,
        current_value=350.0, direction="drop", description=""
    )
    r.description = make_description(r)
    assert "drop" in r.description
    assert "cart" in r.description


# ─────────────────────────────────────────────────────────────────────────────
# API tests — mocked DB via dependency_overrides
# ─────────────────────────────────────────────────────────────────────────────

def _mock_anomaly(service="payment", metric="http.duration",
                  z=5.2, direction="spike", active=True):
    a = MagicMock()
    a.id              = 1
    a.service_name    = service
    a.metric_name     = metric
    a.z_score         = z
    a.direction       = direction
    a.current_value   = 150.0
    a.baseline_mean   = 100.0
    a.baseline_stddev = 10.0
    a.description     = f"{service}: {metric} {direction}"
    a.is_active       = active
    a.detected_at_unix_nano  = 1_000_000_000_000
    a.resolved_at_unix_nano  = None
    return a


@pytest.mark.asyncio
async def test_list_active_anomalies_shape():
    """GET /api/v1/anomalies returns list with correct fields."""
    from app.db.session import get_db

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [
        _mock_anomaly("payment", "http.duration", z=5.2),
        _mock_anomaly("cart",    "error_rate",    z=4.1),
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
            resp = await client.get("/api/v1/anomalies")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    a = data["anomalies"][0]
    assert a["service_name"] == "payment"
    assert a["z_score"]      == pytest.approx(5.2)
    assert a["direction"]    == "spike"
    assert "detected_at_ms"  in a


@pytest.mark.asyncio
async def test_list_active_anomalies_empty():
    """Empty anomalies returns total=0."""
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
            resp = await client.get("/api/v1/anomalies")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 200
    assert resp.json()["total"] == 0


@pytest.mark.asyncio
async def test_scan_endpoint_exists():
    """POST /api/v1/anomalies/scan route must be registered."""
    from app.db.session import get_db

    # Mock all three DB calls in run_anomaly_scan:
    # _get_candidate_pairs → empty list → scan returns immediately
    empty = MagicMock(); empty.all.return_value = []
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
            resp = await client.post("/api/v1/anomalies/scan")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 200
    data = resp.json()
    assert data["scanned"]            == 0
    assert data["anomalies_detected"] == 0
    assert data["anomalies"]          == []
