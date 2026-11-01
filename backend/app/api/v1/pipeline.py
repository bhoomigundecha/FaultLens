"""
FaultLens Backend — Pipeline Runner API

POST /api/v1/pipeline/run
    Runs the full detection + analysis pipeline in one HTTP call:
      1. Anomaly scan (Z-score engine)
      2. Incident engine (rule-based triage)
      3. RCA (backward graph traversal)

    Returns a combined summary of all three stages.
    Intended for:
      - Manual testing: curl -X POST http://localhost:8000/api/v1/pipeline/run
      - Automated scheduling (cron / frontend poll)
      - Debugging: shows exactly what happened at each stage

POST /api/v1/pipeline/run-with-ai
    Same as above, then also generates AI explanations for all newly
    opened/updated incidents.
"""
from __future__ import annotations

import logging
import time

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.incident import Incident
from app.services.anomaly import run_anomaly_scan
from app.services.incident import run_incident_engine
from app.services.rca import run_rca_for_all_open
from app.services.evidence import assemble_evidence
from app.services.ai import generate_explanation
from app.models.ai_explanation import AIExplanation
from app.services import scheduler

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["pipeline"])

_NS_PER_MS = 1_000_000


@router.get("/pipeline/status", summary="Last background pipeline cycle")
async def pipeline_status() -> dict:
    """
    Report of the most recent background cycle (anomalies, incident changes,
    RCA results, AI explanations, per-stage timings). Polled by the frontend /
    handy for curl during a demo.
    """
    return scheduler.last_report


@router.post("/pipeline/run", summary="Run the full detection pipeline")
async def run_pipeline(
    db: AsyncSession = Depends(get_db),
) -> dict:
    async with scheduler.PIPELINE_LOCK:
        return await _run_pipeline(db)


async def _run_pipeline(db: AsyncSession) -> dict:
    """
    Runs anomaly scan → incident engine → RCA in sequence.

    This is the primary endpoint to call to "refresh" the system state.
    Typical use:
      - Every 5 minutes via a scheduler
      - Manually after injecting a fault for demo/testing

    Returns a detailed summary of every stage including what changed.
    """
    t_start = time.perf_counter()
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logger.info("PIPELINE RUN STARTED")
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    # ── Stage 1: Anomaly Scan ──────────────────────────────────────────────
    t0 = time.perf_counter()
    logger.info("[1/3] Running anomaly scan (Z-score engine)...")
    anomaly_summary = await run_anomaly_scan(db)
    await db.commit()
    t1 = time.perf_counter()
    logger.info(
        "[1/3] Anomaly scan complete in %.2fs │ scanned=%d detected=%d",
        t1 - t0,
        anomaly_summary.get("scanned", 0),
        anomaly_summary.get("anomalies_detected", 0),
    )
    if anomaly_summary.get("anomalies_detected", 0) > 0:
        for a in anomaly_summary.get("anomalies", [])[:5]:
            logger.warning(
                "  ANOMALY: %s │ %s │ Z=%.1f (%s)",
                a.get("service_name"),
                a.get("metric_name"),
                a.get("z_score", 0),
                a.get("direction"),
            )

    # ── Stage 2: Incident Engine ───────────────────────────────────────────
    t0 = time.perf_counter()
    logger.info("[2/3] Running incident engine (rule-based triage)...")
    incident_summary = await run_incident_engine(db)
    await db.commit()
    t1 = time.perf_counter()
    logger.info(
        "[2/3] Incident engine complete in %.2fs │ created=%d updated=%d resolved=%d",
        t1 - t0,
        incident_summary.get("incidents_created", 0),
        incident_summary.get("incidents_updated", 0),
        incident_summary.get("incidents_resolved", 0),
    )

    # ── Stage 3: RCA ───────────────────────────────────────────────────────
    t0 = time.perf_counter()
    logger.info("[3/3] Running root cause analysis (graph traversal)...")
    rca_results = await run_rca_for_all_open(db)
    await db.commit()
    t1 = time.perf_counter()
    logger.info(
        "[3/3] RCA complete in %.2fs │ incidents_analysed=%d",
        t1 - t0,
        len(rca_results),
    )
    for r in rca_results:
        logger.info(
            "  RCA: incident=%d root_cause=%s confidence=%.2f path=%s",
            r.get("incident_id"),
            r.get("root_cause_service"),
            r.get("confidence", 0),
            " → ".join(r.get("propagation_path", [])),
        )

    elapsed = time.perf_counter() - t_start
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logger.info("PIPELINE RUN COMPLETE in %.2fs", elapsed)
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    return {
        "pipeline_duration_ms": round(elapsed * 1000, 1),
        "stage_1_anomaly_scan": anomaly_summary,
        "stage_2_incidents":    incident_summary,
        "stage_3_rca": {
            "incidents_analysed": len(rca_results),
            "results":            rca_results,
        },
    }


@router.post("/pipeline/run-with-ai", summary="Run full pipeline including AI explanations")
async def run_pipeline_with_ai(
    db: AsyncSession = Depends(get_db),
) -> dict:
    async with scheduler.PIPELINE_LOCK:
        return await _run_pipeline_with_ai(db)


async def _run_pipeline_with_ai(db: AsyncSession) -> dict:
    """
    Runs the full pipeline AND generates AI explanations for all open incidents.

    Slightly slower than /pipeline/run due to Groq API calls.
    Use this when you want the complete picture immediately.
    """
    t_start = time.perf_counter()
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    logger.info("PIPELINE (WITH AI) RUN STARTED")
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    # Run stages 1-3
    anomaly_summary  = await run_anomaly_scan(db)
    await db.commit()
    incident_summary = await run_incident_engine(db)
    await db.commit()
    rca_results      = await run_rca_for_all_open(db)
    await db.commit()

    # ── Stage 4: AI Explanations ───────────────────────────────────────────
    logger.info("[4/4] Generating AI explanations via Groq...")
    open_inc_result = await db.execute(
        select(Incident).where(Incident.status == "open")
    )
    open_incidents = open_inc_result.scalars().all()

    ai_results = []
    for inc in open_incidents:
        logger.info("  AI: generating explanation for incident %d (%s)...", inc.id, inc.title)
        evidence = await assemble_evidence(db, inc.id)
        if evidence is None:
            continue
        ai_result = await generate_explanation(evidence)

        # Persist
        import time as _time
        now_ns = _time.time_ns()
        from app.core.config import get_settings
        settings = get_settings()

        existing = await db.execute(
            select(AIExplanation).where(AIExplanation.incident_id == inc.id)
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
            from app.models.ai_explanation import AIExplanation as AIExp
            exp = AIExp(
                incident_id        = inc.id,
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

        logger.info(
            "  AI: incident=%d root=%s fault=%s confidence=%s ai_available=%s",
            inc.id,
            ai_result.get("root_cause_service"),
            ai_result.get("fault_type"),
            ai_result.get("confidence_label"),
            ai_result.get("_ai_available"),
        )
        ai_results.append({
            "incident_id":        inc.id,
            "root_cause_service": ai_result.get("root_cause_service"),
            "fault_type":         ai_result.get("fault_type"),
            "confidence_label":   ai_result.get("confidence_label"),
            "ai_available":       ai_result.get("_ai_available", False),
        })

    await db.commit()

    elapsed = time.perf_counter() - t_start
    logger.info("PIPELINE (WITH AI) COMPLETE in %.2fs", elapsed)
    logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    return {
        "pipeline_duration_ms": round(elapsed * 1000, 1),
        "stage_1_anomaly_scan": anomaly_summary,
        "stage_2_incidents":    incident_summary,
        "stage_3_rca": {
            "incidents_analysed": len(rca_results),
            "results":            rca_results,
        },
        "stage_4_ai": {
            "explanations_generated": len(ai_results),
            "results":                ai_results,
        },
    }
