"""
Master RCA Investigator Agent — ReAct-powered autonomous root cause analysis.

This is the true agentic core of FaultLens. Unlike the other nodes (which
run deterministic data-gathering pipelines), this node uses a ReAct loop:

  Observe → Reason → Act (call a tool) → Observe → Reason → Act → … → Conclude

The LLM (Ollama llama3.2) is given:
  1. Pre-gathered evidence from anomaly_hunter + graph_weaver (context)
  2. A set of investigative tools it can call freely
  3. A goal: identify the root cause service and explain the causal chain

The agent decides WHAT to investigate, WHEN it has enough evidence, and
WHAT the root cause is. Nothing is hardcoded — it's driven by LLM reasoning.

Tools available to the agent:
  - query_metric_window       : fetch raw metric values for any service/metric
  - run_zscore_on_metric      : run Z-score detection on a specific metric
  - search_logs               : search logs by keyword or service
  - get_service_dependencies  : get upstream/downstream services from Neo4j
  - run_pagerank              : score services by causal centrality
  - find_similar_incidents    : semantic search of past incidents in ES
  - classify_failure_type     : classify into known failure taxonomy
  - get_error_rate            : get HTTP error rate for a service in a window
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from langchain_ollama import ChatOllama
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, ToolMessage
from langchain_core.utils.function_calling import convert_to_openai_tool

import storage.timescale as ts_store
import storage.elasticsearch_client as es_store
import storage.neo4j_client as neo4j_store
import storage.postgres_client as pg_store
from agents.state import FaultLensState
from ml.anomaly_detection import run_zscore as _run_zscore
from ml.log_clustering import embed_text, parse_log
from ml.fusion import fuse_scores
from agents.triage import FAILURE_TAXONOMY
from config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Maximum ReAct iterations before forcing a conclusion
MAX_ITERATIONS = 8


# ─── Tool definitions ─────────────────────────────────────────────────────────
# These are the tools the LLM can autonomously choose to call.
# Each returns a string — the LLM reads the result and decides what to do next.

def _make_tools(service_id: str):
    """
    Build tool functions bound to the current service context.
    Returns a list of (tool_fn, openai_schema) pairs.
    """

    async def query_metric_window(target_service_id: str, metric_name: str, window_minutes: int = 15) -> str:
        """
        Fetch recent values of a specific metric for a service.
        Use this to investigate whether a particular metric is anomalous.
        Returns: recent values as a JSON list with timestamps.
        """
        try:
            rows = await ts_store.get_metric_window(target_service_id, metric_name, window_minutes)
            if not rows:
                return f"No data found for metric '{metric_name}' on '{target_service_id}' in the last {window_minutes} minutes."
            values = [{"time": str(r["time"]), "value": r["value"]} for r in rows[-20:]]
            return json.dumps({"metric": metric_name, "service": target_service_id, "data_points": values})
        except Exception as e:
            return f"Error querying metric: {e}"

    async def run_zscore_on_metric(target_service_id: str, metric_name: str) -> str:
        """
        Run Z-score anomaly detection on a specific metric for a service.
        Use this when you suspect a metric might be anomalous but need statistical confirmation.
        Returns: whether the metric is anomalous, the Z-score, and the baseline.
        """
        try:
            rows = await ts_store.get_metric_window(target_service_id, metric_name)
            if not rows:
                return f"No data for '{metric_name}' on '{target_service_id}' — cannot run Z-score."
            values = [r["value"] for r in rows]
            results = _run_zscore(target_service_id, metric_name, values)
            anomalous = [r for r in results if r.is_anomaly]
            if anomalous:
                worst = max(anomalous, key=lambda r: r.score)
                return (
                    f"ANOMALY DETECTED: {metric_name} on {target_service_id}\n"
                    f"  Value: {worst.value:.2f}\n"
                    f"  Z-score: {worst.z_score:.2f}σ (threshold={settings.zscore_threshold}σ)\n"
                    f"  Baseline: mean={worst.baseline_mean:.2f}, stddev={worst.baseline_stddev:.2f}"
                )
            return f"No anomaly detected in '{metric_name}' on '{target_service_id}'. Latest value: {values[-1]:.2f}"
        except Exception as e:
            return f"Z-score detection error: {e}"

    async def search_logs(target_service_id: str, keyword: str = "", window_minutes: int = 15) -> str:
        """
        Search recent logs for a service, optionally filtered by keyword.
        Use this to find specific error patterns, exception messages, or status codes.
        Returns: up to 10 matching log entries.
        """
        try:
            logs = await es_store.get_logs_window(target_service_id, window_minutes)
            if keyword:
                logs = [l for l in logs if keyword.lower() in l.get("body", "").lower()]
            if not logs:
                return f"No logs found for '{target_service_id}'" + (f" matching '{keyword}'" if keyword else "") + "."
            entries = [{"level": l.get("level"), "body": l.get("body", "")[:200]} for l in logs[:10]]
            return json.dumps({"service": target_service_id, "keyword": keyword, "logs": entries})
        except Exception as e:
            return f"Log search error: {e}"

    def get_service_dependencies(target_service_id: str) -> str:
        """
        Get the upstream callers and downstream dependencies of a service.
        Use this to understand the call chain and identify where a failure could originate.
        Returns: lists of upstream callers and downstream callees.
        """
        try:
            upstream = neo4j_store.get_upstream_callers(target_service_id)
            downstream = neo4j_store.get_downstream_callees(target_service_id)
            graph = neo4j_store.get_service_subgraph(target_service_id, depth=2)
            edges_with_health = [
                {
                    "from": e["source"],
                    "to": e["target"],
                    "latency_p99_ms": e.get("latency_p99_ms"),
                    "error_rate": e.get("error_rate"),
                }
                for e in graph.get("edges", [])
            ]
            return json.dumps({
                "service": target_service_id,
                "upstream_callers": upstream,
                "downstream_callees": downstream,
                "edge_health": edges_with_health,
            })
        except Exception as e:
            return f"Dependency query error: {e}"

    def run_pagerank(seed_service_ids: list[str], seed_scores: list[float]) -> str:
        """
        Run personalised PageRank on the service graph starting from suspected services.
        Use this to propagate anomaly scores and rank all services by likelihood of being root cause.
        seed_service_ids: list of service IDs you suspect are involved.
        seed_scores: anomaly score for each seed service (0.0 to 1.0).
        Returns: ranked list of services with PageRank scores.
        """
        try:
            seeds = dict(zip(seed_service_ids, seed_scores))
            scores = neo4j_store.run_pagerank(seeds)
            ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:10]
            return json.dumps({"pagerank_scores": [{"service": k, "score": round(v, 4)} for k, v in ranked]})
        except Exception as e:
            return f"PageRank error: {e}"

    async def find_similar_incidents(description: str) -> str:
        """
        Search historical incidents for similar failures using semantic similarity.
        Use this to check if this pattern has been seen before and how it was resolved.
        description: brief description of what you're seeing (will be embedded for search).
        Returns: up to 3 similar past incidents with their failure types and reports.
        """
        try:
            embedding = await embed_text(description[:512])
            if not embedding:
                return "Embedding unavailable — cannot search historical incidents."
            similar = await es_store.search_similar_incidents(embedding, k=3)
            if not similar:
                return "No similar incidents found in history."
            results = [
                {
                    "failure_type": s.get("failure_type"),
                    "confidence": s.get("confidence"),
                    "summary": (s.get("report", "")[:300]),
                }
                for s in similar
            ]
            return json.dumps({"similar_incidents": results})
        except Exception as e:
            return f"Similarity search error: {e}"

    async def get_error_rate(target_service_id: str, window_minutes: int = 15) -> str:
        """
        Get the HTTP error count and approximate error rate for a service.
        Use this as a quick health check for any service in the call chain.
        Returns: error count and rate description.
        """
        try:
            err_count = await es_store.get_error_log_count(target_service_id, window_minutes)
            all_logs = await es_store.get_logs_window(target_service_id, window_minutes)
            total = len(all_logs) if all_logs else 0
            rate = err_count / total if total > 0 else 0.0
            severity = "HIGH" if rate > 0.3 else "MEDIUM" if rate > 0.1 else "LOW"
            return (
                f"Service '{target_service_id}' in last {window_minutes}m:\n"
                f"  Error count: {err_count}\n"
                f"  Total logs:  {total}\n"
                f"  Error rate:  {rate:.1%} ({severity})"
            )
        except Exception as e:
            return f"Error rate query failed: {e}"

    def classify_failure_type(evidence_description: str) -> str:
        """
        Match evidence against the known failure taxonomy to get a failure type classification.
        Use this once you have enough evidence to name the failure type.
        evidence_description: describe what you found in plain text.
        Returns: most likely failure type and the team to route to.
        """
        evidence_lower = evidence_description.lower()
        matches = []
        for ftype, meta in FAILURE_TAXONOMY.items():
            count = sum(1 for kw in meta["keywords"] if kw in evidence_lower)
            if count > 0:
                matches.append((ftype, count, meta["team"]))
        matches.sort(key=lambda x: x[1], reverse=True)
        if matches:
            best = matches[0]
            return json.dumps({
                "failure_type": best[0],
                "team": best[2],
                "confidence": min(1.0, best[1] / 3.0),
                "alternatives": [m[0] for m in matches[1:3]],
            })
        return json.dumps({"failure_type": "UNHANDLED_EXCEPTION", "team": "backend", "confidence": 0.3})

    # ── Tool registry ─────────────────────────────────────────────────────────
    tool_fns = {
        "query_metric_window":     query_metric_window,
        "run_zscore_on_metric":    run_zscore_on_metric,
        "search_logs":             search_logs,
        "get_service_dependencies": get_service_dependencies,
        "run_pagerank":            run_pagerank,
        "find_similar_incidents":  find_similar_incidents,
        "get_error_rate":          get_error_rate,
        "classify_failure_type":   classify_failure_type,
    }

    # OpenAI-compatible tool schemas for Ollama tool-calling
    tool_schemas = [
        {
            "type": "function",
            "function": {
                "name": "query_metric_window",
                "description": "Fetch recent values of a specific metric for a service.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "target_service_id": {"type": "string", "description": "Service ID to query"},
                        "metric_name":       {"type": "string", "description": "Metric name (e.g. http.request.duration_ms)"},
                        "window_minutes":    {"type": "integer", "description": "Lookback window in minutes", "default": 15},
                    },
                    "required": ["target_service_id", "metric_name"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "run_zscore_on_metric",
                "description": "Run Z-score anomaly detection on a specific metric.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "target_service_id": {"type": "string"},
                        "metric_name":       {"type": "string"},
                    },
                    "required": ["target_service_id", "metric_name"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "search_logs",
                "description": "Search recent logs for a service, optionally filtered by keyword.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "target_service_id": {"type": "string"},
                        "keyword":           {"type": "string", "description": "Keyword to filter logs (optional)", "default": ""},
                        "window_minutes":    {"type": "integer", "default": 15},
                    },
                    "required": ["target_service_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_service_dependencies",
                "description": "Get upstream callers and downstream dependencies of a service from the graph.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "target_service_id": {"type": "string"},
                    },
                    "required": ["target_service_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "run_pagerank",
                "description": "Run personalised PageRank to rank services by likelihood of being root cause.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "seed_service_ids": {"type": "array",  "items": {"type": "string"}},
                        "seed_scores":      {"type": "array",  "items": {"type": "number"}},
                    },
                    "required": ["seed_service_ids", "seed_scores"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "find_similar_incidents",
                "description": "Search historical incidents for similar failures.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "description": {"type": "string", "description": "Brief description of the anomaly pattern"},
                    },
                    "required": ["description"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_error_rate",
                "description": "Get error count and rate for a service.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "target_service_id": {"type": "string"},
                        "window_minutes":    {"type": "integer", "default": 15},
                    },
                    "required": ["target_service_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "classify_failure_type",
                "description": "Match evidence against known failure taxonomy to get a failure type.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "evidence_description": {
                            "type": "string",
                            "description": "Plain text description of all evidence found so far",
                        },
                    },
                    "required": ["evidence_description"],
                },
            },
        },
    ]

    return tool_fns, tool_schemas


# ─── ReAct loop ───────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are the Master RCA Investigator in FaultLens, an incident intelligence system.

Your mission: autonomously investigate a service incident and identify the root cause.

You have access to investigative tools. Use them strategically:
1. Start by reviewing the pre-gathered evidence provided to you
2. Use tools to DIG DEEPER into suspicious areas — check specific metrics, search logs, trace dependencies
3. Run PageRank once you have a set of suspect services
4. Check if similar incidents have occurred before
5. Once confident, classify the failure type

When you have identified the root cause, respond with FINAL_ANSWER in this exact JSON format:
{
  "FINAL_ANSWER": true,
  "root_cause_service": "service-id",
  "failure_type": "FAILURE_TYPE",
  "confidence": 0.85,
  "causal_path": ["service-a", "service-b", "root-cause"],
  "ranked_suspects": [{"service_id": "x", "score": 0.9, "evidence": "..."}],
  "reasoning": "2-3 sentences explaining the causal chain"
}

Be thorough but decisive. Do not call the same tool twice with identical arguments."""


async def _call_tool(tool_name: str, tool_args: dict, tool_fns: dict) -> str:
    """Dispatch a tool call and return the string result."""
    fn = tool_fns.get(tool_name)
    if fn is None:
        return f"Unknown tool: {tool_name}"
    try:
        import asyncio
        import inspect
        if inspect.iscoroutinefunction(fn):
            return await fn(**tool_args)
        else:
            return fn(**tool_args)
    except TypeError as e:
        return f"Tool call error ({tool_name}): {e}"
    except Exception as e:
        return f"Tool execution error ({tool_name}): {e}"


async def rca_investigator_node(state: FaultLensState) -> dict[str, Any]:
    """
    LangGraph node: ReAct-powered autonomous RCA investigation.

    The LLM drives this loop — it reads evidence, decides which tools to call,
    interprets results, and iterates until it can confidently name the root cause.
    """
    service_id = state["service_id"]
    logger.info(f"[RCAInvestigator] Starting autonomous investigation for {service_id}")

    # Build tools
    tool_fns, tool_schemas = _make_tools(service_id)

    # Build LLM (with tool-calling)
    llm = ChatOllama(
        model=settings.ollama_model,
        base_url=settings.ollama_base_url,
        temperature=0.1,
    )

    # Build initial context from pre-gathered evidence
    initial_context = _build_initial_context(state)

    # ── ReAct message history ─────────────────────────────────────────────────
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=initial_context),
    ]

    # ── ReAct loop ────────────────────────────────────────────────────────────
    iteration = 0
    final_answer: dict | None = None
    all_tool_calls_made: list[str] = []

    while iteration < MAX_ITERATIONS and final_answer is None:
        iteration += 1
        logger.info(f"[RCAInvestigator] Iteration {iteration}/{MAX_ITERATIONS}")

        try:
            # Call LLM with tool schemas
            response = await llm.ainvoke(
                messages,
                tools=tool_schemas,
            )
            messages.append(response)

            response_text = response.content or ""

            # ── Check for FINAL_ANSWER ─────────────────────────────────────────
            if "FINAL_ANSWER" in response_text:
                json_match = re.search(r"\{.*\"FINAL_ANSWER\".*\}", response_text, re.DOTALL)
                if json_match:
                    try:
                        final_answer = json.loads(json_match.group())
                        logger.info(
                            f"[RCAInvestigator] Agent reached conclusion after {iteration} iterations: "
                            f"{final_answer.get('root_cause_service')} ({final_answer.get('failure_type')})"
                        )
                        break
                    except json.JSONDecodeError:
                        pass

            # ── Process tool calls if LLM made any ────────────────────────────
            tool_calls = getattr(response, "tool_calls", None) or []

            if not tool_calls:
                # Model might have encoded tool call in content — try to extract
                tool_calls = _extract_tool_calls_from_content(response_text)

            if tool_calls:
                for tc in tool_calls:
                    tool_name = tc.get("name") or tc.get("function", {}).get("name", "")
                    raw_args  = tc.get("args") or tc.get("function", {}).get("arguments", "{}")
                    tool_args = raw_args if isinstance(raw_args, dict) else json.loads(raw_args or "{}")

                    call_signature = f"{tool_name}({json.dumps(tool_args)[:80]})"
                    if call_signature in all_tool_calls_made:
                        logger.debug(f"[RCAInvestigator] Skipping duplicate tool call: {call_signature}")
                        continue

                    all_tool_calls_made.append(call_signature)
                    logger.info(f"[RCAInvestigator]   🔧 Calling tool: {tool_name}({list(tool_args.keys())})")

                    result = await _call_tool(tool_name, tool_args, tool_fns)
                    logger.info(f"[RCAInvestigator]   ↩  Tool result ({tool_name}): {result[:150]}")

                    # Append tool result so LLM sees it next iteration
                    messages.append(HumanMessage(content=f"Tool '{tool_name}' result:\n{result}"))
            else:
                # No tool calls and no FINAL_ANSWER — nudge the agent
                if iteration < MAX_ITERATIONS:
                    messages.append(HumanMessage(
                        content="Continue your investigation. Call more tools if needed, or provide your FINAL_ANSWER."
                    ))

        except Exception as e:
            logger.exception(f"[RCAInvestigator] LLM error on iteration {iteration}: {e}")
            messages.append(HumanMessage(content=f"There was an error. Continue with what you know."))

    # ── Extract results from final answer (or fallback) ───────────────────────
    if final_answer:
        ranked_suspects = final_answer.get("ranked_suspects") or [
            {"service_id": final_answer.get("root_cause_service", service_id),
             "score": final_answer.get("confidence", 0.5),
             "evidence": final_answer.get("reasoning", "")}
        ]
        return {
            "ranked_suspects":  ranked_suspects,
            "causal_path":      final_answer.get("causal_path", [service_id]),
            "confidence":       float(final_answer.get("confidence", 0.5)),
            "failure_type":     final_answer.get("failure_type", ""),
            "pagerank_scores":  {},
            "nodes_executed":   ["rca_investigator"],
        }

    # Fallback if agent didn't converge
    logger.warning(f"[RCAInvestigator] Agent did not converge in {MAX_ITERATIONS} iterations, using heuristic fallback")
    return _heuristic_fallback(state)


def _build_initial_context(state: FaultLensState) -> str:
    """Build the initial evidence briefing for the LLM."""
    lines = [
        f"=== INCIDENT INVESTIGATION BRIEF ===",
        f"Service under investigation: {state['service_id']}",
        f"Environment type: {state['environment_type']}",
        f"",
        "=== PRE-GATHERED EVIDENCE ===",
        "",
        "METRIC ANOMALIES detected by AnomalyHunter:",
    ]
    for a in state.get("metric_anomalies", [])[:5]:
        lines.append(f"  • {a.get('evidence') or a.get('metric_name', 'unknown metric')}")

    lines.append("\nLOG ANOMALIES:")
    for a in state.get("log_anomalies", [])[:5]:
        lines.append(f"  • {a.get('reason', '')}")

    lines.append("\nTRACE/DEPENDENCY ANOMALIES (from service graph):")
    for a in state.get("trace_anomalies", [])[:5]:
        lines.append(f"  • {a.get('evidence', '')}")

    lines += [
        "",
        "=== YOUR TASK ===",
        "Use the tools available to you to investigate this incident further.",
        "Dig into specific metrics, search logs for error patterns, trace the dependency graph.",
        "When you have identified the root cause with confidence, provide your FINAL_ANSWER.",
    ]
    return "\n".join(lines)


def _extract_tool_calls_from_content(content: str) -> list[dict]:
    """
    Fallback: some Ollama versions embed tool calls as JSON in content rather
    than using the tool_calls field. Try to parse them out.
    """
    tool_calls = []
    # Look for patterns like {"name": "tool_name", "arguments": {...}}
    for match in re.finditer(r'\{"name":\s*"(\w+)".*?"arguments":\s*(\{[^}]+\})', content, re.DOTALL):
        try:
            tool_calls.append({
                "name": match.group(1),
                "args": json.loads(match.group(2)),
            })
        except Exception:
            pass
    return tool_calls


def _heuristic_fallback(state: FaultLensState) -> dict[str, Any]:
    """If the agent doesn't converge, use the pre-gathered anomaly scores."""
    suspects_from_traces = [
        {"service_id": a.get("callee", state["service_id"]), "score": a.get("score", 0.5), "evidence": a.get("evidence", "")}
        for a in state.get("trace_anomalies", [])
        if a.get("callee")
    ]
    ranked = sorted(suspects_from_traces, key=lambda x: x["score"], reverse=True) or [
        {"service_id": state["service_id"], "score": 0.4, "evidence": "Heuristic fallback — agent did not converge"}
    ]
    return {
        "ranked_suspects": ranked,
        "causal_path":     [state["service_id"]],
        "confidence":      0.3,
        "failure_type":    "",
        "pagerank_scores": {},
        "nodes_executed":  ["rca_investigator"],
    }
