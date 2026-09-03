"""
Multi-modal signal fusion.

Combines anomaly scores from metrics, logs, and traces into a single
fused anomaly score using environment-aware weights.

Design: rule-based weighted fusion with confidence calibration.
  - Deterministic (good for demo reproducibility)
  - Degrades gracefully when signals are missing (thin environments)
  - Each signal type returns a score in [0, 1]
  - Weights adapt based on the detected environment type
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from ingestion.models import EnvironmentType

# ─── Fusion Weight Tables ─────────────────────────────────────────────────────
# Each row sums to 1.0. Missing signals get weight 0 and remaining weights rescale.

FUSION_WEIGHTS: dict[str, dict[str, float]] = {
    EnvironmentType.RICH.value: {
        "metrics": 0.40,
        "logs":    0.30,
        "traces":  0.30,
    },
    EnvironmentType.MEDIUM.value: {
        "metrics": 0.00,
        "logs":    0.45,
        "traces":  0.55,
    },
    EnvironmentType.THIN.value: {
        "metrics": 0.00,
        "logs":    1.00,
        "traces":  0.00,
    },
    EnvironmentType.UNKNOWN.value: {
        "metrics": 0.33,
        "logs":    0.34,
        "traces":  0.33,
    },
}

ANOMALY_THRESHOLD = 0.45  # fused score above this = incident trigger


@dataclass
class FusedScore:
    service_id:         str
    fused_score:        float           # 0.0 → 1.0
    is_anomalous:       bool
    weights_used:       dict[str, float]
    metric_score:       float = 0.0
    log_score:          float = 0.0
    trace_score:        float = 0.0
    missing_modalities: list[str] = field(default_factory=list)
    evidence_summary:   str = ""

    def to_dict(self) -> dict:
        return {
            "service_id": self.service_id,
            "fused_score": self.fused_score,
            "is_anomalous": self.is_anomalous,
            "weights_used": self.weights_used,
            "metric_score": self.metric_score,
            "log_score": self.log_score,
            "trace_score": self.trace_score,
            "missing_modalities": self.missing_modalities,
            "evidence_summary": self.evidence_summary,
        }


def fuse_scores(
    service_id: str,
    env_type: str,
    metric_score: float | None,
    log_score: float | None,
    trace_score: float | None,
) -> FusedScore:
    """
    Compute weighted fusion of available signal anomaly scores.

    If a signal is None (missing), its weight is redistributed
    proportionally to the available signals.
    """
    base_weights = dict(FUSION_WEIGHTS.get(env_type, FUSION_WEIGHTS[EnvironmentType.UNKNOWN.value]))

    scores: dict[str, float | None] = {
        "metrics": metric_score,
        "logs":    log_score,
        "traces":  trace_score,
    }

    # Zero out weights for missing signals
    effective_weights: dict[str, float] = {}
    missing: list[str] = []

    for signal, score in scores.items():
        if score is None:
            missing.append(signal)
            effective_weights[signal] = 0.0
        else:
            effective_weights[signal] = base_weights[signal]

    # Renormalise
    total_weight = sum(effective_weights.values())
    if total_weight > 0:
        effective_weights = {k: v / total_weight for k, v in effective_weights.items()}

    # Weighted sum
    fused = sum(
        effective_weights[sig] * (scores[sig] or 0.0)
        for sig in ["metrics", "logs", "traces"]
    )
    fused = min(1.0, max(0.0, fused))

    evidence_parts = []
    if metric_score is not None:
        evidence_parts.append(f"metrics={metric_score:.2f}(w={effective_weights['metrics']:.2f})")
    if log_score is not None:
        evidence_parts.append(f"logs={log_score:.2f}(w={effective_weights['logs']:.2f})")
    if trace_score is not None:
        evidence_parts.append(f"traces={trace_score:.2f}(w={effective_weights['traces']:.2f})")

    return FusedScore(
        service_id=service_id,
        fused_score=fused,
        is_anomalous=fused >= ANOMALY_THRESHOLD,
        weights_used=effective_weights,
        metric_score=metric_score or 0.0,
        log_score=log_score or 0.0,
        trace_score=trace_score or 0.0,
        missing_modalities=missing,
        evidence_summary=f"fused={fused:.3f} [{', '.join(evidence_parts)}] missing={missing}",
    )
