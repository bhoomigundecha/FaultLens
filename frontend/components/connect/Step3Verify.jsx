'use client';
import { useState } from 'react';

const CODE_EXAMPLES = {
  nodejs: {
    install: 'npm install @opentelemetry/sdk-node @opentelemetry/exporter-otlp-http',
    lines: [
      { text: "const { NodeSDK } = require('@opentelemetry/sdk-node');", color: '#e2e8f0' },
      { text: "const { OTLPTraceExporter } = require('@opentelemetry/exporter-otlp-http');", color: '#e2e8f0' },
      { text: '', color: 'transparent' },
      { text: 'const sdk = new NodeSDK({', color: '#e2e8f0' },
      { text: '  traceExporter: new OTLPTraceExporter({', color: '#e2e8f0' },
      { text: "    url: 'https://api.faultlens.com/v1/otlp',", color: '#93c5fd' },
      { text: "    headers: { 'Authorization': 'fl_live_3f9a2c4e8b1d7a6e...' }", color: '#93c5fd' },
      { text: '  }),', color: '#e2e8f0' },
      { text: '});', color: '#e2e8f0' },
      { text: 'sdk.start();', color: '#60a5fa' },
    ],
    raw: `const { NodeSDK } = require('@opentelemetry/sdk-node');
const { OTLPTraceExporter } = require('@opentelemetry/exporter-otlp-http');

const sdk = new NodeSDK({
  traceExporter: new OTLPTraceExporter({
    url: 'https://api.faultlens.com/v1/otlp',
    headers: { 'Authorization': 'fl_live_3f9a2c4e8b1d7a6e...' }
  }),
});
sdk.start();`,
  },
  python: {
    install: 'pip install opentelemetry-distro opentelemetry-exporter-otlp',
    lines: [
      { text: 'from opentelemetry import trace', color: '#e2e8f0' },
      { text: 'from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter', color: '#e2e8f0' },
      { text: 'from opentelemetry.sdk.trace import TracerProvider', color: '#e2e8f0' },
      { text: 'from opentelemetry.sdk.trace.export import BatchSpanProcessor', color: '#e2e8f0' },
      { text: '', color: 'transparent' },
      { text: 'provider = TracerProvider()', color: '#60a5fa' },
      { text: 'processor = BatchSpanProcessor(OTLPSpanExporter(', color: '#e2e8f0' },
      { text: '    endpoint="https://api.faultlens.com/v1/otlp",', color: '#93c5fd' },
      { text: '    headers={"Authorization": "fl_live_3f9a2c4e8b1d7a6e..."}', color: '#93c5fd' },
      { text: '))', color: '#e2e8f0' },
      { text: 'provider.add_span_processor(processor)', color: '#e2e8f0' },
      { text: 'trace.set_tracer_provider(provider)', color: '#60a5fa' },
    ],
    raw: `from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

provider = TracerProvider()
processor = BatchSpanProcessor(OTLPSpanExporter(
    endpoint="https://api.faultlens.com/v1/otlp",
    headers={"Authorization": "fl_live_3f9a2c4e8b1d7a6e..."}
))
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)`,
  },
  java: {
    install: 'curl -L -O https://github.com/open-telemetry/opentelemetry-java-instrumentation/releases/latest/download/opentelemetry-javaagent.jar',
    lines: [
      { text: 'java -javaagent:./opentelemetry-javaagent.jar \\', color: '#e2e8f0' },
      { text: '     -Dotel.exporter.otlp.endpoint=https://api.faultlens.com/v1/otlp \\', color: '#93c5fd' },
      { text: '     -Dotel.exporter.otlp.headers="Authorization=fl_live_3f9a2c4e8b1d7a6e..." \\', color: '#93c5fd' },
      { text: '     -jar target/my-app.jar', color: '#60a5fa' },
    ],
    raw: `java -javaagent:./opentelemetry-javaagent.jar \\
     -Dotel.exporter.otlp.endpoint=https://api.faultlens.com/v1/otlp \\
     -Dotel.exporter.otlp.headers="Authorization=fl_live_3f9a2c4e8b1d7a6e..." \\
     -jar target/my-app.jar`,
  },
  go: {
    install: 'go get go.opentelemetry.io/otel go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracehttp',
    lines: [
      { text: 'exporter, err := otlptracehttp.New(ctx,', color: '#e2e8f0' },
      { text: '    otlptracehttp.WithEndpoint("api.faultlens.com/v1/otlp"),', color: '#93c5fd' },
      { text: '    otlptracehttp.WithHeaders(map[string]string{', color: '#e2e8f0' },
      { text: '        "Authorization": "fl_live_3f9a2c4e8b1d7a6e...",', color: '#93c5fd' },
      { text: '    }),', color: '#e2e8f0' },
      { text: ')', color: '#e2e8f0' },
      { text: 'tp := sdktrace.NewTracerProvider(sdktrace.WithBatcher(exporter))', color: '#60a5fa' },
      { text: 'otel.SetTracerProvider(tp)', color: '#60a5fa' },
    ],
    raw: `exporter, err := otlptracehttp.New(ctx,
    otlptracehttp.WithEndpoint("api.faultlens.com/v1/otlp"),
    otlptracehttp.WithHeaders(map[string]string{
        "Authorization": "fl_live_3f9a2c4e8b1d7a6e...",
    }),
)
tp := sdktrace.NewTracerProvider(sdktrace.WithBatcher(exporter))
otel.SetTracerProvider(tp)`,
  },
  dotnet: {
    install: 'dotnet add package OpenTelemetry.Exporter.OpenTelemetryProtocol',
    lines: [
      { text: 'builder.Services.AddOpenTelemetry()', color: '#e2e8f0' },
      { text: '    .WithTracing(tracing => tracing', color: '#e2e8f0' },
      { text: '        .AddOtlpExporter(opt => {', color: '#e2e8f0' },
      { text: '            opt.Endpoint = new Uri("https://api.faultlens.com/v1/otlp");', color: '#93c5fd' },
      { text: '            opt.Headers = "Authorization=fl_live_3f9a2c4e8b1d7a6e...";', color: '#93c5fd' },
      { text: '        }));', color: '#60a5fa' },
    ],
    raw: `builder.Services.AddOpenTelemetry()
    .WithTracing(tracing => tracing
        .AddOtlpExporter(opt => {
            opt.Endpoint = new Uri("https://api.faultlens.com/v1/otlp");
            opt.Headers = "Authorization=fl_live_3f9a2c4e8b1d7a6e...";
        }));`,
  },
  ruby: {
    install: 'gem install opentelemetry-sdk opentelemetry-exporter-otlp',
    lines: [
      { text: "require 'opentelemetry/sdk'", color: '#e2e8f0' },
      { text: "require 'opentelemetry/exporter/otlp'", color: '#e2e8f0' },
      { text: '', color: 'transparent' },
      { text: 'OpenTelemetry::SDK.configure do |c|', color: '#e2e8f0' },
      { text: '  c.use_all', color: '#60a5fa' },
      { text: '  c.add_span_processor(', color: '#e2e8f0' },
      { text: '    OpenTelemetry::SDK::Trace::Export::BatchSpanProcessor.new(', color: '#e2e8f0' },
      { text: '      OpenTelemetry::Exporter::OTLP::Exporter.new(', color: '#e2e8f0' },
      { text: "        endpoint: 'https://api.faultlens.com/v1/otlp',", color: '#93c5fd' },
      { text: "        headers: { 'Authorization' => 'fl_live_3f9a2c4e8b1d7a6e...' }", color: '#93c5fd' },
      { text: '      )', color: '#e2e8f0' },
      { text: '    )', color: '#e2e8f0' },
      { text: '  )', color: '#e2e8f0' },
      { text: 'end', color: '#60a5fa' },
    ],
    raw: `require 'opentelemetry/sdk'
require 'opentelemetry/exporter/otlp'

OpenTelemetry::SDK.configure do |c|
  c.use_all
  c.add_span_processor(
    OpenTelemetry::SDK::Trace::Export::BatchSpanProcessor.new(
      OpenTelemetry::Exporter::OTLP::Exporter.new(
        endpoint: 'https://api.faultlens.com/v1/otlp',
        headers: { 'Authorization' => 'fl_live_3f9a2c4e8b1d7a6e...' }
      )
    )
  )
end`,
  },
};

export default function Step3Verify({
  selectedEnv,
  selectedLang = 'nodejs',
  selectedDeploy,
  selectedSignals,
  onBack,
}) {
  const [activeLang, setActiveLang] = useState(selectedLang || 'nodejs');
  const [copiedKey, setCopiedKey] = useState(null);

  const handleCopy = (key, text) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const codeData = CODE_EXAMPLES[activeLang] || CODE_EXAMPLES.nodejs;

  return (
    <div style={{ maxWidth: 1040, margin: '0 auto', width: '100%', userSelect: 'none' }}>

      {/* Top Header Row with Back Button */}
      <div style={{ display: 'flex', alignItems: 'center', marginBottom: 6 }}>
        <button
          onClick={onBack}
          style={{
            background: 'none',
            border: 'none',
            fontSize: '12.5px',
            fontWeight: 600,
            color: '#475569',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            padding: '2px 4px',
          }}
        >
          ← Back
        </button>
      </div>

      {/* Stepper (01 check, 02 check, 03 active) */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 10 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {/* Step 01 */}
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 3, minWidth: 26 }}>
            <div style={{
              width: 14, height: 14, borderRadius: '50%', background: '#93c5fd',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              color: '#ffffff', fontSize: '9px', fontWeight: 800,
            }}>
              ✓
            </div>
            <span style={{ fontSize: '10px', fontWeight: 700, color: '#2563eb' }}>01</span>
          </div>

          <div style={{ width: 50, height: 1.5, background: '#2563eb', marginBottom: 14 }}/>

          {/* Step 02 */}
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 3, minWidth: 26 }}>
            <div style={{
              width: 14, height: 14, borderRadius: '50%', background: '#93c5fd',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              color: '#ffffff', fontSize: '9px', fontWeight: 800,
            }}>
              ✓
            </div>
            <span style={{ fontSize: '10px', fontWeight: 700, color: '#2563eb' }}>02</span>
          </div>

          <div style={{ width: 50, height: 1.5, background: '#2563eb', marginBottom: 14 }}/>

          {/* Step 03 */}
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 3, minWidth: 26 }}>
            <div style={{
              width: 12, height: 12, borderRadius: '50%', background: '#2563eb',
            }}/>
            <span style={{ fontSize: '10px', fontWeight: 700, color: '#2563eb' }}>03</span>
          </div>
        </div>
      </div>

      {/* Title */}
      <div style={{ textAlign: 'center', marginBottom: 14 }}>
        <h1 style={{
          fontSize: 'clamp(1.7rem, 2.5vw, 2.15rem)',
          fontWeight: 800,
          color: '#0b1f3a',
          letterSpacing: '-0.025em',
          lineHeight: 1.2,
          margin: 0,
        }}>
          You&apos;re almost <span style={{ color: '#2563eb' }}>connected.</span>
        </h1>
        <p style={{ fontSize: '12px', color: '#64748b', marginTop: 4, marginBottom: 0 }}>
          Here&apos;s everything you need to start sending telemetry to FaultLens.
        </p>
      </div>

      {/* ── 2-COLUMN DASHBOARD GRID (Compact) ── */}
      <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr', gap: 14, alignItems: 'start' }}>

        {/* LEFT COLUMN: 1. Connection Details + 2. Add FaultLens */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>

          {/* Card 1: Your connection details */}
          <div style={{
            background: '#ffffff',
            borderRadius: 14,
            padding: '12px 16px',
            border: '1px solid rgba(226, 232, 240, 0.9)',
            boxShadow: '0 4px 18px -2px rgba(15, 23, 42, 0.04)',
          }}>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: 9, marginBottom: 10 }}>
              <div style={{
                width: 20, height: 20, borderRadius: '50%', background: '#2563eb',
                color: '#ffffff', fontSize: '10px', fontWeight: 700,
                display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
              }}>
                1
              </div>
              <div>
                <h3 style={{ fontSize: '13.5px', fontWeight: 700, color: '#0b1f3a', margin: 0 }}>
                  Your connection details
                </h3>
                <p style={{ fontSize: '11px', color: '#64748b', margin: '2px 0 0 0' }}>
                  Use the endpoint and API key below in your OpenTelemetry configuration.
                </p>
              </div>
            </div>

            {/* Inputs Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
              {/* OTLP Endpoint */}
              <div>
                <label style={{ fontSize: '10px', fontWeight: 600, color: '#475569', display: 'block', marginBottom: 3 }}>
                  FaultLens OTLP Endpoint
                </label>
                <div style={{
                  background: '#f8fafc',
                  border: '1px solid #e2e8f0',
                  borderRadius: 7,
                  padding: '5px 8px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  fontFamily: 'monospace',
                  fontSize: '10.5px',
                  color: '#0f172a',
                }}>
                  <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    https://api.faultlens.com/v1/otlp
                  </span>
                  <button
                    onClick={() => handleCopy('endpoint', 'https://api.faultlens.com/v1/otlp')}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: '#2563eb',
                      fontSize: '10px',
                      fontWeight: 600,
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: 3,
                      flexShrink: 0,
                      marginLeft: 4,
                    }}
                  >
                    {copiedKey === 'endpoint' ? '✓ Copied' : '📋 Copy'}
                  </button>
                </div>
              </div>

              {/* API Key */}
              <div>
                <label style={{ fontSize: '10px', fontWeight: 600, color: '#475569', display: 'block', marginBottom: 3 }}>
                  API Key
                </label>
                <div style={{
                  background: '#f8fafc',
                  border: '1px solid #e2e8f0',
                  borderRadius: 7,
                  padding: '5px 8px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  fontFamily: 'monospace',
                  fontSize: '10.5px',
                  color: '#0f172a',
                }}>
                  <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    fl_live_3f9a2c4e8b1d7a6e...
                  </span>
                  <button
                    onClick={() => handleCopy('apikey', 'fl_live_3f9a2c4e8b1d7a6e921bcfae32')}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: '#2563eb',
                      fontSize: '10px',
                      fontWeight: 600,
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      gap: 3,
                      flexShrink: 0,
                      marginLeft: 4,
                    }}
                  >
                    {copiedKey === 'apikey' ? '✓ Copied' : '📋 Copy'}
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* Card 2: Add FaultLens to your application */}
          <div style={{
            background: '#ffffff',
            borderRadius: 14,
            padding: '12px 16px',
            border: '1px solid rgba(226, 232, 240, 0.9)',
            boxShadow: '0 4px 18px -2px rgba(15, 23, 42, 0.04)',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: 9 }}>
                <div style={{
                  width: 20, height: 20, borderRadius: '50%', background: '#2563eb',
                  color: '#ffffff', fontSize: '10px', fontWeight: 700,
                  display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                }}>
                  2
                </div>
                <div>
                  <h3 style={{ fontSize: '13.5px', fontWeight: 700, color: '#0b1f3a', margin: 0 }}>
                    Add FaultLens to your application
                  </h3>
                  <p style={{ fontSize: '11px', color: '#64748b', margin: '2px 0 0 0' }}>
                    Install and configure OpenTelemetry SDK for your {activeLang === 'nodejs' ? 'Node.js' : activeLang} application.
                  </p>
                </div>
              </div>

              {/* Language Pills Switcher */}
              <div style={{ display: 'flex', gap: 3 }}>
                {['nodejs', 'python', 'java', 'go', 'dotnet', 'ruby'].map(langId => {
                  const labels = { nodejs: 'Node.js', python: 'Python', java: 'Java', go: 'Go', dotnet: '.NET', ruby: 'Ruby' };
                  const isActive = activeLang === langId;
                  return (
                    <button
                      key={langId}
                      onClick={() => setActiveLang(langId)}
                      style={{
                        background: isActive ? '#eff6ff' : 'transparent',
                        color: isActive ? '#2563eb' : '#64748b',
                        fontWeight: isActive ? 700 : 500,
                        fontSize: '10.5px',
                        border: isActive ? '1px solid #bfdbfe' : 'none',
                        borderRadius: 9999,
                        padding: '2px 8px',
                        cursor: 'pointer',
                        transition: 'all 0.15s ease',
                      }}
                    >
                      {labels[langId]}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* 1. Install dependencies */}
            <div style={{ marginBottom: 10 }}>
              <p style={{ fontSize: '11px', fontWeight: 600, color: '#334155', margin: '0 0 4px 0' }}>
                1. Install dependencies
              </p>
              <div style={{
                background: '#0f172a',
                color: '#f8fafc',
                borderRadius: 8,
                padding: '7px 10px',
                fontFamily: 'monospace',
                fontSize: '11px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
              }}>
                <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {codeData.install}
                </span>
                <button
                  onClick={() => handleCopy('install', codeData.install)}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: '#94a3b8',
                    cursor: 'pointer',
                    fontSize: '11px',
                    marginLeft: 8,
                    flexShrink: 0,
                  }}
                >
                  {copiedKey === 'install' ? '✓' : '📋'}
                </button>
              </div>
            </div>

            {/* 2. Add configuration */}
            <div style={{ marginBottom: 8 }}>
              <p style={{ fontSize: '10.5px', fontWeight: 600, color: '#334155', margin: '0 0 3px 0' }}>
                2. Add the following configuration
              </p>
              <div style={{
                background: '#0f172a',
                borderRadius: 8,
                padding: '8px 10px',
                fontFamily: 'monospace',
                fontSize: '10.5px',
                lineHeight: 1.4,
                position: 'relative',
              }}>
                <button
                  onClick={() => handleCopy('config', codeData.raw)}
                  style={{
                    position: 'absolute',
                    right: 6,
                    top: 6,
                    background: 'rgba(255,255,255,0.1)',
                    border: 'none',
                    color: '#e2e8f0',
                    borderRadius: 4,
                    padding: '2px 5px',
                    fontSize: '9.5px',
                    cursor: 'pointer',
                  }}
                >
                  {copiedKey === 'config' ? '✓ Copied' : '📋'}
                </button>
                {codeData.lines.map((line, idx) => (
                  <div key={idx} style={{ color: line.color, minHeight: 15, whiteSpace: 'pre' }}>
                    {line.text}
                  </div>
                ))}
              </div>
            </div>

            {/* Card Footer */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderTop: '1px solid #f1f5f9', paddingTop: 6 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                <span style={{ color: '#2563eb', fontSize: '10.5px' }}>ⓘ</span>
                <span style={{ fontSize: '10.5px', color: '#64748b' }}>
                  Minimal configuration. Check out our docs for more options.
                </span>
              </div>
              <a href="#docs" style={{ fontSize: '10.5px', fontWeight: 600, color: '#2563eb' }}>
                View docs →
              </a>
            </div>

          </div>

        </div>

        {/* RIGHT COLUMN: 3. Verify your connection */}
        <div style={{
          background: '#ffffff',
          borderRadius: 14,
          padding: '14px 16px',
          border: '1px solid rgba(226, 232, 240, 0.9)',
          boxShadow: '0 4px 18px -2px rgba(15, 23, 42, 0.04)',
        }}>
          {/* Header */}
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: 9, marginBottom: 14 }}>
            <div style={{
              width: 20, height: 20, borderRadius: '50%', background: '#2563eb',
              color: '#ffffff', fontSize: '10px', fontWeight: 700,
              display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
            }}>
              3
            </div>
            <div>
              <h3 style={{ fontSize: '13.5px', fontWeight: 700, color: '#0b1f3a', margin: 0 }}>
                Verify your connection
              </h3>
              <p style={{ fontSize: '11px', color: '#64748b', margin: '2px 0 0 0', lineHeight: 1.35 }}>
                Once you&apos;ve added the configuration, we&apos;ll automatically detect your telemetry.
              </p>
            </div>
          </div>

          {/* Verification Timeline */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10, position: 'relative' }}>

            {/* Vertical Guide Line */}
            <div style={{
              position: 'absolute',
              left: 13,
              top: 16,
              bottom: 16,
              width: 1,
              background: '#e2e8f0',
              zIndex: 0,
            }}/>

            {/* Step 1: Waiting for telemetry */}
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10, position: 'relative', zIndex: 1 }}>
              {/* Animated blue ring */}
              <div style={{
                width: 26, height: 26, borderRadius: '50%',
                background: '#ffffff',
                border: '2px solid #2563eb',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                flexShrink: 0,
              }}>
                <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#2563eb', opacity: 0.25 }}/>
              </div>
              <div style={{ flex: 1 }}>
                <p style={{ fontSize: '13px', fontWeight: 700, color: '#0b1f3a', margin: 0 }}>
                  Waiting for telemetry...
                </p>
                <p style={{ fontSize: '11px', color: '#64748b', margin: '1px 0 8px 0' }}>
                  Your application will appear here automatically.
                </p>

                {/* Sub items checklist */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6, paddingLeft: 2 }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
                      <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
                        <rect x="1.5" y="9" width="3" height="6" rx="0.5" fill="#2563eb"/>
                        <rect x="6.5" y="5.5" width="3" height="9.5" rx="0.5" fill="#2563eb"/>
                        <rect x="11.5" y="2" width="3" height="13" rx="0.5" fill="#2563eb"/>
                      </svg>
                      <span style={{ fontSize: '11.5px', fontWeight: 600, color: '#334155' }}>Metrics</span>
                    </div>
                    <span style={{ fontSize: '10.5px', color: '#2563eb', fontWeight: 500 }}>
                      ● Waiting...
                    </span>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
                      <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
                        <rect x="2.5" y="1.5" width="11" height="13" rx="1.5" stroke="#2563eb" strokeWidth="1.3"/>
                        <line x1="5" y1="5" x2="11" y2="5" stroke="#2563eb" strokeWidth="1.2"/>
                        <line x1="5" y1="8" x2="11" y2="8" stroke="#2563eb" strokeWidth="1.2"/>
                      </svg>
                      <span style={{ fontSize: '11.5px', fontWeight: 600, color: '#334155' }}>Logs</span>
                    </div>
                    <span style={{ fontSize: '10.5px', color: '#2563eb', fontWeight: 500 }}>
                      ● Waiting...
                    </span>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
                      <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
                        <circle cx="3.5" cy="8" r="2" stroke="#2563eb" strokeWidth="1.3"/>
                        <circle cx="12.5" cy="4" r="2" stroke="#2563eb" strokeWidth="1.3"/>
                        <circle cx="12.5" cy="12" r="2" stroke="#2563eb" strokeWidth="1.3"/>
                        <path d="M5.5 8H8.5Q10.5 8 10.5 5V4" stroke="#2563eb" strokeWidth="1.2" fill="none"/>
                      </svg>
                      <span style={{ fontSize: '11.5px', fontWeight: 600, color: '#334155' }}>Traces</span>
                    </div>
                    <span style={{ fontSize: '10.5px', color: '#2563eb', fontWeight: 500 }}>
                      ● Waiting...
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* Step 2: Discovering services */}
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10, position: 'relative', zIndex: 1 }}>
              <div style={{
                width: 26, height: 26, borderRadius: '50%',
                background: '#f8fafc',
                border: '1px solid #e2e8f0',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                flexShrink: 0,
              }}>
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none">
                  <path d="M12 2L21 7V17L12 22L3 17V7L12 2Z" stroke="#94a3b8" strokeWidth="1.5"/>
                  <path d="M12 2V22M3 7L12 12L21 7" stroke="#94a3b8" strokeWidth="1.3"/>
                </svg>
              </div>
              <div>
                <p style={{ fontSize: '12px', fontWeight: 700, color: '#64748b', margin: 0 }}>
                  Discovering services...
                </p>
                <p style={{ fontSize: '10.5px', color: '#94a3b8', margin: '1px 0 0 0' }}>
                  We&apos;ll identify your services and dependencies.
                </p>
              </div>
            </div>

            {/* Step 3: Finalizing setup */}
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10, position: 'relative', zIndex: 1 }}>
              <div style={{
                width: 26, height: 26, borderRadius: '50%',
                background: '#f8fafc',
                border: '1px solid #e2e8f0',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                flexShrink: 0,
              }}>
                <span style={{ color: '#94a3b8', fontSize: '10px' }}>✓</span>
              </div>
              <div>
                <p style={{ fontSize: '12px', fontWeight: 700, color: '#64748b', margin: 0 }}>
                  Finalizing setup...
                </p>
                <p style={{ fontSize: '10.5px', color: '#94a3b8', margin: '1px 0 0 0' }}>
                  Almost there!
                </p>
              </div>
            </div>

          </div>

        </div>

      </div>

    </div>
  );
}
