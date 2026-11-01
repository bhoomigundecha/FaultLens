"""
FaultLens Backend — AI Explanation API (Phase 17)

POST /api/v1/ai/explain/{incident_id}
    Assembles evidence for an incident, calls Groq, returns the explanation.
    Also patches the incident's dashboard detail response with the result.

GET /api/v1/ai/explain/{incident_id}
    Returns the stored AI explanation for an incident (if already generated).
    404 if not yet generated.
"""
from __future__ import annotations

import logging
import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.config import get_settings
from app.models.incident import Incident
from app.models.ai_explanation import AIExplanation
from app.services.evidence import assemble_evidence
from app.services.ai import generate_explanation

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["ai"])

_NS_PER_MS = 1_000_000


def _explanation_to_dict(exp: AIExplanation) -> dict[str, Any]:
    return {
        "incident_id":        exp.incident_id,
        "root_cause_service": exp.root_cause_service,
        "fault_type":         exp.fault_type,
        "confidence_label":   exp.confidence_label,
        "propagation_path":   exp.propagation_path,
        "human_summary":      exp.human_summary,
        "remediation_steps":  exp.remediation_steps,
        "model":              exp.model,
        "ai_available":       exp.ai_available,
        "generated_at_ms":    (exp.generated_at_unix_nano or 0) // _NS_PER_MS,
    }


@router.post("/ai/explain/{incident_id}", summary="Generate AI explanation for an incident")
async def generate_incident_explanation(
    incident_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Runs the full AI explanation pipeline for one incident:

      1. Assemble evidence (Phase 15)
      2. Call Groq with structured prompt (Phase 17)
      3. Persist result to ai_explanations table
      4. Return explanation

    Safe to call multiple times — re-generates and overwrites the stored result.
    Works even without GROQ_API_KEY (returns a graceful placeholder).
    """
    settings = get_settings()

    # Assemble evidence
    evidence = await assemble_evidence(db, incident_id)
    if evidence is None:
        raise HTTPException(
            status_code=404,
            detail=f"Incident {incident_id} not found.",
        )

    # Call Groq
    ai_result = await generate_explanation(evidence)

    # Persist
    now_ns = time.time_ns()
    existing = await db.execute(
        select(AIExplanation).where(AIExplanation.incident_id == incident_id)
    )
    exp = existing.scalar_one_or_none()

    if exp:
        exp.root_cause_service = ai_result.get("root_cause_service", "unknown")
        exp.fault_type         = ai_result.get("fault_type", "unknown")
        exp.confidence_label   = ai_result.get("confidence_label", "low")
        exp.propagation_path   = ai_result.get("propagation_path", [])
        exp.human_summary      = ai_result.get("human_summary", "")
        exp.remediation_steps  = ai_result.get("remediation_steps", [])
        exp.model              = settings.groq_model
        exp.ai_available       = ai_result.get("_ai_available", False)
        exp.generated_at_unix_nano = now_ns
    else:
        exp = AIExplanation(
            incident_id        = incident_id,
            root_cause_service = ai_result.get("root_cause_service", "unknown"),
            fault_type         = ai_result.get("fault_type", "unknown"),
            confidence_label   = ai_result.get("confidence_label", "low"),
            propagation_path   = ai_result.get("propagation_path", []),
            human_summary      = ai_result.get("human_summary", ""),
            remediation_steps  = ai_result.get("remediation_steps", []),
            model              = settings.groq_model,
            ai_available       = ai_result.get("_ai_available", False),
            generated_at_unix_nano = now_ns,
        )

    db.add(exp)
    await db.commit()

    return _explanation_to_dict(exp)


@router.get("/ai/explain/{incident_id}", summary="Get stored AI explanation for an incident")
async def get_incident_explanation(
    incident_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Returns the stored AI explanation for an incident.
    404 if POST /ai/explain/{id} has not been called yet.
    """
    result = await db.execute(
        select(AIExplanation).where(AIExplanation.incident_id == incident_id)
    )
    exp = result.scalar_one_or_none()
    if exp is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"No AI explanation for incident {incident_id}. "
                "Run POST /api/v1/ai/explain/{incident_id} first."
            ),
        )
    return _explanation_to_dict(exp)
