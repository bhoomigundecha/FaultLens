const CARD = {
  background: '#ffffff',
  borderRadius: 14,
  border: '1px solid rgba(147,197,253,0.35)',
  boxShadow: '0 4px 20px rgba(37,99,235,0.08), 0 1px 4px rgba(0,0,0,0.05)',
};

export default function ClearAnswersPanel() {
  return (
    <div className="anim-slide-r" style={{ position: 'relative', height: '100%', display: 'flex', flexDirection: 'column' }}>

      {/* Panel header */}
      <div style={{ marginBottom: 10 }}>
        <p style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.18em', textTransform: 'uppercase', color: '#2563eb' }}>
          Clear Answers
        </p>
        <p style={{ fontSize: 11, color: '#9ca3af', marginTop: 3 }}>Root cause, context and next steps.</p>
      </div>

      {/* Cards */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>

        {/* 1 — Root Cause */}
        <div className="anim-fade-up d2" style={{ ...CARD, padding: '12px 14px' }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 8 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              {/* Green check */}
              <div style={{ width: 26, height: 26, borderRadius: '50%', background: '#dcfce7',
                            display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
                  <path d="M2.5 6.5L5.5 9.5L10.5 3.5" stroke="#22c55e" strokeWidth="1.8"
                        strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </div>
              <div>
                <p style={{ fontSize: 13, fontWeight: 700, color: '#0b1f3a', lineHeight: 1.3 }}>Root Cause Identified</p>
                <p style={{ fontSize: 10, color: '#9ca3af', fontFamily: 'monospace', marginTop: 2 }}>DB_CONNECTION_POOL_EXHAUSTED</p>
              </div>
            </div>
            <span style={{
              padding: '3px 9px', borderRadius: 100, flexShrink: 0,
              background: '#f0fdf4', border: '1px solid #bbf7d0',
              fontSize: 10, fontWeight: 700, color: '#16a34a', whiteSpace: 'nowrap',
            }}>
              Confidence: 92%
            </span>
          </div>

          {/* Service chain */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 12 }}>
            <ServiceNode icon="globe"     label="api-gateway"     highlight={false}/>
            <Arrow/>
            <ServiceNode icon="box"       label="order-service"   highlight={false}/>
            <Arrow/>
            <ServiceNode icon="box-alert" label="payment-service" highlight={true}/>
            <Arrow/>
            <ServiceNode icon="db"        label="database"        highlight={false}/>
          </div>
        </div>

        {/* 2 — Failure Triage */}
        <div className="anim-fade-up d3" style={{ ...CARD, padding: '10px 14px' }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
            <SmallIcon bg="#eff6ff">
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                <rect x="1" y="1" width="10" height="10" rx="1.5" stroke="#2563eb" strokeWidth="1.1"/>
                <line x1="3" y1="4.5" x2="9" y2="4.5" stroke="#2563eb" strokeWidth="0.9"/>
                <line x1="3" y1="6.5" x2="9" y2="6.5" stroke="#2563eb" strokeWidth="0.9"/>
                <line x1="3" y1="8.5" x2="6" y2="8.5" stroke="#2563eb" strokeWidth="0.9"/>
              </svg>
            </SmallIcon>
            <div>
              <p style={{ fontSize: 12.5, fontWeight: 700, color: '#0b1f3a' }}>Failure Triage</p>
              <p style={{ fontSize: 11, color: '#6b7280', lineHeight: 1.55, marginTop: 2 }}>
                Classified as DB connection pool exhaustion<br/>
                Routed to Backend Engineering Team
              </p>
            </div>
          </div>
        </div>

        {/* 3 — Causal Chain */}
        <div className="anim-fade-up d4" style={{ ...CARD, padding: '10px 14px' }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
            <SmallIcon bg="#f5f3ff">
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                <circle cx="2"  cy="6" r="1.5" stroke="#8b5cf6" strokeWidth="1"/>
                <circle cx="10" cy="6" r="1.5" stroke="#8b5cf6" strokeWidth="1"/>
                <path d="M3.5 6 Q6 2.5 8.5 6" stroke="#8b5cf6" strokeWidth="1" fill="none" strokeLinecap="round"/>
                <path d="M3.5 6 Q6 9.5 8.5 6" stroke="#8b5cf6" strokeWidth="1" fill="none" strokeLinecap="round" strokeDasharray="1.5 1.2"/>
              </svg>
            </SmallIcon>
            <div>
              <p style={{ fontSize: 12.5, fontWeight: 700, color: '#0b1f3a' }}>Causal Chain</p>
              <p style={{ fontSize: 10.5, color: '#9ca3af', fontFamily: 'monospace', lineHeight: 1.6, marginTop: 2 }}>
                api-gateway → order-service → payment-service → database
              </p>
            </div>
          </div>
        </div>

        {/* 4 — Recommended Actions */}
        <div className="anim-fade-up d5" style={{ ...CARD, padding: '10px 14px' }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
            <SmallIcon bg="#fffbeb">
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                <path d="M8 2C9 1 11 1 11 3C11 4.5 9.5 5 8.5 6L7 7.5L4.5 5L6 3.5C6.5 3 7.5 2.5 8 2Z"
                      stroke="#f59e0b" strokeWidth="1" fill="none" strokeLinejoin="round"/>
                <path d="M4.5 5L2.5 7C2 7.5 2 8.5 3 9C4 9.5 5 9 5 8L7 7.5"
                      stroke="#f59e0b" strokeWidth="1" fill="none" strokeLinecap="round"/>
              </svg>
            </SmallIcon>
            <div>
              <p style={{ fontSize: 12.5, fontWeight: 700, color: '#0b1f3a', marginBottom: 5 }}>Recommended Actions</p>
              {[
                'Increase DB connection pool size',
                'Check for connection leaks in payment-service',
                'Review recent deployment',
              ].map((a, i) => (
                <div key={i} style={{ display: 'flex', gap: 6, marginBottom: 3 }}>
                  <span style={{ fontSize: 11, fontWeight: 700, color: '#2563eb', flexShrink: 0 }}>{i+1}.</span>
                  <span style={{ fontSize: 11, color: '#6b7280', lineHeight: 1.5 }}>{a}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ── Helpers ── */
function SmallIcon({ bg, children }) {
  return (
    <div style={{ width: 22, height: 22, borderRadius: 6, background: bg, flexShrink: 0,
                  display: 'flex', alignItems: 'center', justifyContent: 'center', marginTop: 1 }}>
      {children}
    </div>
  );
}

function ServiceNode({ icon, label, highlight }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4, flexShrink: 0 }}>
      <div style={{
        width: 34, height: 34, borderRadius: 10, display: 'flex', alignItems: 'center', justifyContent: 'center',
        border: `2px solid ${highlight ? '#fca5a5' : '#e5e7eb'}`,
        background: highlight ? '#fef2f2' : '#f9fafb',
        boxShadow: highlight ? '0 0 10px rgba(239,68,68,0.25)' : 'none',
      }}>
        <NodeIcon type={icon} highlight={highlight}/>
      </div>
      <span style={{ fontSize: 8.5, fontWeight: highlight ? 700 : 500,
                     color: highlight ? '#ef4444' : '#6b7280', textAlign: 'center', lineHeight: 1.3 }}>
        {label}
      </span>
    </div>
  );
}

function Arrow() {
  return (
    <div style={{ display: 'flex', alignItems: 'center', paddingBottom: 18, flexShrink: 0 }}>
      <svg width="16" height="8" viewBox="0 0 16 8" fill="none">
        <line x1="0" y1="4" x2="11" y2="4" stroke="#d1d5db" strokeWidth="1.4"/>
        <path d="M9 1.5L13 4L9 6.5" stroke="#d1d5db" strokeWidth="1.4"
              strokeLinecap="round" strokeLinejoin="round" fill="none"/>
      </svg>
    </div>
  );
}

function NodeIcon({ type, highlight }) {
  const c = highlight ? '#ef4444' : '#9ca3af';
  if (type === 'globe') return (
    <svg width="15" height="15" viewBox="0 0 15 15" fill="none">
      <circle cx="7.5" cy="7.5" r="6" stroke={c} strokeWidth="1.2"/>
      <ellipse cx="7.5" cy="7.5" rx="2.8" ry="6" stroke={c} strokeWidth="1"/>
      <line x1="1.5" y1="7.5" x2="13.5" y2="7.5" stroke={c} strokeWidth="1"/>
    </svg>
  );
  if (type === 'box' || type === 'box-alert') return (
    <svg width="15" height="15" viewBox="0 0 15 15" fill="none">
      <path d="M7.5 2L13 5.5V9.5L7.5 13L2 9.5V5.5L7.5 2Z"
            stroke={c} strokeWidth="1.2" strokeLinejoin="round"/>
      {type === 'box-alert' && <circle cx="12.5" cy="3.5" r="2.8" fill="#ef4444"/>}
      {type === 'box-alert' && (
        <text x="12.5" y="4.8" textAnchor="middle" fontSize="3.8" fill="white" fontWeight="bold">!</text>
      )}
    </svg>
  );
  if (type === 'db') return (
    <svg width="15" height="15" viewBox="0 0 15 15" fill="none">
      <ellipse cx="7.5" cy="4.2" rx="5" ry="2" stroke={c} strokeWidth="1.2"/>
      <path d="M2.5 4.2V11C2.5 12.1 4.8 13 7.5 13C10.2 13 12.5 12.1 12.5 11V4.2"
            stroke={c} strokeWidth="1.2"/>
      <path d="M2.5 7.6C2.5 8.7 4.8 9.6 7.5 9.6C10.2 9.6 12.5 8.7 12.5 7.6"
            stroke={c} strokeWidth="1" strokeDasharray="2 1.5"/>
    </svg>
  );
  return null;
}
