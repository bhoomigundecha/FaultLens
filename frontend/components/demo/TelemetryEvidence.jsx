'use client';

/* ── Icon presets ─────────────────────────────────────────────────── */
function MetricIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 16 16" fill="none">
      <rect x="1.5" y="8.5" width="3" height="6.5" rx="0.5" fill="#2563eb"/>
      <rect x="6.5" y="5"   width="3" height="10"  rx="0.5" fill="#2563eb"/>
      <rect x="11.5" y="2"  width="3" height="13"  rx="0.5" fill="#2563eb"/>
    </svg>
  );
}
function LogIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 16 16" fill="none">
      <rect x="2.5" y="1.5" width="11" height="13" rx="1.5" stroke="#7c3aed" strokeWidth="1.3"/>
      <line x1="5" y1="5"  x2="11" y2="5"  stroke="#7c3aed" strokeWidth="1.2"/>
      <line x1="5" y1="8"  x2="11" y2="8"  stroke="#7c3aed" strokeWidth="1.2"/>
      <line x1="5" y1="11" x2="9"  y2="11" stroke="#7c3aed" strokeWidth="1.2"/>
    </svg>
  );
}
function TraceIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 16 16" fill="none">
      <circle cx="3.5"  cy="8" r="2" stroke="#0891b2" strokeWidth="1.3"/>
      <circle cx="12.5" cy="4" r="2" stroke="#0891b2" strokeWidth="1.3"/>
      <circle cx="12.5" cy="12" r="2" stroke="#0891b2" strokeWidth="1.3"/>
      <path d="M5.5 8H8.5Q10.5 8 10.5 5V4" stroke="#0891b2" strokeWidth="1.2" fill="none"/>
    </svg>
  );
}
function DepIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none">
      <circle cx="6"  cy="6"  r="3" stroke="#2563eb" strokeWidth="2"/>
      <circle cx="6"  cy="18" r="3" stroke="#2563eb" strokeWidth="2"/>
      <circle cx="18" cy="12" r="3" stroke="#2563eb" strokeWidth="2"/>
      <path d="M9 6H12C13.66 6 15 7.34 15 9V12" stroke="#2563eb" strokeWidth="1.8"/>
    </svg>
  );
}

/* ── IconBox ─────────────────────────────────────────────────────── */
function IconBox({ bg, border, children }) {
  return (
    <div style={{
      width: 26, height: 26, borderRadius: 8, background: bg,
      border: `1px solid ${border}`, display: 'flex', alignItems: 'center',
      justifyContent: 'center', flexShrink: 0,
    }}>{children}</div>
  );
}

/* ── Check bubble ────────────────────────────────────────────────── */
function Check() {
  return (
    <div style={{
      width: 15, height: 15, borderRadius: '50%', background: '#10b981',
      color: '#fff', fontSize: 9, fontWeight: 800,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      flexShrink: 0, marginTop: 2,
    }}>✓</div>
  );
}

/* ── EvidenceRow ─────────────────────────────────────────────────── */
function EvidenceRow({ icon, iconBg, iconBorder, title, children, graph }) {
  return (
    <div style={{ display: 'flex', alignItems: 'flex-start', gap: 9 }}>
      <Check />
      <IconBox bg={iconBg} border={iconBorder}>{icon}</IconBox>
      <div style={{ flex: 1, minWidth: 0 }}>
        <p style={{ fontSize: 12, fontWeight: 700, color: '#0b1f3a', margin: 0 }}>{title}</p>
        {children}
      </div>
      {graph && <div style={{ flexShrink: 0 }}>{graph}</div>}
    </div>
  );
}

/* ── Rising sparkline ────────────────────────────────────────────── */
function RisingGraph({ color = '#ef4444' }) {
  return (
    <svg width="60" height="22" viewBox="0 0 60 22" fill="none">
      <path d="M0,18 L15,18 L30,17 L42,16 L52,6 L58,4" stroke={color} strokeWidth="1.6" fill="none"/>
      <circle cx="58" cy="4" r="2" fill={color}/>
    </svg>
  );
}

/* ── TelemetryEvidence ───────────────────────────────────────────── */
export default function TelemetryEvidence({ incident }) {
  const metrics = incident?.metric_anomalies ?? [];
  const logs    = incident?.log_anomalies    ?? [];
  const traces  = incident?.trace_anomalies  ?? [];
  const chain   = incident?.causal_path      ?? [];

  // Build evidence items from real data, falling back gracefully
  const hasMetrics = metrics.length > 0;
  const hasLogs    = logs.length    > 0;
  const hasTraces  = traces.length  > 0;
  const hasChain   = chain.length   > 1;

  // Pull first metric anomaly details
  const m0       = metrics[0] ?? {};
  const metricName  = m0.metric_name  ?? m0.name ?? 'metric anomaly';
  const zScore      = m0.z_score != null ? `${m0.z_score.toFixed(1)}σ` : (m0.score ? `${(m0.score * 7).toFixed(1)}σ` : '—');

  // Pull first log anomaly
  const l0         = logs[0] ?? {};
  const logTemplate = l0.template ?? l0.message ?? l0.body ?? '';
  const logCount    = logs.length;

  // Pull first trace anomaly
  const t0           = traces[0] ?? {};
  const traceDesc    = t0.description ?? (t0.callee_id ? `${t0.caller_id} → ${t0.callee_id}` : '');
  const latencyPct   = t0.latency_increase_pct != null ? `↑ ${Math.round(t0.latency_increase_pct)}%` : '';
  const errRate      = t0.error_rate != null ? `Error rate: ${(t0.error_rate * 100).toFixed(0)}%` : '';

  // Causal chain
  const chainText = hasChain ? chain.join(' → ') : '';

  return (
    <div style={{
      background: '#ffffff', borderRadius: 16,
      border: '1px solid rgba(226,232,240,0.95)',
      boxShadow: '0 4px 18px -2px rgba(15,23,42,0.04)',
      padding: '16px 18px', display: 'flex', flexDirection: 'column',
      height: '100%', boxSizing: 'border-box',
    }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 9, marginBottom: 12 }}>
        <div style={{
          width: 24, height: 24, borderRadius: 7, background: '#eff6ff',
          border: '1px solid #dbeafe', display: 'flex', alignItems: 'center',
          justifyContent: 'center',
        }}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
            <path d="M14 2H6C4.9 2 4 2.9 4 4V20C4 21.1 4.9 22 6 22H18C19.1 22 20 21.1 20 20V8L14 2Z"
                  stroke="#2563eb" strokeWidth="1.8"/>
            <path d="M14 2V8H20" stroke="#2563eb" strokeWidth="1.8"/>
            <line x1="8" y1="13" x2="16" y2="13" stroke="#2563eb" strokeWidth="1.6"/>
            <line x1="8" y1="17" x2="13" y2="17" stroke="#2563eb" strokeWidth="1.6"/>
          </svg>
        </div>
        <h3 style={{ fontSize: '13.5px', fontWeight: 700, color: '#0b1f3a', margin: 0 }}>
          Evidence from telemetry
        </h3>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>

        {/* ── 1. Metric anomaly ── */}
        <EvidenceRow
          icon={<MetricIcon />}
          iconBg="#eff6ff" iconBorder="#dbeafe"
          title={hasMetrics ? 'Metric anomaly detected' : 'No metric anomalies'}
          graph={hasMetrics ? <RisingGraph /> : null}
        >
          {hasMetrics ? (
            <>
              <p style={{ fontSize: 10, color: '#475569', margin: '1px 0 0 0', fontFamily: 'monospace' }}>
                {metricName}
              </p>
              <p style={{ fontSize: 10, color: '#64748b', margin: '1px 0 0 0' }}>
                Z-score: {zScore}
              </p>
            </>
          ) : (
            <p style={{ fontSize: 10, color: '#94a3b8', margin: '1px 0 0 0' }}>
              Metrics within normal range
            </p>
          )}
        </EvidenceRow>

        {/* ── 2. Log anomaly ── */}
        <EvidenceRow
          icon={<LogIcon />}
          iconBg="#f5f3ff" iconBorder="#ddd6fe"
          title={hasLogs ? 'Log anomaly detected' : 'No log anomalies'}
        >
          {hasLogs ? (
            <>
              <p style={{ fontSize: '9.5px', color: '#475569', margin: '2px 0 0 0', fontFamily: 'monospace', lineHeight: 1.35 }}>
                <span style={{ color: '#ef4444', fontWeight: 700 }}>ERROR</span>{' '}
                {logTemplate.slice(0, 60)}
              </p>
              {logCount > 1 && (
                <p style={{ fontSize: '9.5px', color: '#64748b', margin: '2px 0 0 0' }}>
                  +{logCount - 1} similar log line{logCount > 2 ? 's' : ''}
                </p>
              )}
            </>
          ) : (
            <p style={{ fontSize: 10, color: '#94a3b8', margin: '1px 0 0 0' }}>Logs look healthy</p>
          )}
        </EvidenceRow>

        {/* ── 3. Trace anomaly ── */}
        <EvidenceRow
          icon={<TraceIcon />}
          iconBg="#ecfeff" iconBorder="#a5f3fc"
          title={hasTraces ? 'Trace anomaly detected' : 'No trace anomalies'}
        >
          {hasTraces ? (
            <>
              {traceDesc && (
                <p style={{ fontSize: 10, color: '#475569', margin: '2px 0 0 0' }}>{traceDesc}</p>
              )}
              {latencyPct && (
                <p style={{ fontSize: 10, color: '#475569', margin: '1px 0 0 0' }}>
                  Latency <span style={{ color: '#ef4444', fontWeight: 700 }}>{latencyPct}</span>
                </p>
              )}
              {errRate && (
                <p style={{ fontSize: 10, color: '#475569', margin: '1px 0 0 0' }}>{errRate}</p>
              )}
            </>
          ) : (
            <p style={{ fontSize: 10, color: '#94a3b8', margin: '1px 0 0 0' }}>Traces look normal</p>
          )}
        </EvidenceRow>

        {/* ── 4. Dependency evidence ── */}
        <EvidenceRow
          icon={<DepIcon />}
          iconBg="#eff6ff" iconBorder="#dbeafe"
          title="Dependency evidence"
        >
          {hasChain ? (
            <>
              <p style={{ fontSize: 10, color: '#0b1f3a', fontWeight: 600, margin: '2px 0 0 0' }}>
                {chainText}
              </p>
              <p style={{ fontSize: 10, color: '#64748b', margin: '1px 0 0 0' }}>
                Error propagation through causal chain
              </p>
            </>
          ) : (
            <p style={{ fontSize: 10, color: '#94a3b8', margin: '2px 0 0 0' }}>
              {incident?.service_id ?? 'Service'} — analysing dependencies
            </p>
          )}
        </EvidenceRow>

        {/* ── 5. Similar incidents ── */}
        <EvidenceRow
          icon={
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none">
              <ellipse cx="12" cy="5" rx="9" ry="3" stroke="#7c3aed" strokeWidth="1.6"/>
              <path d="M3 5V12C3 13.66 7.03 15 12 15C16.97 15 21 13.66 21 12V5" stroke="#7c3aed" strokeWidth="1.6"/>
              <path d="M3 12V19C3 20.66 7.03 22 12 22C16.97 22 21 20.66 21 19V12" stroke="#7c3aed" strokeWidth="1.6"/>
            </svg>
          }
          iconBg="#f5f3ff" iconBorder="#ddd6fe"
          title="Incident history"
        >
          <p style={{ fontSize: 10, color: '#0b1f3a', fontWeight: 600, margin: '2px 0 0 0' }}>
            Failure type: {incident?.failure_type ?? 'analysing…'}
          </p>
          <p style={{ fontSize: 10, color: '#64748b', margin: '1px 0 0 0' }}>
            Env: {incident?.environment_type ?? 'unknown'}
          </p>
        </EvidenceRow>

      </div>
    </div>
  );
}
