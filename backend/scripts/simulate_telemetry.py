#!/usr/bin/env python3
"""
FaultLens — Lightweight Telemetry & Fault Simulator
────────────────────────────────────────────────────
Simulates realistic microservice traffic, service dependencies, baseline metrics,
and targeted fault injection directly to FaultLens via OTLP protobuf HTTP endpoints.

ZERO Docker containers required. Takes < 0.2% CPU and ~15MB RAM.

Usage:
  # 1. Seed 10 minutes of normal baseline traffic (instantly establishes baseline):
  python scripts/simulate_telemetry.py --baseline

  # 2. Inject a payment service timeout fault (high latency + error status):
  python scripts/simulate_telemetry.py --fault payment-timeout

  # 3. Inject a payment service crash fault (100% 500 errors + error logs):
  python scripts/simulate_telemetry.py --fault payment-crash

  # 4. Inject a database / product-catalog latency spike:
  python scripts/simulate_telemetry.py --fault db-slowdown

  # 5. Recover all services to normal:
  python scripts/simulate_telemetry.py --fault recover

  # 6. Run live low-frequency traffic stream (1 batch every 3s, negligible CPU):
  python scripts/simulate_telemetry.py --stream
"""
from __future__ import annotations

import argparse
import random
import sys
import time
import urllib.error
import urllib.request
from typing import Any

from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTraceServiceRequest
from opentelemetry.proto.collector.metrics.v1.metrics_service_pb2 import ExportMetricsServiceRequest
from opentelemetry.proto.collector.logs.v1.logs_service_pb2 import ExportLogsServiceRequest
from opentelemetry.proto.trace.v1.trace_pb2 import ResourceSpans, ScopeSpans, Span, Status
from opentelemetry.proto.metrics.v1.metrics_pb2 import ResourceMetrics, ScopeMetrics, Metric, Gauge, NumberDataPoint
from opentelemetry.proto.logs.v1.logs_pb2 import ResourceLogs, ScopeLogs, LogRecord
from opentelemetry.proto.common.v1.common_pb2 import AnyValue, KeyValue, InstrumentationScope
from opentelemetry.proto.resource.v1.resource_pb2 import Resource

_PROTO_HEADER = {"Content-Type": "application/x-protobuf"}
_DEFAULT_HOST = "http://localhost:8000"
_NS = 1_000_000_000

# ── Helper Builders ──────────────────────────────────────────────────────────

def _kv(key: str, value: Any) -> KeyValue:
    if isinstance(value, bool):
        return KeyValue(key=key, value=AnyValue(bool_value=value))
    elif isinstance(value, int):
        return KeyValue(key=key, value=AnyValue(int_value=value))
    elif isinstance(value, float):
        return KeyValue(key=key, value=AnyValue(double_value=value))
    return KeyValue(key=key, value=AnyValue(string_value=str(value)))


def _resource(service_name: str) -> Resource:
    return Resource(attributes=[
        _kv("service.name", service_name),
        _kv("telemetry.sdk.name", "faultlens-simulator"),
        _kv("telemetry.sdk.version", "1.0.0"),
    ])


def _scope(name: str = "faultlens.simulator") -> InstrumentationScope:
    return InstrumentationScope(name=name, version="1.0.0")


def post_otlp(endpoint: str, data: bytes, base_url: str = _DEFAULT_HOST) -> bool:
    url = f"{base_url.rstrip('/')}{endpoint}"
    req = urllib.request.Request(url, data=data, headers=_PROTO_HEADER, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status in (200, 202)
    except urllib.error.URLError as e:
        print(f"  [!] HTTP POST to {url} failed: {e}", file=sys.stderr)
        return False


# ── Telemetry Generators ─────────────────────────────────────────────────────

def build_traces_payload(
    timestamp_ns: int,
    payment_status: str = "normal",  # "normal", "timeout", "crash"
    db_status: str = "normal",       # "normal", "slow"
) -> bytes:
    """
    Generates a distributed transaction across:
      frontend -> checkout -> payment -> currency
      frontend -> product-catalog
    """
    trace_id = random.randbytes(16)
    s_frontend = random.randbytes(8)
    s_checkout = random.randbytes(8)
    s_payment = random.randbytes(8)
    s_currency = random.randbytes(8)
    s_catalog = random.randbytes(8)

    # Durations in nanoseconds
    d_currency = int(random.uniform(8, 15) * 1_000_000)
    
    if payment_status == "timeout":
        d_payment = int(random.uniform(3200, 3800) * 1_000_000)
        pay_code = 2  # ERROR
        pay_msg = "GatewayTimeout: upstream payment gateway unresponsive"
    elif payment_status == "crash":
        d_payment = int(random.uniform(50, 90) * 1_000_000)
        pay_code = 2  # ERROR
        pay_msg = "HTTP 500 InternalServerError: connection refused by payment daemon"
    else:
        d_payment = int(random.uniform(35, 55) * 1_000_000) + d_currency
        pay_code = 1  # OK
        pay_msg = "OK"

    if db_status == "slow":
        d_catalog = int(random.uniform(2200, 2800) * 1_000_000)
        cat_code = 2
        cat_msg = "QueryTimeout: database lock acquisition timeout"
    else:
        d_catalog = int(random.uniform(15, 30) * 1_000_000)
        cat_code = 1
        cat_msg = "OK"

    d_checkout = d_payment + int(random.uniform(20, 40) * 1_000_000)
    d_frontend = max(d_checkout, d_catalog) + int(random.uniform(20, 50) * 1_000_000)

    chk_code = 2 if pay_code == 2 else 1
    chk_msg = "CheckoutFailed: payment failed" if pay_code == 2 else "OK"
    front_code = 2 if (chk_code == 2 or cat_code == 2) else 1

    # Spans
    span_front = Span(
        trace_id=trace_id, span_id=s_frontend, parent_span_id=b"",
        name="POST /cart/checkout", kind=2,
        start_time_unix_nano=timestamp_ns,
        end_time_unix_nano=timestamp_ns + d_frontend,
        status=Status(code=front_code),
        attributes=[_kv("http.status_code", 500 if front_code == 2 else 200)]
    )
    span_chk = Span(
        trace_id=trace_id, span_id=s_checkout, parent_span_id=s_frontend,
        name="checkout.PlaceOrder", kind=2,
        start_time_unix_nano=timestamp_ns + 5_000_000,
        end_time_unix_nano=timestamp_ns + 5_000_000 + d_checkout,
        status=Status(code=chk_code, message=chk_msg),
    )
    span_pay = Span(
        trace_id=trace_id, span_id=s_payment, parent_span_id=s_checkout,
        name="payment.ChargeCard", kind=2,
        start_time_unix_nano=timestamp_ns + 10_000_000,
        end_time_unix_nano=timestamp_ns + 10_000_000 + d_payment,
        status=Status(code=pay_code, message=pay_msg),
        attributes=[
            _kv("payment.provider", "stripe"),
            _kv("http.status_code", 504 if payment_status == "timeout" else (500 if payment_status == "crash" else 200)),
        ]
    )
    span_curr = Span(
        trace_id=trace_id, span_id=s_currency, parent_span_id=s_payment,
        name="currency.ConvertCurrency", kind=2,
        start_time_unix_nano=timestamp_ns + 15_000_000,
        end_time_unix_nano=timestamp_ns + 15_000_000 + d_currency,
        status=Status(code=1, message="OK"),
    )
    span_cat = Span(
        trace_id=trace_id, span_id=s_catalog, parent_span_id=s_frontend,
        name="productcatalog.GetProduct", kind=2,
        start_time_unix_nano=timestamp_ns + 5_000_000,
        end_time_unix_nano=timestamp_ns + 5_000_000 + d_catalog,
        status=Status(code=cat_code, message=cat_msg),
    )

    req = ExportTraceServiceRequest(
        resource_spans=[
            ResourceSpans(resource=_resource("frontend"), scope_spans=[ScopeSpans(scope=_scope(), spans=[span_front])]),
            ResourceSpans(resource=_resource("checkout"), scope_spans=[ScopeSpans(scope=_scope(), spans=[span_chk])]),
            ResourceSpans(resource=_resource("payment"), scope_spans=[ScopeSpans(scope=_scope(), spans=[span_pay])]),
            ResourceSpans(resource=_resource("currency"), scope_spans=[ScopeSpans(scope=_scope(), spans=[span_curr])]),
            ResourceSpans(resource=_resource("product-catalog"), scope_spans=[ScopeSpans(scope=_scope(), spans=[span_cat])]),
        ]
    )
    return req.SerializeToString()


def build_metrics_payload(
    timestamp_ns: int,
    payment_status: str = "normal",
    db_status: str = "normal",
) -> bytes:
    """Generates duration and error_rate metric points for all services."""
    services = {
        "frontend": {"duration": random.uniform(50, 70), "error_rate": 0.0},
        "checkout": {"duration": random.uniform(40, 60), "error_rate": 0.0},
        "payment": {"duration": random.uniform(35, 50), "error_rate": 0.0},
        "currency": {"duration": random.uniform(8, 15), "error_rate": 0.0},
        "product-catalog": {"duration": random.uniform(15, 25), "error_rate": 0.0},
    }

    if payment_status == "timeout":
        services["payment"]["duration"] = random.uniform(3400, 3900)
        services["payment"]["error_rate"] = random.uniform(0.7, 0.95)
        services["checkout"]["error_rate"] = random.uniform(0.6, 0.9)
        services["frontend"]["error_rate"] = random.uniform(0.5, 0.8)
    elif payment_status == "crash":
        services["payment"]["duration"] = random.uniform(40, 60)
        services["payment"]["error_rate"] = 1.0
        services["checkout"]["error_rate"] = random.uniform(0.8, 1.0)
        services["frontend"]["error_rate"] = random.uniform(0.7, 1.0)

    if db_status == "slow":
        services["product-catalog"]["duration"] = random.uniform(2200, 2700)
        services["product-catalog"]["error_rate"] = random.uniform(0.4, 0.6)

    resource_metrics = []
    for svc_name, metrics in services.items():
        m_list = []
        # Duration metric (gauge)
        m_list.append(Metric(
            name="app.latency",
            description="Request duration in milliseconds",
            gauge=Gauge(data_points=[NumberDataPoint(time_unix_nano=timestamp_ns, as_double=metrics["duration"])])
        ))
        # Error rate metric (gauge)
        m_list.append(Metric(
            name="app.error_rate",
            description="Ratio of failed requests [0.0 - 1.0]",
            gauge=Gauge(data_points=[NumberDataPoint(time_unix_nano=timestamp_ns, as_double=metrics["error_rate"])])
        ))
        resource_metrics.append(
            ResourceMetrics(resource=_resource(svc_name), scope_metrics=[ScopeMetrics(scope=_scope(), metrics=m_list)])
        )

    req = ExportMetricsServiceRequest(resource_metrics=resource_metrics)
    return req.SerializeToString()


def build_logs_payload(timestamp_ns: int, payment_status: str = "normal") -> bytes:
    """Generates structured logs with trace IDs."""
    if payment_status == "normal":
        records = [
            LogRecord(
                time_unix_nano=timestamp_ns,
                severity_text="INFO",
                severity_number=9,
                body=AnyValue(string_value="Charge authorized successfully for cart order"),
                attributes=[_kv("payment.status", "authorized")]
            )
        ]
        svc = "payment"
    elif payment_status == "timeout":
        records = [
            LogRecord(
                time_unix_nano=timestamp_ns,
                severity_text="ERROR",
                severity_number=17,
                body=AnyValue(string_value="PaymentGatewayTimeout: downstream payment processor did not respond within 3500ms"),
                attributes=[_kv("error.type", "timeout"), _kv("http.status_code", 504)]
            )
        ]
        svc = "payment"
    else:  # crash
        records = [
            LogRecord(
                time_unix_nano=timestamp_ns,
                severity_text="FATAL",
                severity_number=21,
                body=AnyValue(string_value="PaymentWorkerCrash: unhandled exception in card tokenisation thread: ConnectionResetError"),
                attributes=[_kv("error.type", "crash"), _kv("http.status_code", 500)]
            )
        ]
        svc = "payment"

    req = ExportLogsServiceRequest(
        resource_logs=[ResourceLogs(resource=_resource(svc), scope_logs=[ScopeLogs(scope=_scope(), log_records=records)])]
    )
    return req.SerializeToString()


# ── High Level Actions ────────────────────────────────────────────────────────

def seed_baseline(base_url: str = _DEFAULT_HOST, minutes: int = 12) -> None:
    """
    Seeds `minutes` of historical normal data at 30-second increments.
    Establishes a solid Z-score baseline instantly.
    """
    print(f"[*] Seeding {minutes} minutes of normal baseline telemetry across 5 services...")
    now_ns = time.time_ns()
    step_ns = 30 * _NS
    points = int((minutes * 60) / 30)
    start_ns = now_ns - (points * step_ns)

    sent = 0
    for i in range(points):
        ts = start_ns + (i * step_ns)
        # Send trace batch (establishes graph edges)
        tr = build_traces_payload(ts, payment_status="normal")
        post_otlp("/otlp/v1/traces", tr, base_url)

        # Send metric batch (establishes baseline mean/stddev)
        mt = build_metrics_payload(ts, payment_status="normal")
        post_otlp("/otlp/v1/metrics", mt, base_url)

        sent += 1
        if sent % 5 == 0 or sent == points:
            sys.stdout.write(f"\r    Progress: {sent}/{points} snapshots ({int(sent/points*100)}%)")
            sys.stdout.flush()

    print("\n[+] Baseline seed complete! All 5 services have healthy baselines.")


def inject_fault(fault_type: str, base_url: str = _DEFAULT_HOST, num_batches: int = 4) -> None:
    """
    Injects immediate anomalous points into the CURRENT window.
    """
    print(f"[*] Injecting fault: '{fault_type}' ({num_batches} batches into current window)...")
    now_ns = time.time_ns()
    
    pay_status = "normal"
    db_status = "normal"

    if fault_type == "payment-timeout":
        pay_status = "timeout"
    elif fault_type == "payment-crash":
        pay_status = "crash"
    elif fault_type == "db-slowdown":
        db_status = "slow"
    elif fault_type in ("normal", "recover"):
        pay_status = "normal"
        db_status = "normal"
    else:
        print(f"[!] Unknown fault type: {fault_type}. Available: payment-timeout, payment-crash, db-slowdown, recover")
        return

    for i in range(num_batches):
        ts = now_ns - ((num_batches - 1 - i) * 2 * _NS)
        tr = build_traces_payload(ts, payment_status=pay_status, db_status=db_status)
        post_otlp("/otlp/v1/traces", tr, base_url)

        mt = build_metrics_payload(ts, payment_status=pay_status, db_status=db_status)
        post_otlp("/otlp/v1/metrics", mt, base_url)

        lg = build_logs_payload(ts, payment_status=pay_status)
        post_otlp("/otlp/v1/logs", lg, base_url)
        time.sleep(0.1)

    print(f"[+] Fault telemetry injected successfully.")
    print("    -> Run pipeline now to see instant detection:")
    print(f"       curl -s -X POST {base_url}/api/v1/pipeline/run-with-ai | python3 -m json.tool")


def stream_loop(base_url: str = _DEFAULT_HOST, interval: float = 3.0) -> None:
    """
    Lightweight background loop sending regular telemetry. Uses negligible CPU.
    """
    print(f"[*] Streaming live normal telemetry every {interval}s to {base_url}...")
    print("    Press Ctrl+C to stop.")
    try:
        while True:
            now_ns = time.time_ns()
            tr = build_traces_payload(now_ns)
            post_otlp("/otlp/v1/traces", tr, base_url)

            mt = build_metrics_payload(now_ns)
            post_otlp("/otlp/v1/metrics", mt, base_url)

            sys.stdout.write(".")
            sys.stdout.flush()
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n[*] Stream stopped.")


# ── Entry Point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="FaultLens Telemetry & Fault Simulator")
    parser.add_argument("--url", default=_DEFAULT_HOST, help="FaultLens backend base URL (default: http://localhost:8000)")
    parser.add_argument("--baseline", action="store_true", help="Seed 10+ minutes of historical normal baseline telemetry")
    parser.add_argument("--fault", choices=["payment-timeout", "payment-crash", "db-slowdown", "recover"], help="Inject a fault scenario")
    parser.add_argument("--stream", action="store_true", help="Stream quiet normal telemetry continuously (Ctrl+C to stop)")
    args = parser.parse_args()

    if args.baseline:
        seed_baseline(args.url)
    elif args.fault:
        inject_fault(args.fault, args.url)
    elif args.stream:
        stream_loop(args.url)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
