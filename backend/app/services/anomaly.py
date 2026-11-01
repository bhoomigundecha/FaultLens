"""
FaultLens Backend — Statistical Anomaly Detection (Phase 12)

Implements the Z-score anomaly detection engine described in the research
literature (GALA, RCAgent, TrioXpert).

Design (research-aligned)
──────────────────────────
The LLM is NOT the anomaly detector. This module does the statistical work:

  1. For each (service_name, metric_name) pair, query the last BASELINE_MINUTES
     of metric_points to establish a baseline (mean, stddev).
  2. Compute the mean of the most recent CURRENT_MINUTES window.
  3. Z-score = (current_mean - baseline_mean) / baseline_stddev
  4. If |z_score| >= THRESHOLD → anomaly detected.

Results are written to the anomalies table:
  - New anomalies → INSERT with is_active=True
  - Existing active anomalies that are still firing → UPDATE z_score
  - Existing active anomalies that resolved → UPDATE is_active=False

Called by: POST /api/v1/anomalies/scan  (on-demand)
Consumed by: Phase 13 Incident Engine, Phase 17 AI context builder

Constants (tunable via environment later)
─────────────────────────────────────────
BASELINE_MINUTES  = 60   (1 hour of history for baseline)
CURRENT_MINUTES   = 5    (last 5 minutes = "current" window)
Z_THRESHOLD       = 3.0  (industry standard for 3-sigma rule)
MIN_SAMPLES       = 10   (skip metric if insufficient history)
"""
from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.telemetry import MetricPoint
from app.models.anomaly import Anomaly

logger = logging.getLogger(__name__)

# ── Tuneable constants ────────────────────────────────────────────────────────
# Lower values = faster detection (good for demo and early data).
# In production you'd set these via environment variables.
BASELINE_MINUTES  = 10    # was 60 — 10 min baseline is enough to detect sharp changes
CURRENT_MINUTES   = 1     # was 5  — compare last 1 min vs 10 min history
Z_THRESHOLD       = 2.5   # was 3.0 — slightly more sensitive
MIN_SAMPLES       = 5     # was 10 — need only 5 points (1 per 2 min)

_NS_PER_MINUTE = 60_000_000_000  # 60 seconds in nanoseconds

# An anomaly stays active until it has not fired for this long.
ANOMALY_COOLDOWN_SECONDS = 90


# ── Internal structures ───────────────────────────────────────────────────────

@dataclass
class AnomalyResult:
    service_name:    str
    metric_name:     str
    z_score:         float
    baseline_mean:   float
    baseline_stddev: float
    current_value:   float
    direction:       str       # "spike" or "drop"
    description:     str


# ── Pure statistics (no DB, fully testable) ───────────────────────────────────

def compute_z_score(
    baseline_values: list[float],
    current_mean: float,
) -> tuple[float, float, float] | None:
    """
    Compute Z-score of current_mean against the baseline distribution.

    Returns (z_score, mean, stddev) or None if insufficient data.

    Uses population stddev (not sample) for simplicity — consistent with
    how most AIOps papers describe their baseline computation.
    """
    n = len(baseline_values)
    if n < MIN_SAMPLES:
        return None

    mean = sum(baseline_values) / n
    variance = sum((x - mean) ** 2 for x in baseline_values) / n
    stddev = math.sqrt(variance)

    if stddev == 0:
        return None  # constant metric — no anomaly possible

    z = (current_mean - mean) / stddev
    return z, mean, stddev


def make_description(result: AnomalyResult) -> str:
    """Build a short human-readable description for the anomaly context."""
    return (
        f"{result.service_name}: {result.metric_name} has a "
        f"{result.direction} (Z={result.z_score:.1f}). "
        f"Current={result.current_value:.2f}, "
        f"baseline mean={result.baseline_mean:.2f} "
        f"±{result.baseline_stddev:.2f}."
    )


# ── DB queries ────────────────────────────────────────────────────────────────

async def _fetch_baseline(
    db: AsyncSession,
    service: str,
    metric: str,
    now_ns: int,
) -> list[float]:
    """Fetch metric values from the baseline window (last BASELINE_MINUTES)."""
    lo = now_ns - BASELINE_MINUTES * _NS_PER_MINUTE
    result = await db.execute(
        select(MetricPoint.value_double, MetricPoint.value_int)
        .where(
            MetricPoint.service_name == service,
            MetricPoint.metric_name == metric,
            MetricPoint.time_unix_nano >= lo,
            MetricPoint.time_unix_nano <= now_ns,
        )
        .order_by(MetricPoint.time_unix_nano)
    )
    rows = result.all()
    values = []
    for row in rows:
        v = row.value_double if row.value_double is not None else (
            float(row.value_int) if row.value_int is not None else None
        )
        if v is not None:
            values.append(v)
    return values


async def _fetch_current_mean(
    db: AsyncSession,
    service: str,
    metric: str,
    now_ns: int,
) -> float | None:
    """Compute mean of the most recent CURRENT_MINUTES window."""
    lo = now_ns - CURRENT_MINUTES * _NS_PER_MINUTE
    result = await db.execute(
        select(
            func.avg(MetricPoint.value_double).label("avg_double"),
            func.avg(MetricPoint.value_int).label("avg_int"),
        )
        .where(
            MetricPoint.service_name == service,
            MetricPoint.metric_name == metric,
            MetricPoint.time_unix_nano >= lo,
            MetricPoint.time_unix_nano <= now_ns,
        )
    )
    row = result.first()
    if row is None:
        return None
    avg = row.avg_double if row.avg_double is not None else (
        float(row.avg_int) if row.avg_int is not None else None
    )
    return avg


async def _get_candidate_pairs(
    db: AsyncSession,
    now_ns: int,
) -> list[tuple[str, str]]:
    """
    Find (service, metric) pairs worth z-scoring: allow-listed resource gauges
    with data in the baseline window (see METRIC_ALLOWLIST).
    """
    lo = now_ns - BASELINE_MINUTES * _NS_PER_MINUTE
    result = await db.execute(
        select(
            MetricPoint.service_name,
            MetricPoint.metric_name,
        )
        .where(
            MetricPoint.time_unix_nano >= lo,
            MetricPoint.metric_name.in_(METRIC_ALLOWLIST),
            MetricPoint.metric_type == "gauge",
        )
        .distinct()
    )
    ignored = _ignored_services()
    return [(row.service_name, row.metric_name) for row in result.all()
            if row.service_name and row.metric_name and row.service_name not in ignored]


# ── Upsert anomaly records ────────────────────────────────────────────────────

async def _upsert_anomalies(
    db: AsyncSession,
    detected: list[AnomalyResult],
    now_ns: int,
) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """
    Write detected anomalies to DB, update existing ones, resolve cleared ones.
    Returns (newly_opened, resolved) as lists of (service, metric).
    """
    opened: list[tuple[str, str]] = []
    resolved: list[tuple[str, str]] = []
    # Collect currently active anomalies
    active_result = await db.execute(
        select(Anomaly).where(Anomaly.is_active == True)  # noqa: E712
    )
    active: dict[tuple[str, str], Anomaly] = {
        (a.service_name, a.metric_name): a
        for a in active_result.scalars().all()
    }

    detected_keys = {(r.service_name, r.metric_name) for r in detected}

    # Insert new anomalies or update existing ones
    for r in detected:
        key = (r.service_name, r.metric_name)
        if key in active:
            # Update existing — z_score may have changed
            a = active[key]
            a.last_firing_unix_nano = now_ns
            a.z_score        = r.z_score
            a.current_value  = r.current_value
            a.direction      = r.direction
            a.description    = r.description
            db.add(a)
        else:
            # New anomaly
            db.add(Anomaly(
                service_name          = r.service_name,
                metric_name           = r.metric_name,
                z_score               = r.z_score,
                baseline_mean         = r.baseline_mean,
                baseline_stddev       = r.baseline_stddev,
                current_value         = r.current_value,
                direction             = r.direction,
                description           = r.description,
                detected_at_unix_nano = now_ns,
                last_firing_unix_nano = now_ns,
                is_active             = True,
            ))
            opened.append(key)

    # Resolve anomalies that stopped firing — but only after a quiet period.
    # Without this cool-down a fault that flickers (e.g. 50 % payment failures
    # with low traffic) would open and close incidents every scan.
    for key, a in active.items():
        if key not in detected_keys:
            last = a.last_firing_unix_nano or a.detected_at_unix_nano or 0
            if now_ns - last < ANOMALY_COOLDOWN_SECONDS * 1_000_000_000:
                continue
            a.is_active             = False
            a.resolved_at_unix_nano = now_ns
            db.add(a)
            resolved.append(key)
    return opened, resolved


# ── RED detectors on spans (Rate · Errors · Duration) ─────────────────────────
#
# This is the primary detector. Every scan, for every service, it compares the
# CURRENT window (last RED_CURRENT_SECONDS) against that service's OWN recent
# history (RED_BASELINE_MINUTES, split into 1-minute buckets):
#
#   error rate   current errors/requests  vs  baseline mean ± stddev
#   p95 latency  current p95 duration     vs  baseline median ± MAD
#   silence      zero requests now, although the baseline says we'd expect many
#
# Only SERVER / CONSUMER spans count — those are the requests a service handled.
# (Client spans describe calls it MADE; counting them would blame the caller.)
#
# Every detector needs BOTH a statistical signal (z-score) AND a minimum
# real-world change (e.g. +10 percentage points errors, 2x and +100 ms latency).
# The z-score alone fires on noise when the baseline is very stable.

RED_CURRENT_SECONDS      = 120   # "now" window
RED_BASELINE_MINUTES     = 15    # history before the current window
RED_MIN_REQUESTS         = 5     # need ≥5 requests now to judge error/latency
RED_MIN_BASELINE_BUCKETS = 5     # need ≥5 minutes of history for a baseline

ERR_MIN_RATE      = 0.10   # current error rate must be ≥10% …
ERR_MIN_DELTA     = 0.10   # … and ≥10 percentage points above baseline
ERR_STD_FLOOR     = 0.02   # spread floor so a perfectly clean baseline can't give z=∞

LAT_MIN_RATIO     = 2.0    # p95 must at least double …
LAT_MIN_DELTA_MS  = 100.0  # … and grow by ≥100 ms

# LEARNING PHASE: a service with < RED_MIN_BASELINE_BUCKETS minutes of history
# is never flagged. Containers are slow and error-prone while they warm up
# (first requests can take 60 s); without a baseline that looks like an outage.

SILENCE_MIN_EXPECTED = 6   # silence only counts if baseline predicts ≥6 requests in the window

RED_Z_MIN = 3.0            # statistical threshold for RED detectors
Z_CAP     = 50.0           # keep z-scores readable


@dataclass
class RedWindow:
    """Aggregated SERVER/CONSUMER spans of one service in one time window."""
    requests: int
    errors:   int
    p95_ms:   float | None

    @property
    def error_rate(self) -> float:
        return self.errors / self.requests if self.requests else 0.0


def _mean_std(values: list[float]) -> tuple[float, float]:
    n = len(values)
    mean = sum(values) / n
    return mean, math.sqrt(sum((v - mean) ** 2 for v in values) / n)


def _median(values: list[float]) -> float:
    v = sorted(values)
    mid = len(v) // 2
    return v[mid] if len(v) % 2 else (v[mid - 1] + v[mid]) / 2


def _cap(z: float) -> float:
    return round(max(-Z_CAP, min(Z_CAP, z)), 2)


def evaluate_red(
    service: str,
    current: RedWindow | None,
    baseline: list[RedWindow],
) -> list[AnomalyResult]:
    """
    Pure function: decide which RED anomalies fire for one service.
    `baseline` holds one RedWindow per minute of history (may be empty).
    """
    out: list[AnomalyResult] = []
    window_min = RED_CURRENT_SECONDS // 60
    if len(baseline) < RED_MIN_BASELINE_BUCKETS:
        return out                      # still learning what "normal" looks like

    # ── Silence ───────────────────────────────────────────────────────────
    per_min = sum(b.requests for b in baseline) / len(baseline)
    expected = per_min * RED_CURRENT_SECONDS / 60
    if (current is None or current.requests == 0) and expected >= SILENCE_MIN_EXPECTED:
        out.append(AnomalyResult(
            service_name=service, metric_name="span.service_silent",
            z_score=Z_CAP, baseline_mean=round(per_min, 2), baseline_stddev=0.0,
            current_value=0.0, direction="drop",
            description=(f"{service}: received 0 requests in the last {window_min} min "
                         f"(normally ~{expected:.0f}). Service may be down or unreachable."),
        ))
        return out

    if current is None or current.requests < RED_MIN_REQUESTS:
        return out

    # ── Error rate ────────────────────────────────────────────────────────
    cur_err = current.error_rate
    busy = [b.error_rate for b in baseline if b.requests]   # minutes that had traffic
    fires = False
    if len(busy) >= RED_MIN_BASELINE_BUCKETS:
        # median/MAD: one bad minute (e.g. a container restart) can't drag
        # the baseline up the way a mean/stddev would
        mean = _median(busy)
        std = max(_median([abs(b - mean) for b in busy]) * 1.4826, ERR_STD_FLOOR)
        z = (cur_err - mean) / std
        fires = z >= RED_Z_MIN and cur_err >= ERR_MIN_RATE and cur_err - mean >= ERR_MIN_DELTA
    if fires:
        out.append(AnomalyResult(
            service_name=service, metric_name="span.error_rate",
            z_score=_cap(z), baseline_mean=round(mean, 4), baseline_stddev=round(std, 4),
            current_value=round(cur_err, 4), direction="spike",
            description=(f"{service}: error rate {cur_err:.0%} in the last {window_min} min "
                         f"({current.errors}/{current.requests} requests failed); "
                         f"normal is {mean:.0%}."),
        ))

    # ── p95 latency ───────────────────────────────────────────────────────
    cur_p95 = current.p95_ms
    hist = [b.p95_ms for b in baseline if b.p95_ms is not None]
    if cur_p95 is not None:
        fires = False
        if len(hist) >= RED_MIN_BASELINE_BUCKETS:
            med = _median(hist)
            mad = _median([abs(h - med) for h in hist]) * 1.4826   # robust stddev
            spread = max(mad, 0.1 * med, 5.0)
            z = (cur_p95 - med) / spread
            fires = (z >= RED_Z_MIN and cur_p95 >= med * LAT_MIN_RATIO
                     and cur_p95 - med >= LAT_MIN_DELTA_MS)
        if fires:
            out.append(AnomalyResult(
                service_name=service, metric_name="span.latency_p95",
                z_score=_cap(z), baseline_mean=round(med, 2), baseline_stddev=round(spread, 2),
                current_value=round(cur_p95, 2), direction="spike",
                description=(f"{service}: p95 latency {cur_p95:,.0f} ms in the last {window_min} min; "
                             f"normal is ~{med:,.0f} ms ({cur_p95 / max(med, 0.001):.1f}x)."),
            ))
    return out


_RED_SQL_CURRENT = text("""
    SELECT service_name,
           count(*)                                     AS requests,
           count(*) FILTER (WHERE status_code = 2)      AS errors,
           percentile_cont(0.95) WITHIN GROUP
               (ORDER BY end_time_unix_nano - start_time_unix_nano) / 1e6 AS p95_ms
    FROM spans
    WHERE start_time_unix_nano >= :lo
      AND kind IN (2, 5)                -- SERVER, CONSUMER
      AND service_name IS NOT NULL
    GROUP BY service_name
""")

_RED_SQL_BASELINE = text("""
    SELECT service_name,
           (start_time_unix_nano - :lo) / 60000000000   AS bucket,
           count(*)                                     AS requests,
           count(*) FILTER (WHERE status_code = 2)      AS errors,
           percentile_cont(0.95) WITHIN GROUP
               (ORDER BY end_time_unix_nano - start_time_unix_nano) / 1e6 AS p95_ms
    FROM spans
    WHERE start_time_unix_nano >= :lo AND start_time_unix_nano < :hi
      AND kind IN (2, 5)
      AND service_name IS NOT NULL
    GROUP BY service_name, bucket
""")


def _ignored_services() -> set[str]:
    from app.core.config import get_settings
    raw = get_settings().detection_ignore_services or ""
    return {s.strip() for s in raw.split(",") if s.strip()}


# Services still in their learning phase after the last scan: {service: minutes of history}
learning: dict[str, int] = {}


async def _span_based_detections(
    db: AsyncSession,
    now_ns: int,
) -> list[AnomalyResult]:
    """Run the RED detectors for every service seen in the last RED_BASELINE_MINUTES."""
    cur_lo  = now_ns - RED_CURRENT_SECONDS * 1_000_000_000
    base_lo = cur_lo - RED_BASELINE_MINUTES * _NS_PER_MINUTE

    current: dict[str, RedWindow] = {}
    for row in (await db.execute(_RED_SQL_CURRENT, {"lo": cur_lo})).all():
        current[row.service_name] = RedWindow(int(row.requests), int(row.errors),
                                              float(row.p95_ms) if row.p95_ms is not None else None)

    # Fill empty minutes with zero-request buckets: a quiet minute is real
    # history (it lowers the expected rate), not missing data.
    buckets: dict[str, dict[int, RedWindow]] = {}
    for row in (await db.execute(_RED_SQL_BASELINE, {"lo": base_lo, "hi": cur_lo})).all():
        buckets.setdefault(row.service_name, {})[int(row.bucket)] = RedWindow(
            int(row.requests), int(row.errors),
            float(row.p95_ms) if row.p95_ms is not None else None)

    ignored = _ignored_services()
    detected: list[AnomalyResult] = []
    learning.clear()
    for svc in sorted((set(current) | set(buckets)) - ignored):
        svc_buckets = buckets.get(svc, {})
        if svc_buckets:
            first = min(svc_buckets)   # history starts when the service first appeared
            history = [svc_buckets.get(i, RedWindow(0, 0, None))
                       for i in range(first, RED_BASELINE_MINUTES)]
        else:
            history = []
        if len(history) < RED_MIN_BASELINE_BUCKETS:
            learning[svc] = len(history)
        for r in evaluate_red(svc, current.get(svc), history):
            detected.append(r)
            logger.debug("RED anomaly: %s", r.description)
    return detected


# ── Metric z-score engine: resource saturation only ──────────────────────────
# Runtime SDK metrics (GC, heap, thread pools …) are far too noisy to z-score
# blindly — across hundreds of series, 2.5σ fires by pure chance every scan.
# We only score container resource gauges, which explain faults like memory
# leaks that spans can't see.
METRIC_ALLOWLIST     = ("container.memory.percent", "container.cpu.utilization")
METRIC_Z_THRESHOLD   = 4.0
METRIC_MIN_REL_DELTA = 0.25   # value must move ≥25 % from baseline mean
METRIC_MIN_ABS_DELTA = 5.0    # … and ≥5 percentage points (both metrics are percentages)


# ── Main scan entry point ─────────────────────────────────────────────────────

async def run_anomaly_scan(db: AsyncSession) -> dict[str, Any]:
    """
    Run a full anomaly scan: Z-score engine + span-based instant detectors.

    Steps:
      1. Span-based detectors — fire immediately on error spikes / service silence.
      2. Metric Z-score engine — detect gradual drift once baseline is established.
      3. Merge results, upsert to anomalies table.

    Returns a summary dict suitable for the API response.
    """
    now_ns = time.time_ns()

    # ── Stage A: Instant span-based detection ─────────────────────────────
    span_detected = await _span_based_detections(db, now_ns)

    # ── Stage B: Metric Z-score detection ─────────────────────────────────
    pairs = await _get_candidate_pairs(db, now_ns)
    metric_detected: list[AnomalyResult] = []
    scanned = 0

    for service, metric in pairs:
        scanned += 1
        baseline_vals = await _fetch_baseline(db, service, metric, now_ns)
        current_mean  = await _fetch_current_mean(db, service, metric, now_ns)

        if current_mean is None:
            continue

        stats = compute_z_score(baseline_vals, current_mean)
        if stats is None:
            continue

        z, mean, stddev = stats
        delta = abs(current_mean - mean)
        if (abs(z) < METRIC_Z_THRESHOLD or delta < METRIC_MIN_ABS_DELTA
                or delta < METRIC_MIN_REL_DELTA * abs(mean)):
            continue

        direction = "spike" if z > 0 else "drop"
        r = AnomalyResult(
            service_name    = service,
            metric_name     = metric,
            z_score         = round(z, 3),
            baseline_mean   = round(mean, 4),
            baseline_stddev = round(stddev, 4),
            current_value   = round(current_mean, 4),
            direction       = direction,
            description     = "",
        )
        r.description = make_description(r)
        metric_detected.append(r)
        logger.debug("Metric anomaly: %s", r.description)

    # ── Merge: span detectors take precedence per (service, metric) key ───
    # (avoids double-counting the same service+metric pair)
    all_keys = {(r.service_name, r.metric_name) for r in span_detected}
    for r in metric_detected:
        if (r.service_name, r.metric_name) not in all_keys:
            span_detected.append(r)
            all_keys.add((r.service_name, r.metric_name))

    detected = span_detected
    opened, resolved = await _upsert_anomalies(db, detected, now_ns)

    logger.debug(
        "Anomaly scan: metric_pairs=%d span_anomalies=%d metric_anomalies=%d total=%d",
        scanned, len(span_detected), len(metric_detected), len(detected),
    )

    return {
        "scanned":            scanned,
        "anomalies_detected": len(detected),
        "learning":           dict(learning),
        "newly_opened":       [f"{svc} / {m}" for svc, m in opened],
        "resolved":           [f"{svc} / {m}" for svc, m in resolved],
        "anomalies": [
            {
                "service_name":    r.service_name,
                "metric_name":     r.metric_name,
                "z_score":         r.z_score,
                "direction":       r.direction,
                "current_value":   r.current_value,
                "baseline_mean":   r.baseline_mean,
                "baseline_stddev": r.baseline_stddev,
                "description":     r.description,
            }
            for r in detected
        ],
    }
