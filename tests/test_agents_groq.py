"""
Verification tests for Groq LLM integration across FaultLens agents.
"""

import asyncio
import json
import re
import pytest
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from agents.llm import get_chat_llm
from config.settings import get_settings


@pytest.mark.asyncio
async def test_llm_factory():
    """Verify get_chat_llm returns a functioning ChatGroq instance."""
    settings = get_settings()
    assert settings.llm_provider == "groq"
    assert settings.groq_model == "openai/gpt-oss-120b"
    assert settings.groq_api_key.startswith("gsk_")

    llm = get_chat_llm(temperature=0.1)
    res = await llm.ainvoke([HumanMessage(content="Return exactly: OK")])
    assert res is not None
    assert "OK" in res.content.upper()


@pytest.mark.asyncio
async def test_signal_scout_prompt_with_groq():
    """Verify Signal Scout JSON output generation via Groq."""
    llm = get_chat_llm(temperature=0.1)
    prompt = """You are the Signal Scout agent in FaultLens, an incident intelligence system.
Your job is to assess what telemetry signals are available for a service and determine the best analysis strategy.
Respond ONLY with a JSON object in this exact format:
{
  "environment_assessment": "brief description",
  "recommended_strategy": "rich | medium | thin",
  "reasoning": "1-2 sentences explaining why"
}"""

    input_data = "Signal summary:\nService: order-service\nMetrics: error rate 42%\nLogs: connection pool exhausted"
    res = await llm.ainvoke([
        SystemMessage(content=prompt),
        HumanMessage(content=input_data),
    ])

    match = re.search(r"\{.*\}", res.content, re.DOTALL)
    assert match is not None, f"Expected JSON in response: {res.content}"
    data = json.loads(match.group())
    assert "recommended_strategy" in data
    assert data["recommended_strategy"] in ["rich", "medium", "thin"]


@pytest.mark.asyncio
async def test_triage_classification_with_groq():
    """Verify Triage classification into failure taxonomy via Groq."""
    llm = get_chat_llm(temperature=0.0)
    prompt = """You are the Triage Agent in FaultLens.
Classify the incident into ONE of these failure types:
["DB_CONNECTION_POOL_EXHAUSTED", "DB_QUERY_TIMEOUT", "AI_RATE_LIMIT_EXCEEDED", "AI_MODEL_TIMEOUT"]

Respond ONLY with JSON:
{
  "failure_type": "FAILURE_TYPE_FROM_LIST",
  "team": "backend | infra | ml-platform",
  "reasoning": "one sentence"
}"""

    incident = "Logs indicate: FATAL: remaining connection slots are reserved for non-replication superuser connections. Active pool size: 10/10."
    res = await llm.ainvoke([
        SystemMessage(content=prompt),
        HumanMessage(content=incident),
    ])

    match = re.search(r"\{.*\}", res.content, re.DOTALL)
    assert match is not None, f"Expected JSON in response: {res.content}"
    data = json.loads(match.group())
    assert data.get("failure_type") == "DB_CONNECTION_POOL_EXHAUSTED"
    assert data.get("team") == "backend"


@pytest.mark.asyncio
async def test_rca_tool_calling_with_groq():
    """Verify autonomous tool-calling in RCA Investigator via Groq."""
    llm = get_chat_llm(temperature=0.1)
    tool_schemas = [
        {
            "type": "function",
            "function": {
                "name": "search_logs",
                "description": "Search recent logs for a service to find error traces.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "target_service_id": {"type": "string", "description": "Service ID"},
                        "keyword": {"type": "string", "description": "Keyword to search"},
                    },
                    "required": ["target_service_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_error_rate",
                "description": "Get error rate for a service.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "target_service_id": {"type": "string"},
                    },
                    "required": ["target_service_id"],
                },
            },
        },
    ]

    messages = [
        SystemMessage(content="You are an RCA investigator. You must call search_logs to investigate."),
        HumanMessage(content="Investigate errors on target_service_id: order-service"),
    ]

    res = await llm.ainvoke(messages, tools=tool_schemas)
    assert len(res.tool_calls) > 0, f"Expected tool call from model: {res}"
    tc = res.tool_calls[0]
    assert tc["name"] in ["search_logs", "get_error_rate"]
    assert "order-service" in str(tc["args"])

    # Multi-turn tool response test
    messages.append(res)
    tool_call_id = tc.get("id") or "call_123"
    messages.append(ToolMessage(
        tool_call_id=str(tool_call_id),
        content="Logs found: 45 connection timeout errors to postgres on port 5434"
    ))
    res2 = await llm.ainvoke(messages, tools=tool_schemas)
    assert res2 is not None


@pytest.mark.asyncio
async def test_reporter_markdown_generation_with_groq():
    """Verify Incident Reporter produces the required markdown sections via Groq."""
    llm = get_chat_llm(temperature=0.3)
    system_prompt = """Generate a structured Root Cause Analysis report with EXACTLY these headings:
## 🚨 What is Going Down
## 🔍 Root Cause & Causal Chain
## 📊 Telemetry Evidence (Logs, Metrics, Traces)
## 🛠 Recommended Remediation"""

    res = await llm.ainvoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content="Root cause: payment-service latency spiked to 4500ms causing gateway 504 timeouts."),
    ])

    report = res.content
    assert "What is Going Down" in report
    assert "Root Cause" in report
    assert "Telemetry Evidence" in report
    assert "Recommended Remediation" in report


if __name__ == "__main__":
    async def main():
        print("Running Groq agent tests...")
        await test_llm_factory()
        print("✓ test_llm_factory passed")
        await test_signal_scout_prompt_with_groq()
        print("✓ test_signal_scout_prompt_with_groq passed")
        await test_triage_classification_with_groq()
        print("✓ test_triage_classification_with_groq passed")
        await test_rca_tool_calling_with_groq()
        print("✓ test_rca_tool_calling_with_groq passed")
        await test_reporter_markdown_generation_with_groq()
        print("✓ test_reporter_markdown_generation_with_groq passed")
        print("\nAll Groq agent tests PASSED successfully!")

    asyncio.run(main())
