/**
 * otel.js — OpenTelemetry SDK bootstrap.
 * Copy this file identically into every service.
 * Set OTEL_SERVICE_NAME per service via env var.
 * Must be -r required before any other import.
 */
'use strict';

const { NodeSDK } = require('@opentelemetry/sdk-node');
const { getNodeAutoInstrumentations } = require('@opentelemetry/auto-instrumentations-node');
const { OTLPTraceExporter }  = require('@opentelemetry/exporter-trace-otlp-http');
const { OTLPMetricExporter } = require('@opentelemetry/exporter-metrics-otlp-http');
const { OTLPLogExporter }    = require('@opentelemetry/exporter-logs-otlp-http');
const { Resource }           = require('@opentelemetry/resources');
const { SEMRESATTRS_SERVICE_NAME, SEMRESATTRS_SERVICE_VERSION } =
  require('@opentelemetry/semantic-conventions');
const { PeriodicExportingMetricReader } = require('@opentelemetry/sdk-metrics');
const { BatchLogRecordProcessor }       = require('@opentelemetry/sdk-logs');

const ENDPOINT = process.env.OTEL_EXPORTER_OTLP_ENDPOINT || 'http://localhost:4318';
const SERVICE  = process.env.OTEL_SERVICE_NAME           || 'unknown-service';

const sdk = new NodeSDK({
  resource: new Resource({
    [SEMRESATTRS_SERVICE_NAME]:    SERVICE,
    [SEMRESATTRS_SERVICE_VERSION]: '2.0.0',
    'deployment.environment': process.env.NODE_ENV || 'production',
  }),
  traceExporter: new OTLPTraceExporter({ url: `${ENDPOINT}/v1/traces` }),
  metricReader: new PeriodicExportingMetricReader({
    exporter: new OTLPMetricExporter({ url: `${ENDPOINT}/v1/metrics` }),
    exportIntervalMillis: 10_000,
  }),
  logRecordProcessor: new BatchLogRecordProcessor(
    new OTLPLogExporter({ url: `${ENDPOINT}/v1/logs` })
  ),
  instrumentations: [
    getNodeAutoInstrumentations({
      '@opentelemetry/instrumentation-fs':      { enabled: false },
      '@opentelemetry/instrumentation-http':    { enabled: true },
      '@opentelemetry/instrumentation-express': { enabled: true },
      '@opentelemetry/instrumentation-pg':      { enabled: true },
      '@opentelemetry/instrumentation-ioredis': { enabled: true },
    }),
  ],
});

sdk.start();
process.on('SIGTERM', () => sdk.shutdown().finally(() => process.exit(0)));
console.log(`[OTel] ${SERVICE} → ${ENDPOINT}`);
