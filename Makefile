PYTHON ?= python3

.PHONY: up down init-db logs ingestion worker topics pull-models \
        demo-up demo-down demo-logs demo-inject demo-restore monitor

# ─── FaultLens infrastructure ─────────────────────────────────────────────────
up:
	docker compose up -d --build

down:
	docker compose down -v

logs:
	docker compose logs -f

logs-ingestion:
	docker compose logs -f ingestion

logs-worker:
	docker compose logs -f agent-worker

# ─── DB Schema Init ───────────────────────────────────────────────────────────
init-db:
	$(PYTHON) storage/init_schemas.py

# ─── Topics ───────────────────────────────────────────────────────────────────
topics:
	docker exec faultlens-redpanda rpk topic create raw.metrics raw.logs raw.traces anomaly.events rca.results \
		--brokers localhost:9092 \
		--partitions 3 \
		--replicas 1

# ─── Local Dev (no Docker) ────────────────────────────────────────────────────
dev-ingestion:
	uvicorn ingestion.main:app --host 0.0.0.0 --port 8000 --reload

dev-worker:
	$(PYTHON) -m agents.worker

# ─── Ollama ───────────────────────────────────────────────────────────────────
pull-models:
	ollama pull llama3.2
	ollama pull nomic-embed-text

# ─── ShopFlow Demo App ────────────────────────────────────────────────────────
demo-up:
	@echo "Starting ShopFlow (multi-service e-commerce demo)..."
	cd demo && docker compose up -d --build
	@echo ""
	@echo "  api-gateway:       http://localhost:3000"
	@echo "  order-service:     http://localhost:3001"
	@echo "  inventory-service: http://localhost:3002"
	@echo "  payment-service:   http://localhost:3003"
	@echo "  ai-service:        http://localhost:3004"

demo-down:
	cd demo && docker compose down -v

demo-logs:
	cd demo && docker compose logs -f

check-gateway:
	@curl -sf http://localhost:3000/health > /dev/null 2>&1 || { echo "❌ Error: ShopFlow is not running at http://localhost:3000! Please start it first with 'make demo-up'."; exit 1; }

demo-status:
	@curl -s http://localhost:3000/chaos/status | $(PYTHON) -m json.tool 2>/dev/null || echo "❌ ShopFlow is not running. Start it with 'make demo-up'."

# Trigger a realistic 1-2 fault production incident that STAYS DOWN until resolved
demo-inject-incident: check-gateway
	@echo "Injecting production incident in ShopFlow (stays down until you run 'make demo-restore')..."
	@curl -s -X POST http://localhost:3000/chaos/incident | $(PYTHON) -m json.tool

demo-restore: check-gateway
	@echo "Applying fix / Restoring ShopFlow to 100% healthy state..."
	@curl -s -X POST http://localhost:3000/chaos/reset | $(PYTHON) -m json.tool

# Specific realistic production faults (stay down until you run 'make demo-restore')
demo-inject-payment: check-gateway
	@echo "Injecting payment gateway slowdown (stays down until 'make demo-restore')..."
	@curl -s -X POST http://localhost:3000/admin/payment/set-latency -H "Content-Type: application/json" -d '{"latency_ms": 6000, "failure_rate": 0.20}' | $(PYTHON) -m json.tool

demo-inject-ai: check-gateway
	@echo "Injecting AI token quota exhaustion / 429 throttle (stays down until 'make demo-restore')..."
	@curl -s -X POST http://localhost:3000/admin/ai/rate-limit/enable -H "Content-Type: application/json" -d '{"rpm": 3}' | $(PYTHON) -m json.tool

demo-inject-stampede: check-gateway
	@echo "Injecting Redis cache drop & DB connection pressure (stays down until 'make demo-restore')..."
	@curl -s -X POST http://localhost:3000/admin/redis/flush | $(PYTHON) -m json.tool

# ─── FaultLens Monitoring & Verification ───────────────────────────────────────
monitor:
	$(PYTHON) tests/monitor.py

# ─── Tests ────────────────────────────────────────────────────────────────────
test-ingest-metrics:
	curl -X POST http://localhost:8000/v1/ingest/metrics \
		-H "Content-Type: application/json" \
		-d @tests/fixtures/sample_otlp_metrics.json

test-ingest-logs:
	curl -X POST http://localhost:8000/v1/ingest/logs \
		-H "Content-Type: application/json" \
		-d @tests/fixtures/sample_otlp_logs.json

test-ingest-traces:
	curl -X POST http://localhost:8000/v1/ingest/traces \
		-H "Content-Type: application/json" \
		-d @tests/fixtures/sample_otlp_traces.json

trigger-incident:
	$(PYTHON) tests/trigger_incident.py

verify-incident:
	$(PYTHON) tests/verify_incident.py

check-incidents:
	curl -s http://localhost:8000/v1/incidents | $(PYTHON) -m json.tool
