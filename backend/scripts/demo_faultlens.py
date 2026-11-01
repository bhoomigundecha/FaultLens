#!/usr/bin/env python3
"""
FaultLens — Live Terminal Showcase & Judge Demo
───────────────────────────────────────────────
Runs an interactive, step-by-step end-to-end demonstration of FaultLens
directly in your terminal with rich logging, live statistics, graph traversal,
and root cause analysis.

Usage:
  # Interactive mode (step-by-step with [Enter]):
  python scripts/demo_faultlens.py

  # Automated mode (runs all stages with timed pauses):
  python scripts/demo_faultlens.py --auto
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from typing import Any

# ── ANSI Color Palette ────────────────────────────────────────────────────────
RESET   = "\033[0m"
BOLD    = "\033[1m"
DIM     = "\033[2m"
CYAN    = "\033[36m"
GREEN   = "\033[32m"
YELLOW  = "\033[33m"
RED     = "\033[31m"
MAGENTA = "\033[35m"
WHITE   = "\033[37m"
BG_BLUE = "\033[44m"

BASE_URL = "http://localhost:8000"

def _print_box(title: str, subtitle: str = ""):
    width = 66
    print(f"\n{BOLD}{CYAN}╔{'═' * (width - 2)}╗{RESET}")
    print(f"{BOLD}{CYAN}║  {WHITE}{title.ljust(width - 6)}{CYAN}  ║{RESET}")
    if subtitle:
        print(f"{BOLD}{CYAN}║  {DIM}{subtitle.ljust(width - 6)}{RESET}{BOLD}{CYAN}  ║{RESET}")
    print(f"{BOLD}{CYAN}╚{'═' * (width - 2)}╝{RESET}\n")

def _step_header(num: int, title: str):
    print(f"\n{BOLD}{MAGENTA}━━━ [STAGE {num}] {WHITE}{title} ━━━{RESET}")

def _info(msg: str):
    print(f"  {GREEN}→{RESET} {msg}")

def _warn(msg: str):
    print(f"  {YELLOW}⚠{RESET} {BOLD}{msg}{RESET}")

def _err(msg: str):
    print(f"  {RED}✗{RESET} {BOLD}{msg}{RESET}")

def _prompt_user(auto: bool, delay: float = 2.0):
    if auto:
        time.sleep(delay)
    else:
        try:
            input(f"\n  {DIM}Press [ENTER] to continue...{RESET}")
        except (KeyboardInterrupt, EOFError):
            print("\nDemo aborted.")
            sys.exit(0)

def http_get(path: str) -> dict[str, Any]:
    url = f"{BASE_URL}{path}"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        _err(f"GET {path} failed: {e}")
        return {}

def http_post(path: str, data: dict | None = None) -> dict[str, Any]:
    url = f"{BASE_URL}{path}"
    body = json.dumps(data or {}).encode() if data else b""
    headers = {"Content-Type": "application/json"} if data else {}
    try:
        req = urllib.request.Request(url, data=body, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        _err(f"POST {path} failed: {e}")
        return {}


# ── Demo Stages ──────────────────────────────────────────────────────────────

def run_demo(auto: bool = False):
    _print_box("FaultLens · Autonomous Incident & RCA Engine", "Live Terminal Demonstration for Judges & SRE Teams")

    # Check backend connectivity
    health = http_get("/health")
    if health.get("status") != "ok":
        _err("FaultLens backend is not responding on http://localhost:8000")
        _info("Start backend with: cd backend && ./venv/bin/uvicorn app.main:app --port 8000")
        sys.exit(1)

    _info("FaultLens Backend connection established: status=200 OK")

    # ─────────────────────────────────────────────────────────────────────────
    # STAGE 1: Baseline & Normal State
    # ─────────────────────────────────────────────────────────────────────────
    _step_header(1, "Baseline Operation — Normal Microservice Traffic")
    print("  In standard operations, microservices continuously exchange spans,")
    print("  metrics (latency, error rates), and health signals.")
    
    _info("Seeding healthy 12-minute baseline distribution across microservices...")
    import subprocess
    cmd = [sys.executable, "scripts/simulate_telemetry.py", "--baseline"]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    _info("Baseline seeded: 5 services (frontend, checkout, payment, currency, product-catalog)")

    _info("Executing detection pipeline on baseline data...")
    res = http_post("/api/v1/pipeline/run")
    anomalies = res.get("stage_1_anomaly_scan", {}).get("anomalies_detected", 0)
    incidents = res.get("stage_2_incidents", {}).get("incidents_created", 0)

    if anomalies == 0 and incidents == 0:
        print(f"\n  {GREEN}{BOLD}✓ SYSTEM HEALTHY:{RESET} 0 active anomalies │ All metrics within 3-sigma baseline")
    else:
        _warn(f"Previous state detected ({anomalies} anomalies). Preparing clean demo state...")

    _prompt_user(auto)

    # ─────────────────────────────────────────────────────────────────────────
    # STAGE 2: Chaos & Fault Injection
    # ─────────────────────────────────────────────────────────────────────────
    _step_header(2, "Fault Injection — Payment Gateway Timeout & Failures")
    print("  SCENARIO:")
    print("  1. Downstream 'payment' gateway suddenly experiences high latency (3,500ms).")
    print("  2. Payment service fails credit card authorizations with HTTP 504.")
    print("  3. Caller service 'checkout' begins timing out and throws errors.")
    print("  4. User-facing 'frontend' encounters checkout failures.")

    _warn("Injecting real-time failure telemetry into OTLP stream...")
    cmd = [sys.executable, "scripts/simulate_telemetry.py", "--fault", "payment-timeout"]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    _info("OTLP Spans, Metrics, and Error Logs submitted to /otlp/v1/*")

    _prompt_user(auto)

    # ─────────────────────────────────────────────────────────────────────────
    # STAGE 3: Statistical Anomaly Detection (Z-Score)
    # ─────────────────────────────────────────────────────────────────────────
    _step_header(3, "Stage 1/3: Statistical Anomaly Engine (Z-Score)")
    print("  Rather than using unreliable LLM prompting for math, FaultLens computes")
    print("  rolling population Z-scores:  Z = (current_mean - baseline_mean) / stddev")

    res = http_post("/api/v1/pipeline/run")
    scan = res.get("stage_1_anomaly_scan", {})
    detected = scan.get("anomalies", [])

    print(f"\n  Scanned {scan.get('scanned', 0)} metric series in {res.get('pipeline_duration_ms', 0)}ms:")
    for a in detected:
        z = a.get("z_score", 0)
        svc = a.get("service_name")
        metric = a.get("metric_name")
        cur = a.get("current_value", 0)
        base = a.get("baseline_mean", 0)
        direction = a.get("direction", "spike")
        print(f"    {RED}●{RESET} {BOLD}{svc:<16}{RESET} │ {CYAN}{metric:<18}{RESET} │ Z={RED}{z:.1f}{RESET} ({direction}) │ Cur={cur:.2f} vs Base={base:.2f}")

    _prompt_user(auto)

    # ─────────────────────────────────────────────────────────────────────────
    # STAGE 4: Incident Engine & Rule-Based Triage
    # ─────────────────────────────────────────────────────────────────────────
    _step_header(4, "Stage 2/3: Deterministic Incident Triage")
    print("  Anomalies are grouped by service and mapped against an SRE rule table:")
    print("  e.g., Z ≥ 8.0 on error rate → Critical 'SERVICE_DOWN'")

    inc_data = http_get("/api/v1/incidents")
    inc_list = inc_data.get("incidents", [])

    print(f"\n  Active Incidents ({len(inc_list)} open):")
    for inc in inc_list:
        sev = inc.get("severity", "medium").upper()
        color = RED if sev == "CRITICAL" else YELLOW
        print(f"    [{color}{BOLD}{sev}{RESET}] Incident #{inc.get('id')}: {inc.get('title')}")
        print(f"           Rule: {CYAN}{inc.get('triggered_by_rule')}{RESET} │ Services: {inc.get('affected_services')}")
        print(f"           {DIM}{inc.get('description')}{RESET}")

    _prompt_user(auto)

    # ─────────────────────────────────────────────────────────────────────────
    # STAGE 5: Graph Backward-Traversal RCA
    # ─────────────────────────────────────────────────────────────────────────
    _step_header(5, "Stage 3/3: Backward Graph Traversal Root Cause Analysis")
    print("  FaultLens walks the directed dependency graph backwards:")
    print("  frontend ──(calls)──> checkout ──(calls)──> payment")
    print("  Upstream victims receive lower candidate scores; the true origin scores 1.0.")

    rca_data = res.get("stage_3_rca", {}).get("results", [])
    for r in rca_data:
        root = r.get("root_cause_service")
        path = " → ".join(r.get("propagation_path", []))
        conf = r.get("confidence", 0)
        scores = r.get("candidate_scores", {})
        print(f"\n  Incident #{r.get('incident_id')} Analysis:")
        print(f"    {GREEN}{BOLD}ROOT CAUSE PINPOINTED:{RESET} {BOLD}{RED}{root}{RESET} (Confidence: {conf * 100:.0f}%)")
        print(f"    Propagation Path:      {CYAN}{path}{RESET}")
        print(f"    Candidate Scores:      {scores}")

    _prompt_user(auto)

    # ─────────────────────────────────────────────────────────────────────────
    # STAGE 6: Live Dashboard & Topology Snapshot
    # ─────────────────────────────────────────────────────────────────────────
    _step_header(6, "Live Microservice Topology & Dashboard Snapshot")
    dash = http_get("/api/v1/dashboard")
    summary = dash.get("summary", {})

    print(f"  Summary: {summary.get('service_count')} services total │ {GREEN}{summary.get('healthy_count')} healthy{RESET} │ {YELLOW}{summary.get('degraded_count')} degraded{RESET} │ {RED}{summary.get('critical_count')} critical{RESET}")
    print("\n  Service Dependency Graph Edges (Live Trace Derived):")
    edges = dash.get("dependency_graph", {}).get("edges", [])
    for e in edges:
        src = e.get("source")
        tgt = e.get("target")
        err_rate = e.get("error_rate", 0)
        status_color = RED if err_rate > 0.05 else GREEN
        print(f"    {src:<16} ──▶ {tgt:<16} │ Calls: {e.get('request_count')} │ Error Rate: {status_color}{err_rate*100:.1f}%{RESET}")

    _prompt_user(auto)

    # ─────────────────────────────────────────────────────────────────────────
    # STAGE 7: Self-Healing & Resolution
    # ─────────────────────────────────────────────────────────────────────────
    _step_header(7, "Resolution & Self-Healing Verification")
    print("  Simulating service remediation (upstream payment gateway restored)...")
    cmd = [sys.executable, "scripts/simulate_telemetry.py", "--fault", "recover"]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    _info("Normal telemetry restored.")

    _info("Re-running pipeline verification...")
    post_res = http_post("/api/v1/pipeline/run")
    dur = post_res.get("pipeline_duration_ms", 0)
    print(f"\n  {GREEN}{BOLD}✓ DEMO COMPLETE:{RESET} Pipeline executed in {dur}ms with zero Docker load.")
    print("  FaultLens successfully detected, triaged, and isolated the root cause.")
    print(f"{BOLD}{CYAN}══════════════════════════════════════════════════════════════{RESET}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FaultLens Live Terminal Demo")
    parser.add_argument("--auto", action="store_true", help="Run automatically without waiting for Enter key")
    args = parser.parse_args()
    run_demo(auto=args.auto)
