"""
FaultLens Backend — Services API (Phase 9)

GET /api/v1/services
    Returns all discovered services with counters.

GET /api/v1/services/{service_name}
    Returns detail for a single service (404 if unknown).
"""
from __future__ import annotations

import logging
import math
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.service import Service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["services"])

# 1 nanosecond = 1e-9 seconds, convert to milliseconds for human readability
_NS_PER_MS = 1_000_000


def _service_to_dict(svc: Service) -> dict[str, Any]:
    """Serialise a Service ORM row to a JSON-safe dict."""
    error_rate = (
        round(svc.error_count / svc.request_count, 4)
        if svc.request_count
        else 0.0
    )
    return {
        "name":           svc.name,
        "first_seen_ms":  (svc.first_seen_unix_nano or 0) // _NS_PER_MS,
        "last_seen_ms":   (svc.last_seen_unix_nano or 0)  // _NS_PER_MS,
        "request_count":  svc.request_count,
        "error_count":    svc.error_count,
        "error_rate":     error_rate,
    }


@router.get("/services", summary="List all discovered services")
async def list_services(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Returns every service FaultLens has seen telemetry from,
    ordered by last_seen descending (most recently active first).
    """
    result = await db.execute(
        select(Service).order_by(Service.last_seen_unix_nano.desc())
    )
    services = result.scalars().all()

    return {
        "services": [_service_to_dict(s) for s in services],
        "total":    len(services),
    }


@router.get("/services/{service_name}", summary="Get a single service by name")
async def get_service(
    service_name: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Returns detail for a specific service.
    404 if the service has never been seen in telemetry.
    """
    result = await db.execute(
        select(Service).where(Service.name == service_name)
    )
    svc = result.scalar_one_or_none()

    if svc is None:
        raise HTTPException(
            status_code=404,
            detail=f"Service '{service_name}' not found. "
                   "It may not have sent telemetry yet.",
        )

    return _service_to_dict(svc)
