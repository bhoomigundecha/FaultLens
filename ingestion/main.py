"""
FaultLens Ingestion API — FastAPI application.

Endpoints:
  POST /v1/ingest/metrics        OTLP/HTTP JSON metrics
  POST /v1/ingest/logs           OTLP/HTTP JSON logs
  POST /v1/ingest/traces         OTLP/HTTP JSON traces
  POST /v1/webhook/vercel        Vercel Log Drain
  POST /v1/webhook/render        Render Log Stream
  GET  /health                   Liveness
  GET  /v1/services              Registered services + env types
  GET  /v1/incidents             Recent incidents
"""

from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from config.settings import get_settings
import storage.postgres_client as pg_store
from ingestion.otlp_receiver import parse_otlp_metrics, parse_otlp_logs, parse_otlp_traces
from ingestion.webhook_receiver import parse_vercel_payload, parse_render_payload
from ingestion.signal_detector import detect_and_persist
from pipeline.producer import publish, flush, ensure_topics_exist
from pipeline.topics import RAW_METRICS, RAW_LOGS, RAW_TRACES
from pipeline.consumer import MetricsConsumer, LogsConsumer, TracesConsumer

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")
logger = logging.getLogger(__name__)
settings = get_settings()

# ─── Consumers (started at startup, run in background threads) ────────────────
_consumers = [MetricsConsumer(), LogsConsumer(), TracesConsumer()]


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ───────────────────────────────────────────────────────────────
    logger.info("Starting FaultLens ingestion service …")
    try:
        ensure_topics_exist()
        logger.info("Kafka topics ready")
    except Exception as e:
        logger.warning(f"Could not ensure Kafka topics (will retry later): {e}")

    # Start storage consumers in background threads
    for consumer in _consumers:
        consumer.start()

    yield

    # ── Shutdown ──────────────────────────────────────────────────────────────
    logger.info("Shutting down …")
    for consumer in _consumers:
        consumer.stop()
    flush()


app = FastAPI(
    title="FaultLens Ingestion API",
    version="0.1.0",
    description="Receives OTel signals and platform webhooks, normalises, and streams to Kafka.",
    default_response_class=ORJSONResponse,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Helpers ──────────────────────────────────────────────────────────────────

async def _parse_otlp_body(request: Request) -> dict[str, Any]:
    """
    Parse an OTLP/HTTP request body regardless of content-type or encoding.

    Handles:
      - gzip-compressed bodies (collector default)
      - application/json → parse as JSON directly
      - application/x-protobuf → decode using opentelemetry-proto stubs
      - unknown content-type → try JSON first, then protobuf
    """
    import gzip

    body = await request.body()
    content_encoding = request.headers.get("content-encoding", "")
    content_type = request.headers.get("content-type", "")

    # Decompress gzip if needed
    if content_encoding == "gzip" or (len(body) > 1 and body[0] == 0x1f and body[1] == 0x8b):
        body = gzip.decompress(body)

    if "json" in content_type:
        return json.loads(body)

    if "protobuf" in content_type:
        return _decode_protobuf(request.url.path, body)

    # Unknown / missing content-type: try JSON first, then protobuf
    try:
        return json.loads(body)
    except Exception:
        return _decode_protobuf(request.url.path, body)


def _decode_protobuf(path: str, body: bytes) -> dict[str, Any]:
    """
    Attempt to decode an OTLP protobuf body to a plain dict.
    Uses MessageToDict with camelCase keys to match the OTLP JSON spec
    that our otlp_receiver parsers expect.
    """
    try:
        from google.protobuf.json_format import MessageToDict
        if "metrics" in path:
            from opentelemetry.proto.collector.metrics.v1.metrics_service_pb2 import ExportMetricsServiceRequest
            msg = ExportMetricsServiceRequest()
            msg.ParseFromString(body)
        elif "logs" in path:
            from opentelemetry.proto.collector.logs.v1.logs_service_pb2 import ExportLogsServiceRequest
            msg = ExportLogsServiceRequest()
            msg.ParseFromString(body)
        elif "traces" in path:
            from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTraceServiceRequest
            msg = ExportTraceServiceRequest()
            msg.ParseFromString(body)
        else:
            return {}
        # Use camelCase (preserving_proto_field_name=False) to match OTLP JSON spec
        return MessageToDict(msg, preserving_proto_field_name=False, including_default_value_fields=False)
    except ImportError:
        logger.error(
            "Received protobuf-encoded OTLP data but opentelemetry-proto is not installed. "
            "Configure your OTel Collector with 'encoding: json' to fix this."
        )
    except Exception as e:
        logger.warning(f"Protobuf decode failed for {path}: {e}")
    return {}


def _publish_metrics(metrics) -> int:
    for m in metrics:
        publish(RAW_METRICS.name, m.to_kafka_payload(), key=m.service_id)
    return len(metrics)


def _publish_logs(logs) -> int:
    for log in logs:
        publish(RAW_LOGS.name, log.to_kafka_payload(), key=log.service_id)
    return len(logs)


def _publish_traces(traces) -> int:
    for trace in traces:
        publish(RAW_TRACES.name, trace.to_kafka_payload(), key=trace.service_id)
    return len(traces)


# ─── OTLP Endpoints ───────────────────────────────────────────────────────────

@app.post("/v1/ingest/metrics", status_code=202)
@app.post("/v1/metrics", status_code=202)
@app.post("/v1/ingest/metrics/v1/metrics", status_code=202)
async def ingest_metrics(request: Request):
    """Accepts OTLP/HTTP JSON or protobuf MetricsService export."""
    try:
        payload = await _parse_otlp_body(request)
        metrics = parse_otlp_metrics(payload)
        count = _publish_metrics(metrics)
        service_ids = {m.service_id for m in metrics}
        for sid in service_ids:
            await detect_and_persist(sid)
        return {"accepted": count, "status": "queued"}
    except Exception as e:
        logger.exception("Error processing metrics payload")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/v1/ingest/logs", status_code=202)
@app.post("/v1/logs", status_code=202)
@app.post("/v1/ingest/logs/v1/logs", status_code=202)
async def ingest_logs(request: Request):
    """Accepts OTLP/HTTP JSON or protobuf LogsService export."""
    try:
        payload = await _parse_otlp_body(request)
        logs = parse_otlp_logs(payload)
        count = _publish_logs(logs)
        service_ids = {log.service_id for log in logs}
        for sid in service_ids:
            await detect_and_persist(sid)
        return {"accepted": count, "status": "queued"}
    except Exception as e:
        logger.exception("Error processing logs payload")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/v1/ingest/traces", status_code=202)
@app.post("/v1/traces", status_code=202)
@app.post("/v1/ingest/traces/v1/traces", status_code=202)
async def ingest_traces(request: Request):
    """Accepts OTLP/HTTP JSON or protobuf TraceService export."""
    try:
        payload = await _parse_otlp_body(request)
        traces = parse_otlp_traces(payload)
        count = _publish_traces(traces)
        service_ids = {t.service_id for t in traces}
        for sid in service_ids:
            await detect_and_persist(sid)
        return {"accepted": count, "status": "queued"}
    except Exception as e:
        logger.exception("Error processing traces payload")
        raise HTTPException(status_code=400, detail=str(e))


# ─── Webhook Endpoints ────────────────────────────────────────────────────────

@app.post("/v1/webhook/vercel", status_code=202)
async def webhook_vercel(
    payload: list[dict[str, Any]],
    service_id: str = Query(..., description="FaultLens service ID to attribute these logs to"),
):
    """Receives Vercel Log Drain POST body."""
    try:
        logs, metrics = parse_vercel_payload(payload, service_id)
        log_count = _publish_logs(logs)
        metric_count = _publish_metrics(metrics)
        await detect_and_persist(service_id)
        return {"logs_accepted": log_count, "metrics_derived": metric_count, "status": "queued"}
    except Exception as e:
        logger.exception("Error processing Vercel webhook")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/v1/webhook/render", status_code=202)
async def webhook_render(
    payload: list[dict[str, Any]],
    service_id: str = Query(..., description="FaultLens service ID to attribute these logs to"),
):
    """Receives Render Log Stream POST body."""
    try:
        logs, metrics = parse_render_payload(payload, service_id)
        log_count = _publish_logs(logs)
        metric_count = _publish_metrics(metrics)
        await detect_and_persist(service_id)
        return {"logs_accepted": log_count, "metrics_derived": metric_count, "status": "queued"}
    except Exception as e:
        logger.exception("Error processing Render webhook")
        raise HTTPException(status_code=400, detail=str(e))


# ─── Utility Endpoints ────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "service": "faultlens-ingestion"}


@app.get("/v1/services")
async def list_services():
    """List all registered services and their detected environment types."""
    return await pg_store.get_all_services()


@app.get("/v1/incidents")
async def list_incidents(service_id: str | None = None, limit: int = 20):
    """List recent incidents, optionally filtered by service."""
    return await pg_store.list_recent_incidents(service_id=service_id, limit=limit)


@app.get("/v1/incidents/{incident_id}")
async def get_incident(incident_id: str):
    incident = await pg_store.get_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident
