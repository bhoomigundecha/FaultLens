"""
Triage Agent — Node 5 in the LangGraph workflow.

Responsibilities:
  1. Classify the failure into a specific failure type (rule-based first, LLM fallback)
  2. Determine which team should handle it
  3. Check if an SLO is breached
  4. Update state with failure_type, team_routing
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.language_models.chat_models import BaseChatModel

from agents.llm import get_chat_llm

from agents.state import FaultLensState
from config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# ─── Failure taxonomy ─────────────────────────────────────────────────────────

FAILURE_TAXONOMY: dict[str, dict[str, Any]] = {
    "DB_CONNECTION_POOL_EXHAUSTED": {
        "team": "backend",
        "keywords": ["connection pool", "too many connections", "connection refused", "pool exhausted"],
        "metric_signals": ["db.connections.active", "db.pool.size"],
        "remediation": [
            "Scale up DB connection pool limit (`DB_POOL_MAX` from 10 to 25+).",
            "Terminate idle transactions: `SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle in transaction';`",
            "Identify slow queries holding connections: `SELECT pid, query, now() - query_start AS duration FROM pg_stat_activity WHERE state != 'idle' ORDER BY duration DESC;`",
            "Implement PgBouncer or server-side connection pooler with transaction pooling mode.",
        ],
    },
    "DB_QUERY_TIMEOUT": {
        "team": "backend",
        "keywords": ["query timeout", "statement timeout", "lock timeout", "deadlock"],
        "metric_signals": ["db.query.duration"],
        "remediation": [
            "Check for table/row lock contention: `SELECT * FROM pg_locks pl JOIN pg_stat_activity psa ON pl.pid = psa.pid;`",
            "Verify missing indexes on queried columns/foreign keys (e.g. `order_items.order_id`, `product_id`).",
            "Enforce strict `statement_timeout = '3000ms'` to prevent runaway queries from blocking other connections.",
            "Retry deadlock transactions with exponential jitter in the application layer.",
        ],
    },
    "AI_RATE_LIMIT_EXCEEDED": {
        "team": "ml-platform",
        "keywords": ["rate limit", "too many requests", "429", "quota exceeded", "rate exceeded"],
        "metric_signals": ["ai.request.error_count", "http.request.error_count"],
        "remediation": [
            "Increase API token quota or RPM limit tier in model provider console.",
            "Enable Redis cache-aside for LLM prompts with a 15-minute TTL to deduplicate requests.",
            "Ensure graceful degradation: fall back to precomputed or trending recommendations when provider returns 429.",
            "Implement a client-side token-bucket rate limiter with exponential backoff and jitter.",
        ],
    },
    "AI_MODEL_TIMEOUT": {
        "team": "ml-platform",
        "keywords": ["model timeout", "inference timeout", "llm timeout"],
        "metric_signals": ["ai.request.duration_ms"],
        "remediation": [
            "Lower inference timeout from 30s to 5-8s and serve cached fallback.",
            "Switch to a smaller/quantized model (e.g., llama3.2:3b vs larger models) for low-latency endpoints.",
            "Ensure GPU acceleration is active on the inference node.",
        ],
    },
    "HIGH_LATENCY_SPIKE": {
        "team": "backend",
        "keywords": ["slow response", "high latency", "timeout", "took too long"],
        "metric_signals": ["http.request.duration_ms", "http.server.request.duration"],
        "remediation": [
            "Inspect downstream dependency latency along the trace causal path.",
            "Tune HTTP client timeouts down to 3000ms to fail fast and release worker threads.",
            "Configure circuit breaker to trip after 5 consecutive slow responses.",
            "Scale horizontal replicas of the affected downstream service.",
        ],
    },
    "CASCADE_FAILURE": {
        "team": "backend",
        "keywords": ["downstream", "upstream failure", "dependency failure", "service unavailable"],
        "metric_signals": ["http.request.error_count"],
        "remediation": [
            "Trip the circuit breaker on the failing dependency to stop cascading timeouts.",
            "Return graceful partial fallback data (e.g. queue checkout requests asynchronously).",
            "Apply exponential backoff with jitter on retry attempts to prevent retry storms.",
        ],
    },
    "HIGH_MEMORY_PRESSURE": {
        "team": "infra",
        "keywords": ["out of memory", "oom", "memory exhausted", "heap", "gc pressure"],
        "metric_signals": ["process.runtime.jvm.memory", "nodejs.memory.heap_used"],
        "remediation": [
            "Increase container memory limit (`resources.limits.memory`).",
            "Inspect Node.js heap snapshot or memory profile for uncollected references or stream buffers.",
            "Restart failing service pods and enable horizontal pod autoscaling on memory > 80%.",
        ],
    },
    "UNHANDLED_EXCEPTION": {
        "team": "backend",
        "keywords": ["unhandled exception", "uncaught error", "stack trace", "500"],
        "metric_signals": ["http.request.error_count"],
        "remediation": [
            "Inspect error stack trace in Elasticsearch logs around the incident timestamp.",
            "Add defensive null-checks / validation around the failing code path.",
            "Wrap unhandled asynchronous rejections in global process error handlers.",
        ],
    },
    "UPSTREAM_DEPENDENCY_FAILURE": {
        "team": "infra",
        "keywords": ["econnrefused", "connection refused", "host unreachable", "dns lookup failed"],
        "metric_signals": [],
        "remediation": [
            "Verify network reachability and health endpoint of the target service.",
            "Check Kubernetes/Docker status for OOMKilled crashes or crash-looping containers.",
            "Verify internal DNS resolution and service discovery.",
        ],
    },
}

TEAM_ROUTING: dict[str, str] = {
    "backend":     "Backend Engineering",
    "infra":       "Infrastructure / SRE",
    "ml-platform": "ML Platform Team",
}


def _rule_based_classify(
    log_anomalies: list[dict], metric_anomalies: list[dict], trace_anomalies: list[dict]
) -> str | None:
    """
    Try to classify failure type from keyword matching in log templates.
    Returns failure type string or None if no match.
    """
    all_evidence = " ".join([
        a.get("template", "") + " " + a.get("reason", "")
        for a in log_anomalies
    ] + [
        a.get("evidence", "")
        for a in metric_anomalies + trace_anomalies
    ]).lower()

    best_match: str | None = None
    best_count = 0

    for failure_type, meta in FAILURE_TAXONOMY.items():
        count = sum(1 for kw in meta["keywords"] if kw in all_evidence)
        if count > best_count:
            best_count = count
            best_match = failure_type

    return best_match if best_count > 0 else None


def get_llm() -> BaseChatModel:
    return get_chat_llm(temperature=0.0)


TRIAGE_SYSTEM_PROMPT = f"""You are the Triage Agent in FaultLens.
Classify the incident into ONE of these failure types:
{json.dumps(list(FAILURE_TAXONOMY.keys()), indent=2)}

Respond ONLY with JSON:
{{
  "failure_type": "FAILURE_TYPE_FROM_LIST",
  "team": "backend | infra | ml-platform",
  "reasoning": "one sentence"
}}"""


async def triage_node(state: FaultLensState) -> dict[str, Any]:
    """LangGraph node: classify failure type and route to team."""
    service_id = state["service_id"]
    logger.info(f"[Triage] Classifying failure for {service_id}")

    # ── Rule-based classification first ──────────────────────────────────────
    failure_type = _rule_based_classify(
        state.get("log_anomalies", []),
        state.get("metric_anomalies", []),
        state.get("trace_anomalies", []),
    )
    team = "backend"  # default

    if failure_type:
        team = FAILURE_TAXONOMY[failure_type]["team"]
        logger.info(f"[Triage] Rule-based classification: {failure_type} → {team}")
    else:
        # ── LLM fallback ──────────────────────────────────────────────────────
        try:
            evidence = (
                f"Service: {service_id}\n"
                f"Metric anomalies: {state.get('metric_anomalies', [])[:3]}\n"
                f"Log anomalies: {state.get('log_anomalies', [])[:3]}\n"
                f"Root cause service: {state.get('ranked_suspects', [{}])[0].get('service_id', 'unknown')}\n"
                f"Causal path: {state.get('causal_path', [])}"
            )
            llm = get_llm()
            response = await llm.ainvoke([
                SystemMessage(content=TRIAGE_SYSTEM_PROMPT),
                HumanMessage(content=evidence),
            ])
            json_match = re.search(r"\{.*\}", response.content, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
                failure_type = parsed.get("failure_type", "UNHANDLED_EXCEPTION")
                team = parsed.get("team", "backend")
                logger.info(f"[Triage] LLM classification: {failure_type} → {team}")
        except Exception as e:
            logger.warning(f"[Triage] LLM triage failed: {e}")
            failure_type = "UNHANDLED_EXCEPTION"

    team_display = TEAM_ROUTING.get(team, team)
    remediation_steps = FAILURE_TAXONOMY.get(failure_type, {}).get("remediation", [
        "Inspect service logs and metrics in Elasticsearch and TimescaleDB.",
        "Check recent deployment diffs or environment variable changes.",
    ])

    return {
        "failure_type":      failure_type or "UNHANDLED_EXCEPTION",
        "team_routing":      team_display,
        "remediation_steps": remediation_steps,
        "nodes_executed":    ["triage"],
    }
