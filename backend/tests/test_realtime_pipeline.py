"""
FaultLens Backend — Real-time pipeline tests

  - evaluate_red: pure RED decision logic (error rate, p95 latency, silence)
  - scheduler._log_report: renders quiet + active reports without crashing
  - run_retention / run_cycle: against a live PostgreSQL (skipped if unreachable)
"""
from __future__ import annotations

import time

import pytest

from app.services.anomaly import (
    RedWindow,
    evaluate_red,
    RED_MIN_BASELINE_BUCKETS,
    RED_MIN_REQUESTS,
)


def _baseline(n=15, requests=20, errors=0, p95=30.0, jitter=3.0):
    """n one-minute buckets of steady, healthy traffic."""
    return [RedWindow(requests, errors, p95 + (jitter if i % 2 else -jitter)) for i in range(n)]


def _metrics(results):
    return {r.metric_name for r in results}


# ── Healthy traffic never fires ───────────────────────────────────────────────

def test_healthy_service_no_anomaly():
    assert evaluate_red("cart", RedWindow(40, 0, 31.0), _baseline()) == []


def test_small_error_blip_does_not_fire():
    # 2/40 = 5 % errors — below the 10 % floor even though z would be high
    assert "span.error_rate" not in _metrics(evaluate_red("cart", RedWindow(40, 2, 31.0), _baseline()))


def test_too_few_requests_not_judged():
    cur = RedWindow(RED_MIN_REQUESTS - 1, RED_MIN_REQUESTS - 1, 5000.0)
    assert evaluate_red("payment", cur, _baseline()) == []


# ── Error rate ────────────────────────────────────────────────────────────────

def test_error_spike_fires():
    res = evaluate_red("payment", RedWindow(40, 20, 31.0), _baseline())
    err = [r for r in res if r.metric_name == "span.error_rate"]
    assert len(err) == 1
    assert err[0].current_value == 0.5
    assert err[0].z_score >= 8          # → SERVICE_DOWN / critical rule
    assert "20/40" in err[0].description


def test_error_rate_relative_to_noisy_baseline():
    # Service normally runs at 20 % errors; 25 % now is not an incident
    base = [RedWindow(20, 4, 30.0) for _ in range(15)]
    assert "span.error_rate" not in _metrics(evaluate_red("svc", RedWindow(40, 10, 30.0), base))


def test_learning_phase_never_alerts():
    """< RED_MIN_BASELINE_BUCKETS minutes of history → no alerts, however bad it looks.
    Mirrors a real cold start: containers just booted, 77 % errors, 60 s latency."""
    short = _baseline(n=RED_MIN_BASELINE_BUCKETS - 1)
    assert evaluate_red("frontend-proxy", RedWindow(13, 10, 65_000.0), short) == []
    assert evaluate_red("frontend-proxy", RedWindow(13, 10, 65_000.0), []) == []


def test_error_baseline_robust_to_one_bad_minute():
    """A single warm-up minute at 80 % errors must not hide a later 40 % outage."""
    base = _baseline() + [RedWindow(20, 16, 30.0)]
    assert "span.error_rate" in _metrics(evaluate_red("svc", RedWindow(40, 16, 31.0), base))


# ── Latency ───────────────────────────────────────────────────────────────────

def test_latency_spike_fires():
    res = evaluate_red("shipping", RedWindow(40, 0, 5000.0), _baseline())
    lat = [r for r in res if r.metric_name == "span.latency_p95"]
    assert len(lat) == 1 and lat[0].current_value == 5000.0
    assert "x)" in lat[0].description   # shows the multiplier


def test_latency_needs_absolute_and_relative_change():
    # 30 ms → 70 ms is 2.3x but only +40 ms: not worth an incident
    assert "span.latency_p95" not in _metrics(evaluate_red("svc", RedWindow(40, 0, 70.0), _baseline()))
    # 400 ms → 600 ms is +200 ms but only 1.5x: also not
    base = _baseline(p95=400.0, jitter=20.0)
    assert "span.latency_p95" not in _metrics(evaluate_red("svc", RedWindow(40, 0, 600.0), base))


def test_latency_baseline_robust_to_warmup_spike():
    """Two 60 s warm-up minutes don't raise the latency baseline."""
    base = _baseline() + [RedWindow(20, 0, 60_000.0), RedWindow(20, 0, 60_000.0)]
    assert "span.latency_p95" in _metrics(evaluate_red("svc", RedWindow(40, 0, 3000.0), base))


# ── Silence ───────────────────────────────────────────────────────────────────

def test_busy_service_going_silent_fires():
    res = evaluate_red("payment", None, _baseline(requests=10))
    assert _metrics(res) == {"span.service_silent"}
    assert res[0].direction == "drop"


def test_low_traffic_service_silence_is_normal():
    # ~1 request/min → 2 expected in the window: a quiet 2 minutes is not an outage
    assert evaluate_red("email", None, _baseline(requests=1)) == []


def test_silence_needs_baseline():
    assert evaluate_red("svc", None, _baseline(n=RED_MIN_BASELINE_BUCKETS - 1)) == []


# ── Log rendering ─────────────────────────────────────────────────────────────

def _report(active: bool) -> dict:
    an = [{"service_name": "payment", "metric_name": "span.error_rate", "z_score": 25.0,
           "description": "payment: error rate 50% …"}] if active else []
    return {
        "cycle": 7, "services": 11, "duration_ms": 42.0,
        "stage_ms": {"detect": 10, "incidents": 5, "rca": 5, "ai": 0},
        "anomalies": {"anomalies": an, "newly_opened": ["payment / span.error_rate"] if active else [],
                      "resolved": []},
        "incidents": {"open_count": 1 if active else 0, "incidents_created": int(active),
                      "incidents_updated": 0, "incidents_resolved": 0,
                      "changes": ["+ NEW [critical] payment: service appears down"] if active else []},
        "rca": [{"incident_id": 1, "root_cause_service": "payment", "confidence": 1.0,
                 "propagation_path": ["payment", "checkout", "frontend"]}] if active else [],
        "ai": [],
    }


@pytest.mark.parametrize("active", [False, True])
def test_log_report_renders(active, caplog):
    from app.services.scheduler import _log_report
    with caplog.at_level("INFO", logger="faultlens.pipeline"):
        _log_report(_report(active))
    text = caplog.text
    if active:
        assert "PIPELINE #7" in text and "root cause → payment" in text and "NEW" in text
    else:
        assert "all healthy" in text


# ── Live DB: retention + full cycle ───────────────────────────────────────────

async def _db_ready() -> bool:
    """(Re)create the engine on THIS test's event loop — pytest-asyncio gives each test its own."""
    from app.core.config import get_settings
    if not get_settings().database_url:
        return False
    import app.db.session as s
    s._async_engine = None
    s.AsyncSessionLocal = None
    try:
        await s.init_db()
    except Exception:
        return False
    return await s.check_db()


@pytest.mark.asyncio
async def test_retention_deletes_only_old_rows():
    if not await _db_ready():
        pytest.skip("PostgreSQL not reachable")
    from sqlalchemy import delete, func, insert, select
    import app.db.session as s
    from app.models.telemetry import Span
    from app.services.scheduler import run_retention

    now = time.time_ns()
    old = now - 3 * 3600 * 1_000_000_000
    rows = [dict(trace_id="f" * 32, span_id=f"{i:016x}", name="retention-test", kind=2,
                 start_time_unix_nano=t, end_time_unix_nano=t + 1, service_name="retention-test")
            for i, t in enumerate([old, old, now])]
    async with s.AsyncSessionLocal() as db, db.begin():
        await db.execute(insert(Span), rows)

    try:
        await run_retention()
        async with s.AsyncSessionLocal() as db:
            left = (await db.execute(select(func.count()).select_from(Span)
                                     .where(Span.service_name == "retention-test"))).scalar()
        assert left == 1
    finally:
        async with s.AsyncSessionLocal() as db, db.begin():
            await db.execute(delete(Span).where(Span.service_name == "retention-test"))


@pytest.mark.asyncio
async def test_run_cycle_end_to_end(monkeypatch):
    """Inject a payment outage directly into spans → one cycle → incident + RCA + AI row."""
    if not await _db_ready():
        pytest.skip("PostgreSQL not reachable")
    from sqlalchemy import delete, insert, select, text
    import app.db.session as s
    from app.models.telemetry import Span
    from app.models.incident import Incident
    from app.models.ai_explanation import AIExplanation
    from app.services import scheduler

    async with s.AsyncSessionLocal() as db, db.begin():
        await db.execute(text("TRUNCATE spans, anomalies, incidents, root_cause_analyses, "
                              "ai_explanations, service_dependencies RESTART IDENTITY"))

    svc = "e2e-payment"
    now = time.time_ns()
    rows, i = [], 0
    for minute in range(15, 2, -1):                  # healthy history
        for k in range(10):
            t = now - minute * 60 * 1_000_000_000 + k * 1_000_000_000
            rows.append(dict(trace_id=f"{i:032x}", span_id=f"{i:016x}", name="Charge", kind=2,
                             status_code=0, start_time_unix_nano=t,
                             end_time_unix_nano=t + 30_000_000, service_name=svc)); i += 1
    for k in range(20):                               # outage now
        t = now - k * 3 * 1_000_000_000
        rows.append(dict(trace_id=f"{i:032x}", span_id=f"{i:016x}", name="Charge", kind=2,
                         status_code=2, start_time_unix_nano=t,
                         end_time_unix_nano=t + 30_000_000, service_name=svc)); i += 1
    async with s.AsyncSessionLocal() as db, db.begin():
        await db.execute(insert(Span), rows)

    async def fake_ai(evidence):
        return {"root_cause_service": svc, "fault_type": "error_spike", "confidence_label": "high",
                "propagation_path": [svc], "human_summary": "test", "remediation_steps": [],
                "_ai_available": True}
    monkeypatch.setattr("app.services.ai.generate_explanation", fake_ai)

    try:
        report = await scheduler.run_cycle(1, explain=True)
        assert any(a["service_name"] == svc for a in report["anomalies"]["anomalies"])
        assert report["incidents"]["incidents_created"] >= 1
        assert any(r["root_cause_service"] == svc for r in report["rca"])
        assert len(report["ai"]) >= 1

        # second cycle: incident stays open and is NOT re-explained
        report2 = await scheduler.run_cycle(2, explain=True)
        assert report2["incidents"]["incidents_created"] == 0
        assert report2["ai"] == []

        async with s.AsyncSessionLocal() as db:
            assert (await db.execute(select(Incident).where(Incident.status == "open"))).scalars().all()
            assert (await db.execute(select(AIExplanation))).scalars().all()
    finally:
        async with s.AsyncSessionLocal() as db, db.begin():
            await db.execute(delete(Span).where(Span.service_name == svc))
            await db.execute(text("TRUNCATE anomalies, incidents, root_cause_analyses, "
                                  "ai_explanations RESTART IDENTITY"))


# ── AI failures are not stored, and pause further calls ──────────────────────

@pytest.mark.asyncio
async def test_ai_failure_not_persisted_and_paused(monkeypatch):
    if not await _db_ready():
        pytest.skip("PostgreSQL not reachable")
    from sqlalchemy import select, text
    import app.db.session as s
    from app.models.incident import Incident
    from app.models.ai_explanation import AIExplanation
    from app.services import scheduler

    async with s.AsyncSessionLocal() as db, db.begin():
        await db.execute(text("TRUNCATE incidents, ai_explanations RESTART IDENTITY"))
        db.add(Incident(title="t", severity="high", status="open", affected_services=["x"],
                        anomaly_ids=[], triggered_by_rule="HIGH_ERROR_RATE", description="",
                        created_at_unix_nano=time.time_ns()))

    calls = []
    async def failing_ai(evidence):
        calls.append(1)
        return {"human_summary": "AI explanation generation failed.", "_ai_available": False}
    monkeypatch.setattr("app.services.ai.generate_explanation", failing_ai)
    monkeypatch.setattr(scheduler, "_ai_paused_until", 0.0)

    try:
        async with s.AsyncSessionLocal() as db:
            out = await scheduler._explain_new_incidents(db)
            await db.commit()
            assert out and out[0]["failed"]
            assert (await db.execute(select(AIExplanation))).scalars().all() == []
            # paused: a second call within AI_RETRY_AFTER_S makes no Groq request
            assert await scheduler._explain_new_incidents(db) == []
        assert len(calls) == 1
    finally:
        async with s.AsyncSessionLocal() as db, db.begin():
            await db.execute(text("TRUNCATE incidents, ai_explanations RESTART IDENTITY"))
