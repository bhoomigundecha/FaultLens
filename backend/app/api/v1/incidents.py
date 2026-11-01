"""
FaultLens Backend — Incidents API (Phase 13)

POST /api/v1/incidents/run
    Triggers the rule-based incident engine (reads active anomalies,
    creates/updates/resolves incident records).

GET /api/v1/incidents
    Returns all open incidents, most severe first.

GET /api/v1/incidents/{incident_id}
    Returns a single incident with full detail.

GET /api/v1/incidents/history
    Returns all incidents (open + resolved), most recent first.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.incident import Incident
from app.services.incident import run_incident_engine

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["incidents"])

_NS_PER_MS = 1_000_000

# Severity display order for sorting
_SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def _incident_to_dict(inc: Incident) -> dict[str, Any]:
    return {
        "id":                inc.id,
        "title":             inc.title,
        "severity":          inc.severity,
        "status":            inc.status,
        "affected_services": inc.affected_services,
        "anomaly_ids":       inc.anomaly_ids,
        "triggered_by_rule": inc.triggered_by_rule,
        "description":       inc.description,
        "created_at_ms":     (inc.created_at_unix_nano or 0) // _NS_PER_MS,
        "resolved_at_ms":    (
            inc.resolved_at_unix_nano // _NS_PER_MS
            if inc.resolved_at_unix_nano else None
        ),
    }


@router.post("/incidents/run", summary="Run the incident engine")
async def run_incidents(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Triggers the rule-based incident engine.

    Reads currently active anomalies, applies the rule table, and
    creates/updates/resolves incident records accordingly.

    Typical call cadence: immediately after POST /api/v1/anomalies/scan.
    """
    summary = await run_incident_engine(db)
    await db.commit()
    return summary


@router.get("/incidents", summary="List open incidents")
async def list_open_incidents(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Returns open incidents ordered by severity (critical first).
    This is what the AI layer (Phase 17) reads to build its context.
    """
    result = await db.execute(
        select(Incident).where(Incident.status == "open")
    )
    incidents = result.scalars().all()

    # Sort: critical > high > medium > low
    incidents = sorted(
        incidents,
        key=lambda i: _SEVERITY_ORDER.get(i.severity, 99),
    )

    return {
        "incidents": [_incident_to_dict(i) for i in incidents],
        "total":     len(incidents),
    }


@router.get("/incidents/history", summary="List all incidents (open + resolved)")
async def list_incident_history(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Returns all incidents most-recently-created first (up to 100)."""
    result = await db.execute(
        select(Incident)
        .order_by(Incident.created_at_unix_nano.desc())
        .limit(100)
    )
    incidents = result.scalars().all()
    return {
        "incidents": [_incident_to_dict(i) for i in incidents],
        "total":     len(incidents),
    }


@router.get("/incidents/{incident_id}", summary="Get a single incident")
async def get_incident(
    incident_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Returns full detail for a single incident. 404 if not found."""
    result = await db.execute(
        select(Incident).where(Incident.id == incident_id)
    )
    inc = result.scalar_one_or_none()
    if inc is None:
        raise HTTPException(
            status_code=404,
            detail=f"Incident {incident_id} not found.",
        )
    return _incident_to_dict(inc)
