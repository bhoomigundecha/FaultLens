"""
Anomaly detection algorithms.

Two complementary approaches:
  1. Z-Score (per-metric, online, O(1)) — fast, good for univariate spikes
  2. Isolation Forest (multivariate, batch) — detects correlated anomalies
     across multiple metrics simultaneously

Both return an AnomalyResult that includes a score, flag, and explanation.
"""

from __future__ import annotations

import math
import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from sklearn.ensemble import IsolationForest

from config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class AnomalyResult:
    metric_name: str
    service_id:  str
    value:       float
    score:       float          # 0.0 (normal) → 1.0 (definitely anomalous)
    is_anomaly:  bool
    z_score:     float = 0.0
    baseline_mean: float = 0.0
    baseline_stddev: float = 0.0
    evidence:    str = ""


@dataclass
class MultivariateAnomalyResult:
    service_id:     str
    score:          float       # 0.0 → 1.0
    is_anomaly:     bool
    anomalous_dims: list[str]   # which metric dimensions drove the detection
    evidence:       str = ""


# ─── Z-Score (Welford's online algorithm) ────────────────────────────────────

class OnlineZScore:
    """
    Running mean and variance using Welford's algorithm.
    O(1) per update, no history stored.
    """

    def __init__(self, threshold: float | None = None) -> None:
        self.n = 0
        self.mean = 0.0
        self._M2 = 0.0
        self.threshold = threshold or settings.zscore_threshold

    def update(self, value: float) -> None:
        self.n += 1
        delta = value - self.mean
        self.mean += delta / self.n
        delta2 = value - self.mean
        self._M2 += delta * delta2

    @property
    def variance(self) -> float:
        return self._M2 / (self.n - 1) if self.n > 1 else 0.0

    @property
    def stddev(self) -> float:
        return math.sqrt(self.variance)

    def score(self, value: float) -> float:
        """Return z-score magnitude. > threshold = anomaly."""
        if self.stddev < 1e-10:
            return 0.0
        return abs((value - self.mean) / self.stddev)


# ─── Per-service Z-Score state registry ──────────────────────────────────────

_zscore_registry: dict[str, dict[str, OnlineZScore]] = {}


def get_zscore_tracker(service_id: str, metric_name: str) -> OnlineZScore:
    """Get or create a per-(service, metric) Z-score tracker."""
    _zscore_registry.setdefault(service_id, {})
    _zscore_registry[service_id].setdefault(metric_name, OnlineZScore())
    return _zscore_registry[service_id][metric_name]


def run_zscore(
    service_id: str,
    metric_name: str,
    values: list[float],
) -> list[AnomalyResult]:
    """
    Run Z-score detection on a list of values for a single metric.
    Updates the running tracker AND returns an AnomalyResult per value.
    """
    tracker = get_zscore_tracker(service_id, metric_name)
    results: list[AnomalyResult] = []

    for v in values:
        z = tracker.score(v)
        is_anomaly = z > tracker.threshold
        score = min(1.0, z / (tracker.threshold * 2)) if tracker.threshold > 0 else 0.0

        results.append(AnomalyResult(
            metric_name=metric_name,
            service_id=service_id,
            value=v,
            score=score,
            is_anomaly=is_anomaly,
            z_score=z,
            baseline_mean=tracker.mean,
            baseline_stddev=tracker.stddev,
            evidence=(
                f"value={v:.2f} is {z:.1f}σ from mean={tracker.mean:.2f} "
                f"(threshold={tracker.threshold}σ)"
                if is_anomaly else ""
            ),
        ))
        tracker.update(v)  # update AFTER scoring so we score against history

    return results


# ─── Isolation Forest (multivariate) ─────────────────────────────────────────

# Per-service Isolation Forest models (retrained periodically)
_if_models: dict[str, IsolationForest] = {}
_if_training_data: dict[str, list[list[float]]] = {}


def update_isolation_forest(
    service_id: str,
    feature_vector: list[float],
) -> None:
    """Accumulate feature vectors for periodic retraining."""
    _if_training_data.setdefault(service_id, []).append(feature_vector)
    # Retrain every N samples
    data = _if_training_data[service_id]
    if len(data) >= settings.min_isolation_forest_samples and len(data) % 50 == 0:
        logger.info(f"Retraining Isolation Forest for {service_id} ({len(data)} samples)")
        model = IsolationForest(
            contamination=settings.isolation_forest_contamination,
            random_state=42,
            n_estimators=100,
        )
        model.fit(np.array(data))
        _if_models[service_id] = model


def run_isolation_forest(
    service_id: str,
    metric_names: list[str],
    feature_matrix: list[list[float]],
) -> MultivariateAnomalyResult | None:
    """
    Score the latest feature vector against the trained model.
    Returns None if not enough data to score.
    feature_matrix: list of [value per metric] windows (rows=time, cols=metrics).
    """
    if not feature_matrix:
        return None

    # Accumulate for retraining
    for vec in feature_matrix:
        update_isolation_forest(service_id, vec)

    model = _if_models.get(service_id)
    if model is None:
        return None  # not enough data yet

    latest = np.array([feature_matrix[-1]])  # score the most recent window
    prediction = model.predict(latest)[0]    # -1 = anomaly, 1 = normal
    decision_score = model.decision_function(latest)[0]  # lower = more anomalous

    # Normalise decision score to [0, 1] anomaly score
    raw_scores = model.decision_function(np.array(feature_matrix))
    min_s, max_s = raw_scores.min(), raw_scores.max()
    if max_s - min_s < 1e-10:
        norm_score = 0.0
    else:
        # Invert: lower decision_function → higher anomaly score
        norm_score = 1.0 - (decision_score - min_s) / (max_s - min_s)

    is_anomaly = prediction == -1

    # Identify which dimensions contributed most (feature importance approximation)
    anomalous_dims: list[str] = []
    if is_anomaly and metric_names and len(feature_matrix) > 1:
        latest_vec = np.array(feature_matrix[-1])
        prev_vecs = np.array(feature_matrix[:-1])
        deviations = np.abs(latest_vec - prev_vecs.mean(axis=0))
        top_idx = np.argsort(deviations)[::-1][:3]
        anomalous_dims = [metric_names[i] for i in top_idx if i < len(metric_names)]

    return MultivariateAnomalyResult(
        service_id=service_id,
        score=float(norm_score),
        is_anomaly=is_anomaly,
        anomalous_dims=anomalous_dims,
        evidence=(
            f"Isolation Forest flagged latest window as anomalous "
            f"(score={norm_score:.3f}, dims={anomalous_dims})"
            if is_anomaly else ""
        ),
    )
