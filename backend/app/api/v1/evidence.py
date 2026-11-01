"""
FaultLens Backend — Evidence API (Phase 15)

GET /api/v1/evidence/{incident_id}
    Returns the complete assembled evidence context for an incident.
    This is exactly what the Phase 17 AI layer sends to Groq.
    Useful for debugging, auditing, and frontend display of "why did AI say this".
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.evidence import assemble_evidence

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["evidence"])


@router.get("/evidence/{incident_id}", summary="Get assembled evidence for an incident")
async def get_evidence(
    incident_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Returns the complete structured evidence context for an incident.

    This is the exact payload that Phase 17 sends to the Groq LLM.
    Returned as-is so the frontend and operators can audit what the AI saw.

    404 if the incident does not exist.
    """
    ctx = await assemble_evidence(db, incident_id)
    if ctx is None:
        raise HTTPException(
            status_code=404,
            detail=f"Incident {incident_id} not found.",
        )
    return ctx
