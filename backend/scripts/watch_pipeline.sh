#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# FaultLens — Pipeline Watch Script
#
# Runs the full detection pipeline on a loop and prints a live dashboard
# in your terminal. Open this in a SECOND terminal while uvicorn runs in
# the first.
#
# Usage:
#   ./scripts/watch_pipeline.sh              # poll every 60 seconds
#   ./scripts/watch_pipeline.sh 30           # poll every 30 seconds
#   ./scripts/watch_pipeline.sh 0            # run once and exit
#
# Prerequisites:
#   brew install jq   (or: apt-get install jq)
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

BASE_URL="${FAULTLENS_URL:-http://localhost:8000}"
INTERVAL="${1:-60}"

# ── Colors ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'; YELLOW='\033[0;33m'; GREEN='\033[0;32m'
CYAN='\033[0;36m'; BOLD='\033[1m'; DIM='\033[2m'; RESET='\033[0m'

_header() { echo -e "\n${BOLD}${CYAN}━━━  $1  ━━━${RESET}"; }
_ok()     { echo -e "${GREEN}✓${RESET}  $*"; }
_warn()   { echo -e "${YELLOW}⚠${RESET}  $*"; }
_err()    { echo -e "${RED}✗${RESET}  $*"; }
_dim()    { echo -e "${DIM}$*${RESET}"; }

check_deps() {
  if ! command -v jq &>/dev/null; then
    echo -e "${RED}ERROR: 'jq' is required. Install: brew install jq${RESET}"
    exit 1
  fi
  if ! curl -sf "${BASE_URL}/health" >/dev/null 2>&1; then
    echo -e "${RED}ERROR: FaultLens is not reachable at ${BASE_URL}${RESET}"
    echo -e "Start it with:  cd backend && ./venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
    exit 1
  fi
}

run_pipeline() {
  local ts
  ts=$(date '+%Y-%m-%d %H:%M:%S')

  echo ""
  echo -e "${BOLD}${CYAN}╔══════════════════════════════════════════════════════════╗${RESET}"
  echo -e "${BOLD}${CYAN}║  FaultLens Pipeline Run   ${ts}       ║${RESET}"
  echo -e "${BOLD}${CYAN}╚══════════════════════════════════════════════════════════╝${RESET}"

  # ── Run pipeline ──────────────────────────────────────────────────────────
  local result
  result=$(curl -sf -X POST "${BASE_URL}/api/v1/pipeline/run" 2>/dev/null) || {
    _err "Pipeline call failed — is the server running?"
    return
  }

  local duration anomalies_detected incidents_created incidents_updated incidents_resolved rca_count
  duration=$(echo "$result"           | jq -r '.pipeline_duration_ms')
  anomalies_detected=$(echo "$result" | jq -r '.stage_1_anomaly_scan.anomalies_detected')
  incidents_created=$(echo "$result"  | jq -r '.stage_2_incidents.incidents_created')
  incidents_updated=$(echo "$result"  | jq -r '.stage_2_incidents.incidents_updated')
  incidents_resolved=$(echo "$result" | jq -r '.stage_2_incidents.incidents_resolved')
  rca_count=$(echo "$result"          | jq -r '.stage_3_rca.incidents_analysed')

  # ── Stage 1 — Anomalies ───────────────────────────────────────────────────
  _header "Stage 1 · Anomaly Scan"
  local scanned
  scanned=$(echo "$result" | jq -r '.stage_1_anomaly_scan.scanned')
  _dim "  Metric series scanned: ${scanned}"
  if [ "$anomalies_detected" -gt 0 ] 2>/dev/null; then
    _warn "  Anomalies detected: ${anomalies_detected}"
    echo "$result" | jq -r '
      .stage_1_anomaly_scan.anomalies[] |
      "  ⚡ \(.service_name) │ \(.metric_name) │ Z=\(.z_score | . * 10 | round / 10) (\(.direction))"
    ' 2>/dev/null || true
  else
    _ok "  No anomalies detected (all metrics within baseline)"
  fi

  # ── Stage 2 — Incidents ───────────────────────────────────────────────────
  _header "Stage 2 · Incident Engine"
  [ "$incidents_created"  -gt 0 ] 2>/dev/null && _warn "  Incidents CREATED:  ${incidents_created}"
  [ "$incidents_updated"  -gt 0 ] 2>/dev/null && _warn "  Incidents UPDATED:  ${incidents_updated}"
  [ "$incidents_resolved" -gt 0 ] 2>/dev/null && _ok   "  Incidents RESOLVED: ${incidents_resolved}"
  [ "$incidents_created" -eq 0 ] && [ "$incidents_updated" -eq 0 ] 2>/dev/null && \
    _ok "  No incident changes"

  # ── Stage 3 — RCA ─────────────────────────────────────────────────────────
  _header "Stage 3 · Root Cause Analysis"
  if [ "$rca_count" -gt 0 ] 2>/dev/null; then
    echo "$result" | jq -r '
      .stage_3_rca.results[] |
      "  ⚡ Incident \(.incident_id): root=\(.root_cause_service) confidence=\(.confidence) path=\(.propagation_path | join(" → "))"
    ' 2>/dev/null || true
  else
    _dim "  No open incidents to analyse"
  fi

  # ── Live dashboard snapshot ───────────────────────────────────────────────
  _header "Live Dashboard Snapshot"
  local dashboard
  dashboard=$(curl -sf "${BASE_URL}/api/v1/dashboard" 2>/dev/null) || {
    _err "Dashboard fetch failed"; return
  }

  local svc_count healthy degraded critical inc_count anomaly_count
  svc_count=$(echo "$dashboard"    | jq -r '.summary.service_count')
  healthy=$(echo "$dashboard"      | jq -r '.summary.healthy_count')
  degraded=$(echo "$dashboard"     | jq -r '.summary.degraded_count')
  critical=$(echo "$dashboard"     | jq -r '.summary.critical_count')
  inc_count=$(echo "$dashboard"    | jq -r '.summary.open_incident_count')
  anomaly_count=$(echo "$dashboard"| jq -r '.summary.active_anomaly_count')

  echo -e "  Services: ${svc_count} total │ ${GREEN}${healthy} healthy${RESET} │ ${YELLOW}${degraded} degraded${RESET} │ ${RED}${critical} critical${RESET}"
  echo -e "  Open incidents:  ${inc_count}    Active anomalies: ${anomaly_count}"

  # Show open incidents
  if [ "$inc_count" -gt 0 ] 2>/dev/null; then
    echo ""
    echo "$dashboard" | jq -r '
      .incidents[] |
      "  [\(.severity | ascii_upcase)] \(.title) — rule: \(.triggered_by_rule // "N/A")"
    ' 2>/dev/null | while IFS= read -r line; do
      if echo "$line" | grep -q "\[CRITICAL\]"; then
        echo -e "  ${RED}${BOLD}${line}${RESET}"
      elif echo "$line" | grep -q "\[HIGH\]"; then
        echo -e "  ${RED}${line}${RESET}"
      elif echo "$line" | grep -q "\[MEDIUM\]"; then
        echo -e "  ${YELLOW}${line}${RESET}"
      else
        echo -e "  ${DIM}${line}${RESET}"
      fi
    done
  fi

  echo ""
  _dim "  Pipeline completed in ${duration}ms"
  _dim "  Next run in ${INTERVAL}s  (Ctrl+C to stop)"
}

# ── Main loop ─────────────────────────────────────────────────────────────────
check_deps

if [ "$INTERVAL" -eq 0 ] 2>/dev/null; then
  run_pipeline
  exit 0
fi

while true; do
  run_pipeline
  sleep "$INTERVAL"
done
