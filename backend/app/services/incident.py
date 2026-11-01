"""
FaultLens Backend — Rule-Based Incident Engine (Phase 13)

Takes active anomalies (from Phase 12) and applies a rule table to
produce Incident records.

Design (research-aligned)
──────────────────────────
Papers like GALA and RCAgent use a two-layer design:
  Layer 1: Statistical pre-computation (our Phase 12 Z-scores)
  Layer 2: Rule-based triage → creates structured incident records
  Layer 3: LLM explains the incident in natural language (Phase 17)

This module is Layer 2. It is entirely deterministic — no AI, no randomness.

Rule Table
───────────
Rules are evaluated in priority order. The first matching rule for a given
(service, anomaly_group) fires and creates/updates the incident.

  RULE                   CONDITION                               SEVERITY
  ─────────────────────────────────────────────────────────────────────────
  SERVICE_DOWN           error_rate anomaly, Z ≥ 8              critical
  HIGH_ERROR_RATE        error_rate anomaly, Z ≥ 3              high
  LATENCY_SPIKE_CRITICAL latency anomaly, Z ≥ 8                 critical
  LATENCY_SPIKE_HIGH     latency anomaly, Z ≥ 3                 high
  MULTI_SIGNAL           ≥ 2 anomalies on same service          high
  SINGLE_ANOMALY         any anomaly                            medium

Rules fire per service — one incident per service per scan.

Incident lifecycle:
  - If no active anomaly exists for a service → mark its incident resolved.
  - If an anomaly fires and incident already exists → update severity/description.
  - If anomaly fires and no incident exists → create one.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import NamedTuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.anomaly import Anomaly
from app.models.incident import Incident

logger = logging.getLogger(__name__)

# ── Metric name patterns ───────────────────────────────────────────────────────
# These match the metric names emitted by the OTel Demo (Astronomy Shop)

_ERROR_KEYWORDS    = ("error", "fail", "exception", "fault")
_LATENCY_KEYWORDS  = ("duration", "latency", "response_time", "rtt")


def _is_error_metric(metric_name: str) -> bool:
    mn = metric_name.lower()
    return any(k in mn for k in _ERROR_KEYWORDS)


def _is_latency_metric(metric_name: str) -> bool:
    mn = metric_name.lower()
    return any(k in mn for k in _LATENCY_KEYWORDS)


# ── Rule evaluation ────────────────────────────────────────────────────────────

@dataclass
class _RuleMatch:
    rule:        str
    severity:    str
    title:       str
    description: str


def evaluate_rules(
    service: str,
    anomalies: list[Anomaly],
) -> _RuleMatch | None:
    """
    Apply the rule table to a service's active anomalies.
    Returns the highest-priority matching rule, or None if no rules fire.

    Pure function — no DB access, fully testable.
    """
    if not anomalies:
        return None

    error_anomalies   = [a for a in anomalies if _is_error_metric(a.metric_name)]
    latency_anomalies = [a for a in anomalies if _is_latency_metric(a.metric_name)]

    # ── RULE: SERVICE_DOWN ────────────────────────────────────────────────
    for a in error_anomalies:
        if abs(a.z_score) >= 8.0:
            return _RuleMatch(
                rule     = "SERVICE_DOWN",
                severity = "critical",
                title    = f"{service}: service appears down — error rate critical",
                description=(
                    f"Service '{service}' has a critical error rate anomaly "
                    f"(Z={a.z_score:.1f}) on metric '{a.metric_name}'. "
                    f"Current value {a.current_value:.2f} vs baseline "
                    f"{a.baseline_mean:.2f}±{a.baseline_stddev:.2f}. "
                    f"Immediate investigation required."
                ),
            )

    # ── RULE: LATENCY_SPIKE_CRITICAL ──────────────────────────────────────
    for a in latency_anomalies:
        if abs(a.z_score) >= 8.0:
            return _RuleMatch(
                rule     = "LATENCY_SPIKE_CRITICAL",
                severity = "critical",
                title    = f"{service}: severe latency spike detected",
                description=(
                    f"Service '{service}' has a critical latency spike "
                    f"(Z={a.z_score:.1f}) on metric '{a.metric_name}'. "
                    f"Response time {a.current_value:.2f} vs baseline "
                    f"{a.baseline_mean:.2f}±{a.baseline_stddev:.2f}."
                ),
            )

    # ── RULE: HIGH_ERROR_RATE ─────────────────────────────────────────────
    for a in error_anomalies:
        if abs(a.z_score) >= 3.0:
            return _RuleMatch(
                rule     = "HIGH_ERROR_RATE",
                severity = "high",
                title    = f"{service}: elevated error rate",
                description=(
                    f"Service '{service}' has an elevated error rate "
                    f"(Z={a.z_score:.1f}) on '{a.metric_name}'. "
                    f"Current {a.current_value:.2f}, baseline {a.baseline_mean:.2f}."
                ),
            )

    # ── RULE: LATENCY_SPIKE_HIGH ──────────────────────────────────────────
    for a in latency_anomalies:
        if abs(a.z_score) >= 3.0:
            return _RuleMatch(
                rule     = "LATENCY_SPIKE_HIGH",
                severity = "high",
                title    = f"{service}: latency spike",
                description=(
                    f"Service '{service}' has a latency spike "
                    f"(Z={a.z_score:.1f}) on '{a.metric_name}'."
                ),
            )

    # ── RULE: MULTI_SIGNAL ────────────────────────────────────────────────
    if len(anomalies) >= 2:
        metric_names = ", ".join(a.metric_name for a in anomalies[:3])
        return _RuleMatch(
            rule     = "MULTI_SIGNAL",
            severity = "high",
            title    = f"{service}: multiple metric anomalies",
            description=(
                f"Service '{service}' has {len(anomalies)} simultaneous anomalies: "
                f"{metric_names}."
            ),
        )

    # ── RULE: SINGLE_ANOMALY ──────────────────────────────────────────────
    a = anomalies[0]
    return _RuleMatch(
        rule     = "SINGLE_ANOMALY",
        severity = "medium",
        title    = f"{service}: metric anomaly on {a.metric_name}",
        description = a.description or f"{service}: {a.metric_name} anomaly (Z={a.z_score:.1f}).",
    )


# ── DB operations ──────────────────────────────────────────────────────────────

async def _get_open_incidents_by_service(
    db: AsyncSession,
) -> dict[str, Incident]:
    """Return {service_name: Incident} for all currently open incidents."""
    result = await db.execute(
        select(Incident).where(Incident.status == "open")
    )
    incidents: dict[str, Incident] = {}
    for inc in result.scalars().all():
        # A single-service incident — use first affected service as key
        svcs = inc.affected_services or []
        if svcs:
            incidents[svcs[0]] = inc
    return incidents


async def _get_active_anomalies_by_service(
    db: AsyncSession,
) -> dict[str, list[Anomaly]]:
    """Return {service_name: [Anomaly, ...]} for all active anomalies."""
    result = await db.execute(
        select(Anomaly).where(Anomaly.is_active == True)  # noqa: E712
    )
    by_service: dict[str, list[Anomaly]] = {}
    for a in result.scalars().all():
        by_service.setdefault(a.service_name, []).append(a)
    return by_service


# ── Main run ───────────────────────────────────────────────────────────────────

async def run_incident_engine(db: AsyncSession) -> dict:
    """
    Run the incident engine over all active anomalies.

    Steps:
      1. Load all active anomalies grouped by service.
      2. Load all open incidents grouped by service.
      3. For each service with active anomalies:
           a. Evaluate rules → get highest-priority match.
           b. Create new incident or update existing one.
      4. For services with open incidents but NO active anomalies:
           → resolve the incident.

    Returns a summary dict.
    """
    now_ns = time.time_ns()

    by_service   = await _get_active_anomalies_by_service(db)
    open_incs    = await _get_open_incidents_by_service(db)

    created  = 0
    updated  = 0
    resolved = 0
    changes: list[str] = []   # human-readable, for the pipeline log

    # ── Services with anomalies ────────────────────────────────────────────
    for service, anomalies in by_service.items():
        match = evaluate_rules(service, anomalies)
        if match is None:
            continue

        anomaly_ids = [a.id for a in anomalies]

        if service in open_incs:
            # Update existing incident
            inc = open_incs[service]
            if inc.severity != match.severity:
                changes.append(f"↑ {service}: {inc.severity} → {match.severity} ({match.rule})")
            inc.severity          = match.severity
            inc.title             = match.title
            inc.description       = match.description
            inc.anomaly_ids       = anomaly_ids
            inc.triggered_by_rule = match.rule
            db.add(inc)
            updated += 1
            logger.debug("Updated incident for %s: %s [%s]", service, match.title, match.severity)
        else:
            # Create new incident
            inc = Incident(
                title             = match.title,
                severity          = match.severity,
                status            = "open",
                affected_services = [service],
                anomaly_ids       = anomaly_ids,
                triggered_by_rule = match.rule,
                description       = match.description,
                created_at_unix_nano = now_ns,
            )
            db.add(inc)
            created += 1
            changes.append(f"+ NEW [{match.severity}] {match.title}")
            logger.debug("Created incident for %s: %s [%s]", service, match.title, match.severity)

    # ── Services with open incidents but no anomalies → resolve ───────────
    for service, inc in open_incs.items():
        if service not in by_service:
            inc.status                = "resolved"
            inc.resolved_at_unix_nano = now_ns
            db.add(inc)
            resolved += 1
            changes.append(f"✓ RESOLVED {inc.title}")
            logger.debug("Resolved incident for %s (no active anomalies)", service)

    return {
        "incidents_created":  created,
        "incidents_updated":  updated,
        "incidents_resolved": resolved,
        "open_count":         len(by_service),
        "changes":            changes,
    }
