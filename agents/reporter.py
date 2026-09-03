"""
Reporter Agent — Final node in the LangGraph workflow.

Responsibilities:
  1. Generate a structured markdown RCA report via Ollama llama3.2
  2. Save the incident to PostgreSQL
  3. Index the incident in Elasticsearch with embedding (for future similarity search)
  4. Publish incident summary to rca.results Kafka topic
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage

import storage.postgres_client as pg_store
import storage.elasticsearch_client as es_store
from agents.state import FaultLensState
from ml.log_clustering import embed_text
from pipeline.producer import publish
from pipeline.topics import RCA_RESULTS
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
            temperature=0.3,  # slight creativity for readable reports
        )
    return _llm


REPORT_SYSTEM_PROMPT = """You are the Reporter Agent in FaultLens, an incident intelligence system.
Generate a structured, actionable Root Cause Analysis (RCA) report in markdown.

Structure your report EXACTLY with these 4 main headings:

## 🚨 What is Going Down
- Affected service and current degradation state
- User/business impact (e.g. users failing checkout with 504 timeouts, slow catalog loading, rate-limited recommendations)

## 🔍 Root Cause & Causal Chain
- Probable root cause service identified by dependency graph traversal
- Causal chain showing how the error propagated (e.g. Service A → Service B → Root Cause)
- Diagnosis explaining why it happened

## 📊 Telemetry Evidence (Logs, Metrics, Traces)
- **Metrics**: Specific metrics that breached baseline (values and Z-scores)
- **Logs**: Error log snippets and template patterns detected
- **Traces**: Slow or failed spans identified in the service dependency graph

## 🛠️ What You Can Fix (Actionable Remediation)
- Immediate mitigation steps to restore production right now
- Exact configuration or command changes needed
- Preventative architecture fixes

Be specific, concise, and use the telemetry evidence provided. Do NOT hallucinate."""


async def reporter_node(state: FaultLensState) -> dict[str, Any]:
    """LangGraph node: generate RCA report and persist the incident."""
    service_id  = state["service_id"]
    incident_id = state["incident_id"]
    logger.info(f"[Reporter] Generating RCA report for incident {incident_id}")

    # ── Generate RCA report via LLM ───────────────────────────────────────────
    rca_report = _build_fallback_report(state)  # always have a fallback

    try:
        context = _build_report_context(state)
        llm = get_llm()
        response = await llm.ainvoke([
            SystemMessage(content=REPORT_SYSTEM_PROMPT),
            HumanMessage(content=context),
        ])
        rca_report = response.content
        logger.info(f"[Reporter] LLM report generated ({len(rca_report)} chars)")
    except Exception as e:
        logger.warning(f"[Reporter] LLM report generation failed, using fallback: {e}")

    # ── Persist to PostgreSQL ─────────────────────────────────────────────────
    try:
        await pg_store.update_incident(incident_id, {
            "environment_type": state.get("environment_type", "unknown"),
            "failure_type":     state.get("failure_type", ""),
            "confidence":       state.get("confidence", 0.0),
            "ranked_suspects":  state.get("ranked_suspects", []),
            "metric_anomalies": state.get("metric_anomalies", []),
            "log_anomalies":    state.get("log_anomalies", []),
            "trace_anomalies":  state.get("trace_anomalies", []),
            "causal_path":      state.get("causal_path", []),
            "rca_report":       rca_report,
            "team_routing":     state.get("team_routing", ""),
            "status":           "open",
        })
        logger.info(f"[Reporter] Incident {incident_id} saved to PostgreSQL")
    except Exception as e:
        logger.exception(f"[Reporter] Failed to save incident to PostgreSQL: {e}")

    # ── Index in Elasticsearch with embedding ─────────────────────────────────
    try:
        embedding = await embed_text(rca_report[:1000])
        incident_doc = {
            "incident_id":     incident_id,
            "service_id":      service_id,
            "failure_type":    state.get("failure_type", ""),
            "confidence":      state.get("confidence", 0.0),
            "ranked_suspects": state.get("ranked_suspects", []),
            "report":          rca_report,
            "created_at":      datetime.now(timezone.utc).isoformat(),
            "embedding":       embedding,
        }
        await es_store.insert_incident(incident_doc)
        logger.info(f"[Reporter] Incident {incident_id} indexed in Elasticsearch")
    except Exception as e:
        logger.warning(f"[Reporter] ES indexing failed: {e}")

    # ── Publish to Kafka ──────────────────────────────────────────────────────
    try:
        summary = {
            "incident_id":  incident_id,
            "service_id":   service_id,
            "failure_type": state.get("failure_type", ""),
            "confidence":   state.get("confidence", 0.0),
            "team_routing": state.get("team_routing", ""),
            "top_suspect":  state.get("ranked_suspects", [{}])[0].get("service_id", ""),
            "timestamp":    datetime.now(timezone.utc).isoformat(),
        }
        publish(RCA_RESULTS.name, summary, key=service_id)
        logger.info(f"[Reporter] Incident summary published to {RCA_RESULTS.name}")
    except Exception as e:
        logger.warning(f"[Reporter] Kafka publish failed: {e}")

    return {
        "rca_report":    rca_report,
        "nodes_executed": ["reporter"],
    }


def _build_report_context(state: FaultLensState) -> str:
    suspects = state.get("ranked_suspects", [])
    top = suspects[0] if suspects else {}
    lines = [
        f"Service: {state['service_id']}",
        f"Incident ID: {state['incident_id']}",
        f"Environment: {state['environment_type']}",
        f"Failure Type: {state.get('failure_type', 'unknown')}",
        f"Confidence: {state.get('confidence', 0):.0%}",
        f"Team Routing: {state.get('team_routing', 'unknown')}",
        "",
        f"Root Cause Service: {top.get('service_id', 'unknown')} (score={top.get('score', 0):.3f})",
        f"LLM Reasoning: {top.get('llm_reasoning', 'N/A')}",
        "",
        "Causal Path: " + " → ".join(state.get("causal_path", [])),
        "",
        "Metric Anomalies:",
        *[f"  • {a.get('evidence', a.get('metric_name', ''))}" for a in state.get("metric_anomalies", [])[:5]],
        "",
        "Log Anomalies:",
        *[f"  • {a.get('reason', '')}" for a in state.get("log_anomalies", [])[:5]],
        "",
        "Trace Anomalies:",
        *[f"  • {a.get('evidence', '')}" for a in state.get("trace_anomalies", [])[:5]],
        "",
        "Recommended Remediation Actions (use these to write the What You Can Fix section):",
        *[f"  • {r}" for r in state.get("remediation_steps", [])],
    ]
    return "\n".join(lines)


def _build_fallback_report(state: FaultLensState) -> str:
    """Structured report when LLM is unavailable or for fallback."""
    suspects = state.get("ranked_suspects", [])
    top = suspects[0].get("service_id", "unknown") if suspects else "unknown"
    remediations = state.get("remediation_steps", [
        "Inspect service logs and metrics in Elasticsearch and TimescaleDB.",
        "Check recent deployment diffs or environment variable changes.",
    ])

    metric_bullets = [f"- {a.get('evidence') or a.get('metric_name')}" for a in state.get("metric_anomalies", [])] or ["- No metric anomalies detected"]
    log_bullets = [f"- {a.get('reason') or a.get('template')}" for a in state.get("log_anomalies", [])] or ["- No error log spikes observed"]
    trace_bullets = [f"- {a.get('evidence') or a.get('type')}" for a in state.get("trace_anomalies", [])] or ["- Dependency graph edges within normal bounds"]
    remediation_bullets = [f"1. {r}" for r in remediations]

    return (
        f"## 🚨 What is Going Down\n"
        f"- **Service Affected**: `{state['service_id']}` ({state.get('environment_type', 'rich')} environment)\n"
        f"- **Incident Status**: ACTIVE (Unresolved in Production)\n"
        f"- **Classification**: `{state.get('failure_type', 'UNHANDLED_EXCEPTION')}` (Confidence: {state.get('confidence', 0.8):.0%})\n"
        f"- **Assigned Team**: {state.get('team_routing', 'Backend Engineering')}\n\n"
        f"## 🔍 Root Cause & Causal Chain\n"
        f"- **Primary Suspect**: `{top}`\n"
        f"- **Causal Path**: {' → '.join(state.get('causal_path', [state['service_id']]))}\n"
        f"- **Root Cause Analysis**: Anomaly propagation detected from `{top}` impacting `{state['service_id']}`.\n\n"
        f"## 📊 Telemetry Evidence (Logs, Metrics, Traces)\n"
        f"### Metrics\n" + "\n".join(metric_bullets) + "\n\n"
        f"### Logs\n" + "\n".join(log_bullets) + "\n\n"
        f"### Traces\n" + "\n".join(trace_bullets) + "\n\n"
        f"## 🛠️ What You Can Fix (Actionable Remediation)\n" + "\n".join(remediation_bullets) + "\n"
    )
