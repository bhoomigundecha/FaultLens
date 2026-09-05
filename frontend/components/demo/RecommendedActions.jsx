'use client';

/* ── Extract actionable steps from real incident data ────────────── */
function extractActions(incident) {
  if (!incident) return [];

  // 1. Try ranked_suspects — each suspect may carry remediation steps
  const suspects = incident.ranked_suspects ?? [];
  const fromSuspects = suspects
    .flatMap(s => (typeof s === 'object' ? (s.remediation_steps ?? s.actions ?? []) : []))
    .filter(Boolean);
  if (fromSuspects.length > 0) return fromSuspects.slice(0, 4);

  // 2. Try rca_report — extract the "## 🛠️ What You Can Fix" section
  if (incident.rca_report) {
    const lines = incident.rca_report.split('\n');
    let inActions = false;
    const found = [];
    for (const line of lines) {
      if (/fix|action|remediat|steps|resolution/i.test(line) && line.startsWith('#')) {
        inActions = true;
        continue;
      }
      if (inActions && line.startsWith('#')) break; // next section
      if (inActions) {
        const cleaned = line.replace(/^[\d\.\-\*\s]+/, '').replace(/\*\*/g, '').trim();
        if (cleaned.length > 8) found.push(cleaned);
      }
    }
    if (found.length > 0) return found.slice(0, 4);
  }

  // 3. Built-in fallback actions keyed by failure_type
  const fallbacks = {
    DB_CONNECTION_POOL_EXHAUSTED: [
      'Increase database connection pool size',
      'Check for connection leaks in payment-service',
      'Review recent deployment changes',
    ],
    DB_QUERY_TIMEOUT: [
      'Identify and optimise slow queries',
      'Add or update database indexes',
      'Review recent schema migrations',
    ],
    AI_RATE_LIMIT_EXCEEDED: [
      'Increase API rate limit quota',
      'Add request queuing / backpressure',
      'Implement exponential back-off retries',
    ],
    HIGH_LATENCY_SPIKE: [
      'Check downstream service health',
      'Review recent deployments',
      'Increase timeout thresholds',
    ],
    CASCADE_FAILURE: [
      'Identify the upstream root cause service',
      'Add circuit-breaker patterns between services',
      'Roll back most recent deployment',
    ],
    UPSTREAM_DEPENDENCY_FAILURE: [
      'Restart the failing upstream service',
      'Check service health endpoints',
      'Verify network / DNS resolution',
    ],
    UNHANDLED_EXCEPTION: [
      'Review recent code changes',
      'Check error logs for stack trace',
      'Add error boundary or try-catch',
    ],
  };
  return (fallbacks[incident.failure_type] ?? [
    'Investigate the affected service logs',
    'Check recent deployments',
    'Review service health endpoints',
  ]).slice(0, 4);
}

/* ── ActionCard ──────────────────────────────────────────────────── */
function ActionCard({ number, text }) {
  return (
    <div style={{
      background: '#f8fafc', border: '1px solid #e2e8f0',
      borderRadius: 12, padding: '8px 12px',
      display: 'flex', alignItems: 'flex-start', gap: 9,
      flex: 1, minWidth: 0,
    }}>
      <div style={{
        width: 20, height: 20, borderRadius: '50%',
        background: '#eff6ff', border: '1px solid #bfdbfe',
        color: '#2563eb', fontSize: '9.5px', fontWeight: 800,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        flexShrink: 0, marginTop: 1,
      }}>
        {String(number).padStart(2, '0')}
      </div>
      <p style={{
        fontSize: 11, fontWeight: 600, color: '#0b1f3a',
        margin: 0, overflow: 'hidden',
        display: '-webkit-box', WebkitLineClamp: 2,
        WebkitBoxOrient: 'vertical',
      }}>
        {text}
      </p>
    </div>
  );
}

/* ── RecommendedActions ──────────────────────────────────────────── */
export default function RecommendedActions({ incident }) {
  const actions = extractActions(incident);

  return (
    <div style={{
      background: '#ffffff', borderRadius: 16,
      border: '1px solid rgba(226,232,240,0.95)',
      boxShadow: '0 4px 18px -2px rgba(15,23,42,0.04)',
      padding: '14px 18px', marginTop: 16,
      display: 'flex', alignItems: 'center', gap: 14,
    }}>
      {/* Label */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0, paddingRight: 4 }}>
        <div style={{
          width: 24, height: 24, borderRadius: 7, background: '#eff6ff',
          border: '1px solid #dbeafe', display: 'flex', alignItems: 'center',
          justifyContent: 'center',
        }}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
            <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"
                  stroke="#2563eb" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </div>
        <span style={{ fontSize: '12.5px', fontWeight: 700, color: '#0b1f3a', whiteSpace: 'nowrap' }}>
          Recommended actions
        </span>
      </div>

      {/* Action cards */}
      <div style={{ display: 'flex', alignItems: 'stretch', gap: 10, flex: 1, minWidth: 0 }}>
        {actions.length === 0 ? (
          <p style={{ fontSize: 12, color: '#94a3b8', margin: 0, paddingTop: 4 }}>
            Generating recommendations…
          </p>
        ) : (
          actions.map((text, i) => (
            <ActionCard key={i} number={i + 1} text={text} />
          ))
        )}
      </div>

      {/* View full RCA */}
      {incident?.rca_report && (
        <button
          onClick={() => {
            const w = window.open('', '_blank');
            w.document.write(
              `<pre style="font-family:system-ui;padding:24px;max-width:800px;white-space:pre-wrap">${
                incident.rca_report
              }</pre>`
            );
          }}
          style={{
            background: '#0b1f3a', color: '#fff',
            borderRadius: 9999, padding: '8px 18px',
            fontSize: '11.5px', fontWeight: 600,
            border: 'none', cursor: 'pointer',
            whiteSpace: 'nowrap', flexShrink: 0,
          }}
          onMouseEnter={e => (e.currentTarget.style.background = '#162d50')}
          onMouseLeave={e => (e.currentTarget.style.background = '#0b1f3a')}
        >
          View full RCA →
        </button>
      )}
    </div>
  );
}
