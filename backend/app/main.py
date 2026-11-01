"""
FaultLens Backend — Application Entry Point

Phase 0: FastAPI foundation
  - Configuration management, structured logging, GET /health

Phase 1: PostgreSQL connection
  - SQLAlchemy async engine, GET /health/db

Phase 3: OTLP ingestion endpoints
  - POST /otlp/v1/traces, /otlp/v1/metrics, /otlp/v1/logs

Phase 4: Trace ingestion + span counting
  - Parses protobuf ExportTraceServiceRequest, logs span count

Phase 5: Metrics ingestion — persists MetricPoint rows to PostgreSQL
Phase 6: Log ingestion    — persists LogRecord rows to PostgreSQL
Phase 7: Telemetry normalisation — protobuf → typed dicts (services.normalise)
Phase 8: Persist all telemetry (Span, MetricPoint, LogRecord) in bulk
Phase 9: Service discovery — GET /api/v1/services, /api/v1/services/{name}
Phase 10: Dependency graph — GET /api/v1/dependencies
Phase 11: Telemetry correlation — GET /api/v1/traces, /api/v1/traces/{trace_id}
Phase 12: Anomaly detection   — POST /api/v1/anomalies/scan, GET /api/v1/anomalies
Phase 13: Incident engine     — POST /api/v1/incidents/run, GET /api/v1/incidents
Phase 14: Root cause analysis — POST /api/v1/rca/run, GET /api/v1/rca/{incident_id}
Phase 15: Evidence assembler  — GET /api/v1/evidence/{incident_id}
Phase 16: Frontend contract   — GET /api/v1/dashboard, /api/v1/dashboard/incident/{id}
Phase 17: AI explanation      — POST /api/v1/ai/explain/{id}, GET /api/v1/ai/explain/{id}
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.logging import setup_logging
from app.api.v1.health import router as health_router
from app.api.v1.ingest import router as ingest_router
from app.api.v1.services import router as services_router        # Phase 9
from app.api.v1.dependencies import router as dependencies_router # Phase 10
from app.api.v1.traces import router as traces_router             # Phase 11
from app.api.v1.anomalies import router as anomalies_router       # Phase 12
from app.api.v1.incidents import router as incidents_router       # Phase 13
from app.api.v1.rca import router as rca_router                   # Phase 14
from app.api.v1.evidence import router as evidence_router         # Phase 15
from app.api.v1.dashboard import router as dashboard_router       # Phase 16
from app.api.v1.ai import router as ai_router                     # Phase 17
from app.api.v1.pipeline import router as pipeline_router         # Pipeline runner
import app.models  # noqa: F401 — registers ORM models in Base.metadata at import time


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Runs startup logic before yield, teardown logic after.
    Using the lifespan pattern avoids deprecated @app.on_event handlers.
    """
    # ── Startup ────────────────────────────────────────────────────────────────
    setup_logging()
    logger = logging.getLogger(__name__)
    settings = get_settings()

    logger.info("=" * 60)
    logger.info("Starting %s | env=%s", settings.app_name, settings.app_env)
    logger.info("=" * 60)

    # Phase 1 — initialise the database connection pool
    if settings.database_url:
        from app.db.session import init_db
        await init_db()
    else:
        logger.warning(
            "DATABASE_URL not set — database features disabled. "
            "Set DATABASE_URL in .env to enable /health/db."
        )

    # Phases 5-8 — DB tables must exist before requests arrive.
    # Run:  alembic upgrade head   (once, or in CI/CD)
    # The app does NOT auto-migrate on startup to keep startup fast and safe.

    # Real-time pipeline — background detect → incidents → RCA → AI loop
    from app.services import scheduler
    if settings.database_url and settings.pipeline_auto_run:
        scheduler.start()
    else:
        logger.info("Real-time pipeline disabled (PIPELINE_AUTO_RUN=false or no DATABASE_URL) — "
                    "trigger it manually with POST /api/v1/pipeline/run")

    yield

    await scheduler.stop()

    # ── Shutdown ───────────────────────────────────────────────────────────────
    logger.info("Shutting down %s", settings.app_name)

    # Phase 1 — close the database connection pool
    if settings.database_url:
        from app.db.session import close_db
        await close_db()


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        description="FaultLens — AI-powered observability platform",
        version="2.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # ── CORS ───────────────────────────────────────────────────────────────────
    # Allow the FaultLens frontend (Next.js dev server runs on port 3000)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Compatibility: rewrite /v1/* to /api/v1/* for frontend ─────────────────
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.requests import Request

    class PrefixCompatMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):
            if request.url.path.startswith("/v1/"):
                request.scope["path"] = "/api" + request.url.path
            return await call_next(request)

    app.add_middleware(PrefixCompatMiddleware)

    # ── Routers ────────────────────────────────────────────────────────────────
    app.include_router(health_router)
    app.include_router(ingest_router)          # Phase 3  — OTLP ingestion
    app.include_router(services_router)        # Phase 9  — service discovery
    app.include_router(dependencies_router)    # Phase 10 — dependency graph
    app.include_router(traces_router)          # Phase 11 — telemetry correlation
    app.include_router(anomalies_router)       # Phase 12 — anomaly detection
    app.include_router(incidents_router)       # Phase 13 — incident engine
    app.include_router(rca_router)             # Phase 14 — root cause analysis
    app.include_router(evidence_router)        # Phase 15 — evidence assembler
    app.include_router(dashboard_router)       # Phase 16 — frontend contract
    app.include_router(ai_router)              # Phase 17 — AI explanation
    app.include_router(pipeline_router)        # Pipeline — combined scan+incidents+RCA+AI

    return app


app = create_app()
