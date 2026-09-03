"""
Log clustering via DRAIN3 + semantic embeddings.

Pipeline per log record:
  1. DRAIN3 extracts a template (e.g. "DB timeout after <*> seconds")
     — this converts variable noise into stable cluster IDs
  2. Template frequency vectors are built per sliding window
     → anomaly detection on frequency shifts
  3. Ollama nomic-embed-text generates 768-dim embeddings
     → stored in Elasticsearch for KNN similarity search

This module is intentionally stateless at the HTTP layer:
all state lives in the TemplateMiner object (DRAIN3) and in Elasticsearch.
"""

from __future__ import annotations

import logging
from collections import Counter
from dataclasses import dataclass
from typing import Any

from drain3 import TemplateMiner
from drain3.template_miner_config import TemplateMinerConfig

from config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# ─── DRAIN3 setup ─────────────────────────────────────────────────────────────

def _make_drain3_config() -> TemplateMinerConfig:
    cfg = TemplateMinerConfig()
    cfg.load_defaults()
    cfg.drain_sim_th = 0.4          # similarity threshold (lower = more clusters)
    cfg.drain_depth = 4             # parse tree depth
    cfg.drain_max_children = 100    # max children per internal node
    cfg.parametrize_numeric_tokens = True
    return cfg


# One global TemplateMiner — DRAIN3 is designed to be shared across all logs
_miner: TemplateMiner | None = None


def get_miner() -> TemplateMiner:
    global _miner
    if _miner is None:
        _miner = TemplateMiner(config=_make_drain3_config())
    return _miner


@dataclass
class ParsedLog:
    original:    str
    template:    str
    template_id: str
    cluster_size: int
    variables:   list[str]   # the wildcarded parts


def parse_log(body: str) -> ParsedLog:
    """Run DRAIN3 on a single log line and return the extracted template."""
    miner = get_miner()
    result = miner.add_log_message(body)
    if result is None:
        return ParsedLog(
            original=body,
            template=body,
            template_id="unknown",
            cluster_size=1,
            variables=[],
        )
    cluster = result["cluster"]
    return ParsedLog(
        original=body,
        template=cluster.get_template(),
        template_id=str(cluster.cluster_id),
        cluster_size=cluster.size,
        variables=result.get("parameters", []),
    )


def parse_logs_batch(bodies: list[str]) -> list[ParsedLog]:
    return [parse_log(b) for b in bodies]


# ─── Template frequency anomaly detection ────────────────────────────────────

@dataclass
class LogAnomalyResult:
    service_id:   str
    template_id:  str
    template:     str
    count:        int
    score:        float       # 0.0 → 1.0
    is_anomaly:   bool
    reason:       str


def detect_log_anomalies(
    service_id: str,
    parsed_logs: list[ParsedLog],
    error_threshold_pct: float = 0.20,  # >20% error templates = anomaly
) -> list[LogAnomalyResult]:
    """
    Simple frequency-based anomaly detection on log templates.

    Strategy:
      - Count occurrences of each template in the window
      - Flag any template that looks error-like (ERROR/TIMEOUT/FAIL) and
        appears in >N% of all logs in the window
    """
    if not parsed_logs:
        return []

    total = len(parsed_logs)
    freq = Counter(p.template_id for p in parsed_logs)
    template_map = {p.template_id: p.template for p in parsed_logs}
    results: list[LogAnomalyResult] = []

    error_keywords = {"error", "exception", "timeout", "fail", "fatal", "critical", "refused", "429", "500", "503"}

    for template_id, count in freq.items():
        template = template_map[template_id].lower()
        is_error_template = any(kw in template for kw in error_keywords)
        pct = count / total
        score = min(1.0, pct * 5) if is_error_template else 0.0
        is_anomaly = is_error_template and pct >= error_threshold_pct

        if is_anomaly:
            results.append(LogAnomalyResult(
                service_id=service_id,
                template_id=template_id,
                template=template_map[template_id],
                count=count,
                score=score,
                is_anomaly=True,
                reason=f"Error template '{template_map[template_id]}' appeared {count}x ({pct:.0%} of window)",
            ))

    return results


# ─── Embeddings via Ollama ────────────────────────────────────────────────────

async def embed_text(text: str) -> list[float] | None:
    """
    Call Ollama nomic-embed-text to get a 768-dim embedding.
    Returns None on failure (embedding is optional, not critical path).
    """
    import httpx

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{settings.ollama_base_url}/api/embeddings",
                json={"model": settings.ollama_embed_model, "prompt": text},
            )
            resp.raise_for_status()
            return resp.json().get("embedding")
    except Exception as e:
        logger.warning(f"Embedding failed: {e}")
        return None


async def embed_logs_batch(texts: list[str]) -> list[list[float] | None]:
    """Embed multiple log templates (for batch ES indexing)."""
    import asyncio
    tasks = [embed_text(t) for t in texts]
    return await asyncio.gather(*tasks)
