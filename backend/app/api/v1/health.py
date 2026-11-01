"""
FaultLens Backend — Health API

Phase 0: GET /health      →  {"status": "ok"}
Phase 1: GET /health/db   →  {"status": "ok", "database": "connected"}
"""
import logging
from fastapi import APIRouter, HTTPException
from app.db.session import check_db

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])


@router.get("/health", summary="Basic liveness check")
async def health() -> dict:
    """
    Liveness endpoint.
    Returns 200 {"status": "ok"} if the application process is alive.
    Does NOT check database or external dependencies.
    """
    logger.debug("Health check requested")
    return {"status": "ok"}


@router.get("/health/db", summary="Database connectivity check")
async def health_db() -> dict:
    """
    Readiness endpoint for the database.
    Executes a lightweight SELECT 1 against PostgreSQL.
    Returns 200 on success, 503 on failure.
    """
    is_connected = await check_db()

    if is_connected:
        logger.debug("Database health check OK")
        return {"status": "ok", "database": "connected"}

    logger.warning("Database health check: not connected")
    raise HTTPException(
        status_code=503,
        detail={"status": "error", "database": "unreachable"},
    )
