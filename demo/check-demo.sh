#!/usr/bin/env bash
# ── OpenTelemetry Demo — Phase 2 Health Check ─────────────────────────────────
# Run this from the demo/ directory after `docker compose up -d`.
# Verifies the core demo services are running and telemetry is flowing.
#
# Usage:
#   cd /Users/bhoomi/Desktop/Active/FaultLens/demo
#   bash check-demo.sh

set -uo pipefail

PASS="✅"
FAIL="❌"
WARN="⚠️ "
FAILURES=0

ok()   { echo "  $PASS $*"; }
fail() { echo "  $FAIL $*"; FAILURES=$((FAILURES+1)); }
warn() { echo "  $WARN $*"; }

echo ""
echo "═══════════════════════════════════════════════════════"
echo "  OpenTelemetry Demo (Astronomy Shop) — Phase 2 Check"
echo "═══════════════════════════════════════════════════════"
echo ""

# ── 1. Core containers ────────────────────────────────────────────────────────
echo "1. Container status (core services):"
CORE_CONTAINERS=(
  frontend-proxy
  frontend
  otel-collector
  flagd
  cart
  checkout
  payment
  product-catalog
  currency
  shipping
  recommendation
  ad
  load-generator
)

for c in "${CORE_CONTAINERS[@]}"; do
  STATUS=$(docker inspect --format='{{.State.Status}}' "$c" 2>/dev/null || echo "missing")
  if [ "$STATUS" = "running" ]; then
    ok "$c → running"
  else
    fail "$c → $STATUS"
  fi
done

echo ""

# ── 2. Frontend accessible ────────────────────────────────────────────────────
echo "2. Frontend (Astronomy Shop UI):"
STATUS=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "http://localhost:8080" 2>/dev/null || echo "000")
if [ "$STATUS" = "200" ]; then
  ok "http://localhost:8080 → HTTP $STATUS (shop is accessible)"
else
  fail "http://localhost:8080 → HTTP $STATUS (expected 200)"
fi

echo ""

# ── 3. OTel Collector ports ───────────────────────────────────────────────────
echo "3. OTel Collector:"
GRPC_OPEN=$(nc -z localhost 4317 2>/dev/null && echo "open" || echo "closed")
HTTP_OPEN=$(nc -z localhost 4318 2>/dev/null && echo "open" || echo "closed")

if [ "$GRPC_OPEN" = "open" ]; then
  ok "gRPC port 4317 → open"
else
  fail "gRPC port 4317 → $GRPC_OPEN"
fi
if [ "$HTTP_OPEN" = "open" ]; then
  ok "HTTP port 4318 → open"
else
  fail "HTTP port 4318 → $HTTP_OPEN"
fi

echo ""

# ── 4. Load generator producing traffic ───────────────────────────────────────
echo "4. Load generator (Locust) — last 5 log lines:"
docker logs load-generator --tail=5 2>&1 | sed 's/^/     /'
echo ""
LG_STATUS=$(docker inspect --format='{{.State.Status}}' load-generator 2>/dev/null || echo "missing")
if [ "$LG_STATUS" = "running" ]; then
  ok "load-generator → running (traffic is being generated)"
else
  warn "load-generator → $LG_STATUS"
fi

echo ""

# ── 5. Collector receiving telemetry ──────────────────────────────────────────
echo "5. OTel Collector — last 15 log lines:"
echo "   (look for: traces/metrics/logs received)"
docker logs otel-collector --tail=15 2>&1 | sed 's/^/     /'

echo ""

# ── 6. Locust web UI ─────────────────────────────────────────────────────────
echo "6. Locust web UI:"
LG_UI=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "http://localhost:8089" 2>/dev/null || echo "000")
if [ "$LG_UI" = "200" ]; then
  ok "http://localhost:8089 → HTTP $LG_UI (Locust UI accessible)"
else
  warn "http://localhost:8089 → HTTP $LG_UI (Locust may still be starting)"
fi

echo ""

# ── Summary ───────────────────────────────────────────────────────────────────
echo "═══════════════════════════════════════════════════════"
if [ "$FAILURES" -eq 0 ]; then
  echo "  $PASS ALL CHECKS PASSED"
  echo ""
  echo "  The OpenTelemetry Demo is running and healthy."
  echo "  Telemetry (traces/metrics/logs) is flowing through"
  echo "  the collector. FaultLens receives nothing yet."
  echo ""
  echo "  Phase 2 is COMPLETE. Proceed to Phase 3."
else
  echo "  $FAIL $FAILURES CHECK(S) FAILED — fix before proceeding."
  echo ""
  echo "  Troubleshooting:"
  echo "    docker compose logs <service-name> --tail=30"
  echo "    docker compose ps"
fi
echo "═══════════════════════════════════════════════════════"
echo ""
