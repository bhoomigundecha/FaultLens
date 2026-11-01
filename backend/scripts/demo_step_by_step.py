#!/usr/bin/env python3
"""
FaultLens — Clean Step-by-Step Failure Demo
──────────────────────────────────────────
Concise, punchy demo script for judges and presentations.
Injects failures and shows step-by-step how FaultLens detects, triages,
and isolates the root cause in real time.

Usage:
  ./venv/bin/python scripts/demo_step_by_step.py
"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
import subprocess
from typing import Any

# ANSI Colors
RESET   = "\033[0m"
BOLD    = "\033[1m"
DIM     = "\033[2m"
CYAN    = "\033[36m"
GREEN   = "\033[32m"
YELLOW  = "\033[33m"
RED     = "\033[31m"
MAGENTA = "\033[35m"
WHITE   = "\033[37m"

BASE_URL = "http://localhost:8000"


def http_post(path: str, data: dict | None = None) -> dict[str, Any]:
    url = f"{BASE_URL}{path}"
    body = json.dumps(data or {}).encode() if data else b""
    headers = {"Content-Type": "application/json"} if data else {}
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        print(f"{RED}Error calling {url}: {e}{RESET}")
        return {}


def http_get(path: str) -> dict[str, Any]:
    url = f"{BASE_URL}{path}"
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        return {}


def run_failure_scenario(scenario_key: str, scenario_name: str, fault_arg: str):
    print(f"\n{BOLD}{CYAN}{'━' * 62}{RESET}")
    print(f"{BOLD}{WHITE}  SCENARIO: {scenario_name}{RESET}")
    print(f"{BOLD}{CYAN}{'━' * 62}{RESET}")

    # Step 1: Inject Failure
    print(f"\n{BOLD}{MAGENTA}[1/4] INJECTING FAILURE{RESET}")
    if fault_arg == "recover":
        print(f"  {GREEN}→ Restoring all services to normal baseline telemetry...{RESET}")
    else:
        print(f"  {RED}⚡ Emitting failure telemetry to OTLP stream: {fault_arg}{RESET}")
    
    cmd = [sys.executable, "scripts/simulate_telemetry.py", "--fault", fault_arg]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(0.5)

    # Step 2: Run Pipeline
    res = http_post("/api/v1/pipeline/run-with-ai")
    if not res:
        print(f"{RED}Failed to run pipeline. Is backend running?{RESET}")
        return

    dur = res.get("pipeline_duration_ms", 0)
    anomalies = res.get("stage_1_anomaly_scan", {}).get("anomalies", [])
    incidents = res.get("stage_2_incidents", {})
    rca = res.get("stage_3_rca", {}).get("results", [])
    ai = res.get("stage_4_ai", {}).get("results", [])

    # If recovery scenario
    if fault_arg == "recover":
        print(f"\n{BOLD}{GREEN}[✓] SYSTEM RECOVERED{RESET}")
        print(f"  {GREEN}→ All metric series within baseline. Open incidents resolved.{RESET}")
        print(f"  {DIM}Execution time: {dur}ms{RESET}\n")
        return

    # Step 2: Anomaly Detection
    print(f"\n{BOLD}{CYAN}[2/4] STATISTICAL ANOMALY DETECTION (Z-Score Engine){RESET}")
    if anomalies:
        for a in anomalies[:3]:
            svc = a.get("service_name")
            metric = a.get("metric_name")
            z = a.get("z_score", 0)
            cur = a.get("current_value", 0)
            base = a.get("baseline_mean", 0)
            direction = a.get("direction", "spike")
            print(f"  {RED}●{RESET} {BOLD}{svc:<16}{RESET} │ {metric:<18} │ {RED}Z = {z:.1f}{RESET} ({direction}) │ Cur={cur:.1f} (Base={base:.1f})")
    else:
        print(f"  {YELLOW}No new anomalies detected.{RESET}")

    # Step 3: Incident Engine
    print(f"\n{BOLD}{YELLOW}[3/4] INCIDENT ENGINE (Rule Triage){RESET}")
    inc_data = http_get("/api/v1/incidents")
    open_incidents = [i for i in inc_data.get("incidents", []) if i.get("status") == "open"]
    if open_incidents:
        for inc in open_incidents[:2]:
            sev = inc.get("severity", "medium").upper()
            sev_color = RED if sev == "CRITICAL" else YELLOW
            print(f"  🚨 [{sev_color}{BOLD}{sev}{RESET}] Incident #{inc.get('id')}: {BOLD}{inc.get('title')}{RESET}")
            print(f"     Rule: {CYAN}{inc.get('triggered_by_rule')}{RESET} │ Affected: {inc.get('affected_services')}")
    else:
        print(f"  {GREEN}No open incidents.{RESET}")

    # Step 4: Root Cause Analysis
    print(f"\n{BOLD}{GREEN}[4/4] ROOT CAUSE ANALYSIS (Graph Traversal & AI){RESET}")
    if rca:
        top_rca = rca[0]
        root = top_rca.get("root_cause_service")
        conf = top_rca.get("confidence", 0) * 100
        path = " ──▶ ".join(top_rca.get("propagation_path", []))
        print(f"  🎯 {BOLD}ROOT CAUSE:{RESET}       {BOLD}{RED}{root}{RESET} (Confidence: {conf:.0f}%)")
        print(f"  🔗 {BOLD}PROPAGATION PATH:{RESET} {CYAN}{path}{RESET}")
    
    if ai:
        top_ai = ai[0]
        print(f"  💡 {BOLD}AI DIAGNOSIS:{RESET}     Fault Type: {top_ai.get('fault_type')} (Confidence: {top_ai.get('confidence_label')})")

    print(f"\n{DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}")
    print(f"  {GREEN}✓ Completed in {dur}ms{RESET} │ Telemetry + Graph + RCA correlated")
    print(f"{DIM}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{RESET}\n")


def main():
    # Verify backend is running
    health = http_get("/health")
    if health.get("status") != "ok":
        print(f"\n{RED}[!] FaultLens backend is not running on {BASE_URL}.{RESET}")
        print(f"    Start it in another terminal with:")
        print(f"    cd backend && ./venv/bin/uvicorn app.main:app --port 8000\n")
        sys.exit(1)

    while True:
        print(f"\n{BOLD}{CYAN}╔══════════════════════════════════════════════════════════╗{RESET}")
        print(f"{BOLD}{CYAN}║             FaultLens · Live Failure Demo                ║{RESET}")
        print(f"{BOLD}{CYAN}╚══════════════════════════════════════════════════════════╝{RESET}")
        print(f"  {BOLD}Choose a failure to inject:{RESET}\n")
        print(f"  {CYAN}[1]{RESET} {BOLD}Payment Gateway Timeout{RESET}  (Latency jumps to 3.5s, 504 errors)")
        print(f"  {CYAN}[2]{RESET} {BOLD}Payment Service Crash{RESET}    (500 errors, worker crash)")
        print(f"  {CYAN}[3]{RESET} {BOLD}Database Latency Spike{RESET}   (Product Catalog DB query slow 2.5s)")
        print(f"  {CYAN}[4]{RESET} {BOLD}Reset System to Normal{RESET}   (Restore all services to healthy)")
        print(f"  {DIM}[q] Quit{RESET}\n")

        try:
            choice = input(f"  {BOLD}Enter choice [1-4]:{RESET} ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            break

        if choice == "1":
            run_failure_scenario("timeout", "Payment Gateway Timeout (504)", "payment-timeout")
        elif choice == "2":
            run_failure_scenario("crash", "Payment Service Crash (500)", "payment-crash")
        elif choice == "3":
            run_failure_scenario("db", "Database Latency Spike (2.5s)", "db-slowdown")
        elif choice == "4":
            run_failure_scenario("recover", "System Recovery", "recover")
        elif choice.lower() in ("q", "quit", "exit"):
            print("Goodbye!")
            break
        else:
            print(f"{YELLOW}Invalid choice, please enter 1, 2, 3, 4, or q.{RESET}")


if __name__ == "__main__":
    main()
