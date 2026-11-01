"""
FaultLens Backend — RCA API (Phase 14)

POST /api/v1/rca/run
    Runs backward graph traversal RCA for all open incidents.

POST /api/v1/rca/{incident_id}/run
    Runs RCA for a single incident.

GET /api/v1/rca/{incident_id}
    Returns the stored RCA result for an incident (404 if not run yet).
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.rca import RootCauseAnalysis
from app.services.rca import run_rca_for_all_open, run_rca_for_incident

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["rca"])

_NS_PER_MS = 1_000_000


def _rca_to_dict(rca: RootCauseAnalysis) -> dict[str, Any]:
    return {
        "id":                 rca.id,
        "incident_id":        rca.incident_id,
        "root_cause_service": rca.root_cause_service,
        "confidence":         rca.confidence,
        "propagation_path":   rca.propagation_path,
        "candidate_scores":   rca.candidate_scores,
        "algorithm":          rca.algorithm,
        "created_at_ms":      (rca.created_at_unix_nano or 0) // _NS_PER_MS,
    }


@router.post("/rca/run", summary="Run RCA for all open incidents")
async def run_rca_all(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Runs backward graph traversal RCA for every open incident.
    Results are persisted to the root_cause_analyses table.

    Typical call cadence: immediately after POST /api/v1/incidents/run.
    """
    results = await run_rca_for_all_open(db)
    await db.commit()
    return {
        "processed": len(results),
        "results":   results,
    }


@router.post("/rca/{incident_id}/run", summary="Run RCA for a specific incident")
async def run_rca_single(
    incident_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Runs RCA for one incident. 404 if the incident doesn't exist."""
    result = await run_rca_for_incident(db, incident_id)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Incident {incident_id} not found.",
        )
    await db.commit()
    return result


@router.get("/rca/{incident_id}", summary="Get stored RCA for an incident")
async def get_rca(
    incident_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Returns the stored RCA result for an incident.
    404 if RCA has not been run for this incident yet.
    """
    result = await db.execute(
        select(RootCauseAnalysis).where(
            RootCauseAnalysis.incident_id == incident_id
        )
    )
    rca = result.scalar_one_or_none()

    if rca is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No RCA found for incident {incident_id}. "
                "Run POST /api/v1/rca/{incident_id}/run first."
            ),
        )
    return _rca_to_dict(rca)
