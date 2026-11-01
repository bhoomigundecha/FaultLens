"""
FaultLens Backend — Real-time pipeline scheduler

Runs the full analysis pipeline in the background, every
PIPELINE_INTERVAL_SECONDS, from app startup until shutdown:

    [1/4] Detect     RED detectors on spans + resource z-scores   (services.anomaly)
    [2/4] Incidents  rule-based triage of active anomalies        (services.incident)
    [3/4] RCA        dependency-graph traversal per open incident (services.rca)
    [4/4] AI         Groq explanation for incidents that lack one (services.ai)

Every ~5 minutes it also deletes raw telemetry older than
TELEMETRY_RETENTION_MINUTES so the database (and every query) stays small.

Log output is designed to be read live during a demo:
  - quiet system  → one heartbeat line per cycle
  - something up  → a framed block showing what each stage found
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from sqlalchemy import select, text

from app.core.config import get_settings
from app.db import session as db_session
from app.services.anomaly import RED_MIN_BASELINE_BUCKETS

logger = logging.getLogger("faultlens.pipeline")

# Shared with the manual /api/v1/pipeline/* endpoints so a manual run and the
# background loop never analyse the same data at the same time.
PIPELINE_LOCK = asyncio.Lock()

AI_MAX_PER_CYCLE  = 2      # protect the Groq free-tier rate limit
AI_RETRY_AFTER_S  = 120    # after a failed Groq call, pause AI this long
_ai_paused_until  = 0.0
RETENTION_EVERY_N = 10     # cycles between retention sweeps (10 × 30 s = 5 min)
_DELETE_BATCH     = 20_000

_task: asyncio.Task | None = None
last_report: dict[str, Any] = {"cycle": 0, "status": "not started"}

_BAR = "━" * 72


# ── AI persistence (shared with the API) ──────────────────────────────────────

async def persist_explanation(db, incident_id: int, ai_result: dict) -> None:
    """Insert or overwrite the stored AI explanation for one incident."""
    from app.models.ai_explanation import AIExplanation

    settings = get_settings()
    row = (await db.execute(
        select(AIExplanation).where(AIExplanation.incident_id == incident_id)
    )).scalar_one_or_none()
    if row is None:
        row = AIExplanation(incident_id=incident_id)
    row.root_cause_service     = ai_result.get("root_cause_service", "unknown")
    row.fault_type             = ai_result.get("fault_type", "unknown")
    row.confidence_label       = ai_result.get("confidence_label", "low")
    row.propagation_path       = ai_result.get("propagation_path", [])
    row.human_summary          = ai_result.get("human_summary", "")
    row.remediation_steps      = ai_result.get("remediation_steps", [])
    row.model                  = settings.groq_model
    row.ai_available           = ai_result.get("_ai_available", False)
    row.generated_at_unix_nano = time.time_ns()
    db.add(row)


async def _explain_new_incidents(db) -> list[dict]:
    """Generate AI explanations for open incidents that don't have one yet."""
    from app.models.incident import Incident
    from app.models.ai_explanation import AIExplanation
    from app.services.evidence import assemble_evidence
    from app.services.ai import generate_explanation

    explained = select(AIExplanation.incident_id)
    pending = (await db.execute(
        select(Incident)
        .where(Incident.status == "open", Incident.id.not_in(explained))
        .order_by(Incident.id)
        .limit(AI_MAX_PER_CYCLE)
    )).scalars().all()

    global _ai_paused_until
    if time.monotonic() < _ai_paused_until:
        return []

    out = []
    for inc in pending:
        evidence = await assemble_evidence(db, inc.id)
        if evidence is None:
            continue
        result = await generate_explanation(evidence)
        if not result.get("_ai_available"):
            # Don't store the failure as if it were an explanation — the
            # incident stays "unexplained" and is retried after the pause.
            _ai_paused_until = time.monotonic() + AI_RETRY_AFTER_S
            out.append({"incident_id": inc.id, "failed": True, **result})
            break
        await persist_explanation(db, inc.id, result)
        out.append({"incident_id": inc.id, **result})
    return out


# ── Retention ─────────────────────────────────────────────────────────────────

_RETENTION_TABLES = (
    ("spans",         "start_time_unix_nano"),
    ("metric_points", "time_unix_nano"),
    ("log_records",   "time_unix_nano"),
)


async def run_retention() -> dict[str, int]:
    """Delete raw telemetry older than the retention window, in small batches."""
    minutes = get_settings().telemetry_retention_minutes
    cutoff = time.time_ns() - minutes * 60 * 1_000_000_000
    deleted: dict[str, int] = {}
    for table, col in _RETENTION_TABLES:
        total = 0
        while True:
            async with db_session.AsyncSessionLocal() as db:
                async with db.begin():
                    res = await db.execute(text(
                        f"DELETE FROM {table} WHERE id IN ("
                        f"  SELECT id FROM {table} WHERE {col} < :cutoff LIMIT {_DELETE_BATCH})"
                    ), {"cutoff": cutoff})
            total += res.rowcount or 0
            if (res.rowcount or 0) < _DELETE_BATCH:
                break
            await asyncio.sleep(0)   # let ingest requests in between batches
        deleted[table] = total
    return deleted


# ── One pipeline cycle ────────────────────────────────────────────────────────

async def run_cycle(cycle: int, explain: bool | None = None) -> dict[str, Any]:
    """Run detect → incidents → RCA → AI once and log the outcome."""
    from app.services.anomaly import run_anomaly_scan
    from app.services.incident import run_incident_engine
    from app.services.rca import run_rca_for_all_open
    from app.models.service import Service

    settings = get_settings()
    if explain is None:
        explain = settings.ai_auto_explain and settings.has_groq

    t0 = time.perf_counter()
    async with PIPELINE_LOCK:
        async with db_session.AsyncSessionLocal() as db:
            anomalies = await run_anomaly_scan(db);      await db.commit()
            t1 = time.perf_counter()
            incidents = await run_incident_engine(db);   await db.commit()
            t2 = time.perf_counter()
            rca       = await run_rca_for_all_open(db);  await db.commit()
            t3 = time.perf_counter()
            ai        = await _explain_new_incidents(db) if explain else []
            await db.commit()
            t4 = time.perf_counter()
            n_services = len((await db.execute(select(Service.name))).all())

    report = {
        "cycle": cycle,
        "status": "ok",
        "finished_at_ms": int(time.time() * 1000),
        "duration_ms": round((t4 - t0) * 1000, 1),
        "services": n_services,
        "anomalies": anomalies,
        "incidents": incidents,
        "rca": rca,
        "ai": [{k: v for k, v in r.items() if not k.startswith("_")} for r in ai],
        "stage_ms": {
            "detect": round((t1 - t0) * 1000, 1), "incidents": round((t2 - t1) * 1000, 1),
            "rca": round((t3 - t2) * 1000, 1), "ai": round((t4 - t3) * 1000, 1),
        },
    }
    _log_report(report)
    return report


def _log_report(r: dict[str, Any]) -> None:
    a, i = r["anomalies"], r["incidents"]
    active = a.get("anomalies", [])
    quiet = (not active and not i.get("changes") and not a.get("resolved")
             and i.get("open_count", 0) == 0)

    if quiet:
        learning = a.get("learning") or {}
        if learning:
            mins = min(learning.values())
            logger.info("[pipeline #%d] … learning baseline │ %d/%d services still learning "
                        "(%d/%d min of history) │ no alerts yet │ %.0f ms",
                        r["cycle"], len(learning), r["services"], mins, RED_MIN_BASELINE_BUCKETS,
                        r["duration_ms"])
        else:
            logger.info("[pipeline #%d] ✓ all healthy │ %d services │ 0 anomalies │ 0 incidents │ %.0f ms",
                        r["cycle"], r["services"], r["duration_ms"])
        return

    ms = r["stage_ms"]
    log, warn = logger.info, logger.warning   # only problems are WARNING
    log(_BAR)
    log("PIPELINE #%d │ %d services │ %d active anomalies │ %d open incidents",
        r["cycle"], r["services"], len(active), i.get("open_count", 0))
    log(_BAR)

    log("[1/4] DETECT     %d anomalies  (%.0f ms)", len(active), ms["detect"])
    new = set(a.get("newly_opened", []))
    for an in sorted(active, key=lambda x: -abs(x.get("z_score", 0))):
        tag = "NEW " if f"{an['service_name']} / {an['metric_name']}" in new else "    "
        warn("        %s⚠ %-15s %-19s z=%5.1f  %s", tag, an["service_name"], an["metric_name"],
            an.get("z_score", 0), an.get("description", "").split(": ", 1)[-1])
    for key in a.get("resolved", []):
        log("            ✓ cleared  %s", key)

    log("[2/4] INCIDENTS  %d open  (+%d new, %d updated, %d resolved)",
        i.get("open_count", 0), i.get("incidents_created", 0),
        i.get("incidents_updated", 0), i.get("incidents_resolved", 0))
    for c in i.get("changes", []):
        (warn if c.startswith(("+", "↑")) else log)("            %s", c)

    log("[3/4] RCA        %d incident(s) analysed  (%.0f ms)", len(r["rca"]), ms["rca"])
    for x in r["rca"]:
        log("            #%-3d root cause → %-15s confidence %.2f   path: %s",
            x["incident_id"], x["root_cause_service"], x.get("confidence", 0),
            " → ".join(x.get("propagation_path", [])))

    ok_ai = [x for x in r["ai"] if not x.get("failed")]
    if any(x.get("failed") for x in r["ai"]):
        warn("[4/4] AI         Groq call failed — will retry in %ds (see error above)", AI_RETRY_AFTER_S)
    elif ok_ai:
        log("[4/4] AI         %d explanation(s) generated  (%.0f ms)", len(ok_ai), ms["ai"])
        for x in ok_ai:
            summary = (x.get("human_summary") or "").replace("\n", " ")
            log("            #%-3d %s / %s: %s", x["incident_id"], x.get("root_cause_service"),
                x.get("fault_type"), summary[:160] + ("…" if len(summary) > 160 else ""))
    else:
        log("[4/4] AI         nothing new to explain")
    log("%s %.0f ms", "━" * 62, r["duration_ms"])


# ── Background loop ───────────────────────────────────────────────────────────

async def _loop() -> None:
    global last_report
    settings = get_settings()
    interval = max(5, settings.pipeline_interval_seconds)
    logger.info("Real-time pipeline started │ every %ds │ retention %d min │ AI %s │ ignoring: %s",
                interval, settings.telemetry_retention_minutes,
                "on" if (settings.ai_auto_explain and settings.has_groq) else "off",
                settings.detection_ignore_services or "-")
    cycle = 0
    while True:
        cycle += 1
        started = time.monotonic()
        try:
            last_report = await run_cycle(cycle)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 — keep the loop alive no matter what
            root = getattr(exc, "orig", None) or exc
            last_report = {"cycle": cycle, "status": "error", "error": str(root)[:300]}
            logger.error("[pipeline #%d] cycle failed: %s: %s",
                         cycle, type(root).__name__, str(root).splitlines()[0][:200])

        if cycle % RETENTION_EVERY_N == 0:
            try:
                deleted = await run_retention()
                if any(deleted.values()):
                    logger.info("[retention] removed telemetry older than %d min │ %s",
                                settings.telemetry_retention_minutes,
                                ", ".join(f"{t}={n:,}" for t, n in deleted.items()))
            except Exception as exc:  # noqa: BLE001
                logger.error("[retention] failed: %s", exc)

        await asyncio.sleep(max(0.0, interval - (time.monotonic() - started)))


def start() -> None:
    """Start the background loop (called from the FastAPI lifespan)."""
    global _task
    if _task is None or _task.done():
        _task = asyncio.create_task(_loop(), name="faultlens-pipeline")


async def stop() -> None:
    global _task
    if _task is not None:
        _task.cancel()
        try:
            await _task
        except (asyncio.CancelledError, Exception):
            pass
        _task = None
