"""
FaultLens Backend — Phase 16+17 Tests: AI Explanation Layer

Tests:
  - _build_user_message: strips _meta, produces valid JSON
  - _parse_groq_response: clean JSON, markdown-fenced JSON
  - _validate_schema: fills missing fields with defaults
  - generate_explanation: no key → graceful placeholder
  - POST /api/v1/ai/explain/{id}: 404 for unknown incident
  - GET /api/v1/ai/explain/{id}: 404 when not generated
  - GET /api/v1/ai/explain/{id}: returns stored explanation
"""
from __future__ import annotations

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.services.ai import (
    _build_user_message,
    _parse_groq_response,
    _validate_schema,
    generate_explanation,
)


# ─────────────────────────────────────────────────────────────────────────────
# Unit tests — pure functions (no DB, no Groq)
# ─────────────────────────────────────────────────────────────────────────────

_SAMPLE_EVIDENCE = {
    "incident": {"id": 1, "title": "payment: down", "severity": "critical"},
    "rca":      {"root_cause_service": "payment", "confidence": 1.0, "propagation_path": ["payment"]},
    "anomalies": [],
    "service_graph": {"nodes": ["payment"], "edges": []},
    "error_spans":   [],
    "error_logs":    [],
    "_meta":    {"rca_available": True, "anomaly_count": 0},
}

_VALID_RESPONSE = {
    "root_cause_service": "payment",
    "fault_type":         "database_connection_refused",
    "confidence_label":   "high",
    "propagation_path":   ["payment", "checkout"],
    "human_summary":      "The payment service cannot connect to its database.",
    "remediation_steps":  ["Check DB pod", "Restart payment service"],
}


def test_build_user_message_strips_meta():
    msg = _build_user_message(_SAMPLE_EVIDENCE)
    parsed = json.loads(msg)
    assert "_meta" not in parsed
    assert "incident" in parsed
    assert "rca"      in parsed


def test_build_user_message_is_valid_json():
    msg = _build_user_message(_SAMPLE_EVIDENCE)
    assert isinstance(json.loads(msg), dict)


def test_parse_groq_clean_json():
    raw = json.dumps(_VALID_RESPONSE)
    result = _parse_groq_response(raw)
    assert result["root_cause_service"] == "payment"


def test_parse_groq_strips_markdown_fences():
    fenced = "```json\n" + json.dumps(_VALID_RESPONSE) + "\n```"
    result = _parse_groq_response(fenced)
    assert result["fault_type"] == "database_connection_refused"


def test_validate_schema_complete():
    result = _validate_schema(_VALID_RESPONSE.copy())
    for key in ("root_cause_service", "fault_type", "confidence_label",
                "propagation_path", "human_summary", "remediation_steps"):
        assert key in result


def test_validate_schema_fills_missing_fields():
    partial = {"root_cause_service": "payment"}
    result = _validate_schema(partial)
    assert result["fault_type"]        == "unknown"
    assert result["confidence_label"]  == "low"
    assert result["propagation_path"]  == []
    assert result["remediation_steps"] == []
    assert "human_summary" in result


def test_validate_schema_preserves_existing():
    d = {"root_cause_service": "cart", "fault_type": "oom", "confidence_label": "high",
         "propagation_path": ["cart"], "human_summary": "OOM", "remediation_steps": ["restart"]}
    result = _validate_schema(d)
    assert result["fault_type"] == "oom"
    assert result["confidence_label"] == "high"


# ─────────────────────────────────────────────────────────────────────────────
# Unit test — generate_explanation without GROQ_API_KEY
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_generate_explanation_no_key():
    """When GROQ_API_KEY is not set, returns a graceful placeholder."""
    from app.core.config import get_settings, Settings

    mock_settings = MagicMock(spec=Settings)
    mock_settings.has_groq = False
    mock_settings.groq_model = "llama-3.3-70b-versatile"

    with patch("app.services.ai.get_settings", return_value=mock_settings):
        result = await generate_explanation(_SAMPLE_EVIDENCE)

    assert result["_ai_available"]   is False
    assert "GROQ_API_KEY"            in result["human_summary"]
    assert result["root_cause_service"] == "payment"


# ─────────────────────────────────────────────────────────────────────────────
# API tests — mocked DB
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ai_explain_post_incident_not_found():
    """POST /api/v1/ai/explain/{id} returns 404 for unknown incident."""
    from app.db.session import get_db

    # assemble_evidence → _load_incident → None
    empty = MagicMock(); empty.scalar_one_or_none.return_value = None
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=empty)

    async def override():
        yield mock_db

    app.dependency_overrides[get_db] = override
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post("/api/v1/ai/explain/999")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_ai_explain_get_not_found():
    """GET /api/v1/ai/explain/{id} returns 404 when not yet generated."""
    from app.db.session import get_db

    empty = MagicMock(); empty.scalar_one_or_none.return_value = None
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=empty)

    async def override():
        yield mock_db

    app.dependency_overrides[get_db] = override
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/v1/ai/explain/1")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_ai_explain_get_returns_stored():
    """GET /api/v1/ai/explain/{id} returns the stored explanation."""
    from app.db.session import get_db

    exp = MagicMock()
    exp.incident_id        = 1
    exp.root_cause_service = "payment"
    exp.fault_type         = "database_connection_refused"
    exp.confidence_label   = "high"
    exp.propagation_path   = ["payment", "checkout"]
    exp.human_summary      = "Payment DB is unreachable."
    exp.remediation_steps  = ["Check DB pod"]
    exp.model              = "llama-3.3-70b-versatile"
    exp.ai_available       = True
    exp.generated_at_unix_nano = 1_000_000_000_000

    mock_result = MagicMock(); mock_result.scalar_one_or_none.return_value = exp
    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)

    async def override():
        yield mock_db

    app.dependency_overrides[get_db] = override
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.get("/api/v1/ai/explain/1")
    finally:
        app.dependency_overrides.pop(get_db, None)

    assert resp.status_code == 200
    data = resp.json()
    assert data["root_cause_service"] == "payment"
    assert data["fault_type"]         == "database_connection_refused"
    assert data["confidence_label"]   == "high"
    assert data["ai_available"]       is True
    assert "human_summary"            in data
    assert "remediation_steps"        in data
    assert "generated_at_ms"          in data
