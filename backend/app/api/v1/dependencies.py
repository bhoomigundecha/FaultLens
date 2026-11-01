"""
FaultLens Backend — Dependency Graph API (Phase 10)

GET /api/v1/dependencies
    Returns all directed service→service edges with counters.
    Response is shaped for easy rendering as a graph (nodes + edges).

GET /api/v1/dependencies/{source}/{target}
    Returns a single edge detail (404 if the pair has never been seen).
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.dependency import ServiceDependency

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["dependencies"])

_NS_PER_MS = 1_000_000


def _edge_to_dict(dep: ServiceDependency) -> dict[str, Any]:
    error_rate = (
        round(dep.error_count / dep.request_count, 4)
        if dep.request_count
        else 0.0
    )
    return {
        "source":         dep.source_service,
        "target":         dep.target_service,
        "first_seen_ms":  (dep.first_seen_unix_nano or 0) // _NS_PER_MS,
        "last_seen_ms":   (dep.last_seen_unix_nano  or 0) // _NS_PER_MS,
        "request_count":  dep.request_count,
        "error_count":    dep.error_count,
        "error_rate":     error_rate,
    }


@router.get("/dependencies", summary="Get the full service dependency graph")
async def get_dependencies(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Returns all known directed service-to-service call edges,
    plus a deduplicated node list for easy graph rendering.

    Edge ordering: highest request_count first (busiest paths at top).
    """
    result = await db.execute(
        select(ServiceDependency).order_by(
            ServiceDependency.request_count.desc()
        )
    )
    deps = result.scalars().all()

    edges = [_edge_to_dict(d) for d in deps]

    # Collect unique service names across all edges for the node list
    node_names: set[str] = set()
    for d in deps:
        node_names.add(d.source_service)
        node_names.add(d.target_service)

    return {
        "nodes": sorted(node_names),   # alphabetical for stable frontend rendering
        "edges": edges,
        "edge_count": len(edges),
        "node_count": len(node_names),
    }


@router.get(
    "/dependencies/{source}/{target}",
    summary="Get a single dependency edge",
)
async def get_dependency(
    source: str,
    target: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Returns the dependency edge between two specific services.
    404 if the pair has never been observed in telemetry.
    """
    result = await db.execute(
        select(ServiceDependency).where(
            ServiceDependency.source_service == source,
            ServiceDependency.target_service == target,
        )
    )
    dep = result.scalar_one_or_none()

    if dep is None:
        raise HTTPException(
            status_code=404,
            detail=f"No dependency found from '{source}' to '{target}'.",
        )

    return _edge_to_dict(dep)
