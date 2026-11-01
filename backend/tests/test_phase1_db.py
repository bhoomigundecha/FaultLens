"""
FaultLens Backend — Phase 1 Tests

Tests /health/db behaviour:
  - When database is reachable → 200 {"status": "ok", "database": "connected"}
  - When database is unreachable → 503

We mock check_db() so these tests don't require a live database.
They verify routing and response shape — integration tests (with a real DB)
are done via docker-compose and manual curl in Phase 1 verification.
"""
import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport
from app.main import app

# check_db is imported at module level in health.py, so we patch it there.
PATCH_TARGET = "app.api.v1.health.check_db"


@pytest.mark.asyncio
async def test_health_db_when_connected():
    """When database is reachable: GET /health/db → 200 connected"""
    with patch(PATCH_TARGET, new_callable=AsyncMock, return_value=True):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/health/db")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["database"] == "connected"


@pytest.mark.asyncio
async def test_health_db_when_unreachable():
    """When database is down: GET /health/db → 503"""
    with patch(PATCH_TARGET, new_callable=AsyncMock, return_value=False):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/health/db")

    assert response.status_code == 503


@pytest.mark.asyncio
async def test_health_still_works_in_phase1():
    """/health must still return 200 — Phase 0 behaviour is preserved."""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
