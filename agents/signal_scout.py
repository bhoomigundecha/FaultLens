"""
Signal Scout Agent — Node 1 in the LangGraph workflow.

Responsibilities:
  1. Read the detected environment type from PostgreSQL
  2. Summarise what signals are available in the lookback window
  3. Use LLM to decide which analysis path to activate (rich vs thin)
  4. Update state with environment_type
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage

import storage.postgres_client as pg_store
import storage.timescale as ts_store
import storage.elasticsearch_client as es_store
from agents.state import FaultLensState
from config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_llm: ChatOllama | None = None


def get_llm() -> ChatOllama:
    global _llm
    if _llm is None:
        _llm = ChatOllama(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            temperature=0.1,
        )
    return _llm


SYSTEM_PROMPT = """You are the Signal Scout agent in FaultLens, an incident intelligence system.
Your job is to assess what telemetry signals are available for a service and determine
the best analysis strategy.

You will be given a summary of signals detected in the last few minutes.
Respond ONLY with a JSON object in this exact format:
{
  "environment_assessment": "brief description of what signals are available",
  "recommended_strategy": "rich | medium | thin",
  "reasoning": "1-2 sentences explaining why"
}"""


async def signal_scout_node(state: FaultLensState) -> dict[str, Any]:
    """LangGraph node: assess environment and route the workflow."""
    service_id = state["service_id"]
    logger.info(f"[SignalScout] Assessing environment for {service_id}")

    # ── Read environment type from DB ─────────────────────────────────────────
    svc = await pg_store.get_service(service_id)
    env_type = svc["env_type"] if svc else "unknown"

    # ── Gather signal summary for LLM context ─────────────────────────────────
    metric_summary = ""
    log_summary = ""

    try:
        all_metrics = await ts_store.get_all_metrics_for_service(
            service_id, window_minutes=settings.metric_window_minutes
        )
        if all_metrics:
            metric_names = list(all_metrics.keys())[:5]
            metric_summary = f"Metrics available: {metric_names} ({sum(len(v) for v in all_metrics.values())} data points)"
        else:
            metric_summary = "No metrics in recent window."
    except Exception as e:
        metric_summary = f"Metrics unavailable: {e}"

    try:
        error_count = await es_store.get_error_log_count(
            service_id, window_minutes=settings.metric_window_minutes
        )
        log_summary = f"Log error count (last {settings.metric_window_minutes}m): {error_count}"
    except Exception as e:
        log_summary = f"Logs unavailable: {e}"

    signal_summary = (
        f"Service: {service_id}\n"
        f"Detected environment type: {env_type}\n"
        f"{metric_summary}\n"
        f"{log_summary}"
    )

    # ── LLM reasoning ─────────────────────────────────────────────────────────
    try:
        llm = get_llm()
        response = await llm.ainvoke([
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=f"Signal summary:\n{signal_summary}"),
        ])
        import json, re
        raw = response.content
        json_match = re.search(r"\{.*\}", raw, re.DOTALL)
        if json_match:
            parsed = json.loads(json_match.group())
            env_type = parsed.get("recommended_strategy", env_type)
            reasoning = parsed.get("reasoning", "")
            logger.info(f"[SignalScout] {service_id} → {env_type}: {reasoning}")
    except Exception as e:
        logger.warning(f"[SignalScout] LLM call failed, using DB env_type: {e}")

    return {
        "environment_type": env_type,
        "nodes_executed": ["signal_scout"],
    }
