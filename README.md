# FaultLens V2

AI-powered observability platform for microservice fault detection, root cause analysis, and incident management.

## Architecture

```
OpenTelemetry Demo (Astronomy Shop)
          │
          │  OTLP (traces / metrics / logs)
          ▼
  OpenTelemetry Collector
          │
          │  OTLP HTTP
          ▼
  FaultLens Backend  ←── backend/
          │
          ▼
      PostgreSQL
          │
     ┌────┴────┐
     ▼         ▼
Correlation   Service
 Service       Graph
     │
     ▼
Anomaly Detection
     │
     ▼
 Incident Engine
     │
     ▼
Root Cause Analysis
     │
     ▼
 AI Explanation (optional)
     │
     ▼
FaultLens Frontend  ←── frontend/
```

## Repository Structure

```
FaultLens/
├── backend/          ← FastAPI backend (Python) — being built phase by phase
│   ├── app/
│   │   ├── api/      ← HTTP route handlers
│   │   ├── core/     ← config, logging
│   │   ├── db/       ← SQLAlchemy session factory
│   │   ├── models/   ← ORM models (added in Phase 8)
│   │   ├── schemas/  ← Pydantic schemas
│   │   └── services/ ← business logic
│   ├── alembic/      ← database migrations
│   ├── tests/        ← pytest test suite
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── requirements.txt
├── demo/             ← Official OpenTelemetry Demo (Astronomy Shop)
│   └── ...           ← unmodified upstream — telemetry source only
└── frontend/         ← Next.js frontend — connected in Phase 16
```

## Technology Stack

| Layer | Technology |
|---|---|
| Backend API | Python, FastAPI, uvicorn |
| Database | PostgreSQL 16, SQLAlchemy (async), Alembic |
| Telemetry | OpenTelemetry, OTLP |
| Telemetry Source | OpenTelemetry Demo (Astronomy Shop) |
| Frontend | Next.js |
| Infrastructure | Docker, Docker Compose |

## Build Phases

| Phase | Description | Status |
|---|---|---|
| 0 | FastAPI foundation, `GET /health` | ✅ Done |
| 1 | PostgreSQL connection, `GET /health/db` | ✅ Done |
| 2 | OpenTelemetry Demo running independently | ✅ Done |
| 3 | Connect Collector → FaultLens (OTLP endpoints) | ✅ Done |
| 4 | Trace ingestion + span counting | ✅ Done |
| 5 | Metrics ingestion | ⏳ Pending |
| 6 | Log ingestion | ⏳ Pending |
| 7 | Telemetry normalisation | ⏳ Pending |
| 8 | Persist telemetry to PostgreSQL | ⏳ Pending |
| 9 | Service discovery | ⏳ Pending |
| 10 | Dependency graph | ⏳ Pending |
| 11 | Telemetry correlation | ⏳ Pending |
| 12 | Statistical anomaly detection | ⏳ Pending |
| 13 | Incident engine | ⏳ Pending |
| 14 | Root cause analysis (deterministic) | ⏳ Pending |
| 15 | Fault scenario evaluation | ⏳ Pending |
| 16 | Frontend API contract | ⏳ Pending |
| 17 | AI explanation layer | ⏳ Pending |

## Quick Start

### Start the backend

```bash
cd backend
./venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Health checks
curl http://localhost:8000/health
curl http://localhost:8000/health/db
```

### Start the OpenTelemetry Demo (Phase 2+)

> Requires Docker Desktop to be running.

```bash
cd demo

# Start core demo services only (no observability stack)
docker compose up -d

# Verify everything is healthy
bash check-demo.sh

# Watch telemetry flowing through the collector
docker logs otel-collector -f --tail=20
```

### Run tests

```bash
cd backend
./venv/bin/pytest tests/ -v
```
