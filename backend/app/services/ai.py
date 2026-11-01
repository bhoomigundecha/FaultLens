"""
FaultLens Backend — AI Explanation Layer (Phase 17)

Implements the research-aligned LLM explanation pattern from GALA/RCAgent:

  1. Evidence Assembler (Phase 15) produces a structured context dict.
  2. This module converts that dict into a strict JSON prompt.
  3. Calls Groq (llama-3.3-70b-versatile) with the prompt.
  4. Validates the response against our expected schema.
  5. Persists the explanation to the ai_explanations table.

Key design decisions (from the research):
  - ONE call per incident. Not per span, not per metric.
  - Graph-constrained: LLM only sees services that actually exist.
  - JSON schema output: machine-parseable, renderable as structured UI.
  - Graceful degradation: if Groq is unavailable or key is missing,
    returns a placeholder — the rest of the pipeline keeps working.

Output schema:
  {
    "root_cause_service":  str,
    "fault_type":          str,   # e.g. "database_connection_refused"
    "confidence_label":    str,   # "high" | "medium" | "low"
    "propagation_path":    [str],
    "human_summary":       str,   # 2-3 sentence plain English explanation
    "remediation_steps":   [str]  # ordered list of actionable steps
  }
"""
from __future__ import annotations

import json
import logging
from typing import Any

from groq import AsyncGroq, BadRequestError

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# ── Prompt templates ───────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """\
You are an expert Site Reliability Engineer (SRE) performing Root Cause Analysis \
on a microservice observability platform.

You will receive structured telemetry evidence about an active incident.
Your job is to explain the root cause in plain language that an on-call engineer \
can act on immediately.

Rules:
- Only reason about services listed in the service_graph.nodes. Do NOT hallucinate \
  services not in that list.
- Base your explanation strictly on the provided anomalies, error_spans, and error_logs.
- Return ONLY valid JSON matching the schema below. No extra text, no markdown fences.

Required JSON schema:
{
  "root_cause_service":  "<service name from the graph>",
  "fault_type":          "<concise technical fault type, e.g. database_connection_refused>",
  "confidence_label":    "<high|medium|low>",
  "propagation_path":    ["<service1>", "<service2>", "..."],
  "human_summary":       "<2-3 sentence plain English explanation of what is happening and why>",
  "remediation_steps":   ["<step 1>", "<step 2>", "<step 3>"]
}
"""


def _build_user_message(evidence: dict[str, Any]) -> str:
    """
    Convert the evidence dict from Phase 15 into a compact, LLM-friendly
    user message.

    We stringify as JSON (not raw Python repr) so the model sees clean structure.
    The evidence dict is already compressed by Phase 15 (top-N spans/logs, subgraph).
    """
    # Remove the _meta block — internal housekeeping, not useful for the model
    payload = {k: v for k, v in evidence.items() if k != "_meta"}
    return json.dumps(payload, indent=2)


def _is_reasoning_model(model: str) -> bool:
    m = model.lower()
    return "gpt-oss" in m or "qwen3" in m


def _short_error(e: Exception) -> str:
    """'NotFoundError: The model `x` does not exist …' — no 40-line traceback."""
    body = getattr(e, "body", None)
    if isinstance(body, dict):
        msg = (body.get("error") or {}).get("message") or str(body)
    else:
        msg = str(e)
    return f"{type(e).__name__}: {msg.splitlines()[0][:200]}"


def _parse_groq_response(content: str) -> dict[str, Any]:
    """
    Parse the Groq response into a dict.

    Groq with JSON mode returns clean JSON but we add a fallback strip in case
    the model wraps it in markdown fences despite the system prompt.
    """
    text = content.strip()
    # Strip markdown fences if present (defensive)
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(
            line for line in lines
            if not line.strip().startswith("```")
        ).strip()
    return json.loads(text)


def _validate_schema(parsed: dict[str, Any]) -> dict[str, Any]:
    """
    Ensure all required fields are present. Fill missing ones with defaults
    rather than crashing — the rest of the pipeline must keep working.
    """
    defaults = {
        "root_cause_service":  "unknown",
        "fault_type":          "unknown",
        "confidence_label":    "low",
        "propagation_path":    [],
        "human_summary":       "Explanation unavailable.",
        "remediation_steps":   [],
    }
    for key, default in defaults.items():
        if key not in parsed:
            logger.warning("Groq response missing field '%s', using default", key)
            parsed[key] = default
    return parsed


# ── Main Groq call ─────────────────────────────────────────────────────────────

async def generate_explanation(
    evidence: dict[str, Any],
) -> dict[str, Any]:
    """
    Call Groq with the evidence context and return the AI explanation dict.

    Returns a structured dict with the standard schema.
    If Groq is not configured or the call fails, returns a graceful placeholder.
    """
    settings = get_settings()

    if not settings.has_groq:
        logger.warning("GROQ_API_KEY not set — skipping AI explanation")
        return {
            "root_cause_service":  evidence.get("rca", {}).get("root_cause_service", "unknown"),
            "fault_type":          "unknown",
            "confidence_label":    "low",
            "propagation_path":    evidence.get("rca", {}).get("propagation_path", []),
            "human_summary":       (
                "AI explanation unavailable: GROQ_API_KEY not configured. "
                "Set GROQ_API_KEY in your .env file and run again."
            ),
            "remediation_steps":   [
                "Add GROQ_API_KEY to backend/.env",
                "Get a free key at https://console.groq.com/keys",
            ],
            "_ai_available": False,
        }

    try:
        client = AsyncGroq(api_key=settings.groq_api_key)
        user_message = _build_user_message(evidence)

        logger.info(
            "Calling Groq (%s) for incident %s",
            settings.groq_model,
            evidence.get("incident", {}).get("id"),
        )

        kwargs: dict[str, Any] = dict(
            model=settings.groq_model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user",   "content": user_message},
            ],
            temperature=0.1,       # Low temperature = more deterministic, less hallucination
            # Reasoning models (gpt-oss, qwen3) spend tokens thinking before they
            # answer — leave room so the JSON answer isn't cut off.
            max_tokens=2048,
            response_format={"type": "json_object"},  # Groq JSON mode
        )
        if _is_reasoning_model(settings.groq_model):
            # Short thinking keeps latency ~1–3 s; passed via extra_body so it
            # works on every groq SDK version.
            kwargs["extra_body"] = {"reasoning_effort": "low"}

        try:
            response = await client.chat.completions.create(**kwargs)
        except BadRequestError as e:
            # Some models reject JSON mode — retry once with a plain response;
            # the system prompt already demands JSON and the parser strips fences.
            logger.warning("Groq rejected request (%s) — retrying without JSON mode",
                           _short_error(e))
            kwargs.pop("response_format", None)
            response = await client.chat.completions.create(**kwargs)

        content = response.choices[0].message.content or ""
        parsed  = _parse_groq_response(content)
        result  = _validate_schema(parsed)
        result["_ai_available"] = True

        logger.info(
            "Groq explanation for incident %s: root=%s fault=%s confidence=%s",
            evidence.get("incident", {}).get("id"),
            result.get("root_cause_service"),
            result.get("fault_type"),
            result.get("confidence_label"),
        )
        return result

    except json.JSONDecodeError as e:
        logger.error("Groq returned non-JSON response: %s", e)
    except Exception as e:
        # One line, no traceback: the demo terminal must stay readable.
        logger.error("Groq call failed (model=%s): %s", settings.groq_model, _short_error(e))

    # Graceful fallback on any error
    return {
        "root_cause_service":  evidence.get("rca", {}).get("root_cause_service", "unknown"),
        "fault_type":          "unknown",
        "confidence_label":    "low",
        "propagation_path":    evidence.get("rca", {}).get("propagation_path", []),
        "human_summary":       "AI explanation generation failed. Check server logs.",
        "remediation_steps":   [],
        "_ai_available":       False,
    }
