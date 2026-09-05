'use client';

const CARD = {
  background: '#ffffff',
  borderRadius: 14,
  border: '1px solid rgba(219, 234, 254, 0.8)',
  boxShadow: '0 4px 20px rgba(37, 99, 235, 0.08), 0 1px 4px rgba(0, 0, 0, 0.04)',
};

export default function ClearAnswersPanel() {
  return (
    <div className="anim-slide-r" style={{ position: 'relative', width: '100%' }}>

      {/* Header Pill */}
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', marginBottom: 14 }}>
        <span style={{
          background: 'rgba(219, 234, 254, 0.75)',
          color: '#2563eb',
          borderRadius: 9999,
          padding: '4px 14px',
          fontSize: '10px',
          fontWeight: 700,
          letterSpacing: '0.08em',
          border: '1px solid rgba(191, 219, 254, 0.8)',
        }}>
          CLEAR ANSWERS
        </span>
        <span style={{ fontSize: '11px', color: '#64748b', marginTop: 4 }}>
          Root cause, context and next steps.
        </span>
      </div>

      {/* 4 Cards */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>

        {/* 1 — Root Cause Identified */}
        <div style={{ ...CARD, padding: '14px 18px' }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 8 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              {/* Green checkmark circle */}
              <div style={{
                width: 26, height: 26, borderRadius: '50%', background: '#dcfce7',
                border: '1.5px solid #86efac',
                display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
              }}>
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                  <path d="M3 7L6 10L11 4" stroke="#16a34a" strokeWidth="2"
                        strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </div>
              <div>
                <p style={{ fontSize: '13px', fontWeight: 700, color: '#0b1f3a', margin: 0, lineHeight: 1.2 }}>
                  Root Cause Identified
                </p>
                <p style={{ fontSize: '10.5px', color: '#64748b', fontFamily: 'monospace', marginTop: 3, marginBottom: 0 }}>
                  DB_CONNECTION_POOL_EXHAUSTED
                </p>
              </div>
            </div>

            {/* Confidence Badge */}
            <span style={{
              padding: '3px 10px', borderRadius: 9999, flexShrink: 0,
              background: '#dcfce7', border: '1px solid #bbf7d0',
              fontSize: '10.5px', fontWeight: 700, color: '#16a34a', whiteSpace: 'nowrap',
            }}>
              Confidence: 92%
            </span>
          </div>

          {/* Microservice Architecture Chain */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginTop: 16,
            padding: '0 4px',
          }}>
            {/* api-gateway */}
            <ServiceNode icon="globe" label="api-gateway" highlight={false} />
            <Arrow />

            {/* order-service */}
            <ServiceNode icon="cube" label="order-service" highlight={false} />
            <Arrow />

            {/* payment-service (with red alert exclamation) */}
            <ServiceNode icon="cube-alert" label="payment-service" highlight={true} />
            <Arrow />

            {/* database */}
            <ServiceNode icon="db" label="database" highlight={false} />
          </div>
        </div>

        {/* 2 — Failure Triage */}
        <div style={{ ...CARD, padding: '12px 16px' }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
            <div style={{
              width: 26, height: 26, borderRadius: 8, background: '#eff6ff',
              border: '1px solid #bfdbfe',
              display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
            }}>
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                <rect x="2" y="1.5" width="10" height="11" rx="1.5" stroke="#2563eb" strokeWidth="1.2"/>
                <line x1="4.5" y1="4.5" x2="9.5" y2="4.5" stroke="#2563eb" strokeWidth="1"/>
                <line x1="4.5" y1="7"   x2="9.5" y2="7"   stroke="#2563eb" strokeWidth="1"/>
                <line x1="4.5" y1="9.5" x2="7.5" y2="9.5" stroke="#2563eb" strokeWidth="1"/>
              </svg>
            </div>
            <div>
              <p style={{ fontSize: '13px', fontWeight: 700, color: '#0b1f3a', margin: 0 }}>
                Failure Triage
              </p>
              <p style={{ fontSize: '11px', color: '#334155', margin: '3px 0 0 0', lineHeight: 1.4 }}>
                Classified as DB connection pool exhaustion
              </p>
              <p style={{ fontSize: '10.5px', color: '#64748b', margin: '2px 0 0 0', lineHeight: 1.4 }}>
                Routed to Backend Engineering Team
              </p>
            </div>
          </div>
        </div>

        {/* 3 — Causal Chain */}
        <div style={{ ...CARD, padding: '12px 16px' }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
            <div style={{
              width: 26, height: 26, borderRadius: 8, background: '#eff6ff',
              border: '1px solid #bfdbfe',
              display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
            }}>
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                <circle cx="3" cy="7" r="1.8" stroke="#2563eb" strokeWidth="1.2"/>
                <circle cx="11" cy="3.5" r="1.8" stroke="#2563eb" strokeWidth="1.2"/>
                <circle cx="11" cy="10.5" r="1.8" stroke="#2563eb" strokeWidth="1.2"/>
                <path d="M4.8 7 H7.5 Q9 7 9 4.5 V3.5" stroke="#2563eb" strokeWidth="1.1" fill="none"/>
                <path d="M7.5 7 Q9 7 9 9.5 V10.5" stroke="#2563eb" strokeWidth="1.1" fill="none"/>
              </svg>
            </div>
            <div>
              <p style={{ fontSize: '13px', fontWeight: 700, color: '#0b1f3a', margin: 0 }}>
                Causal Chain
              </p>
              <p style={{ fontSize: '11px', color: '#334155', margin: '4px 0 0 0' }}>
                api-gateway → order-service → payment-service → database
              </p>
            </div>
          </div>
        </div>

        {/* 4 — Recommended Actions */}
        <div style={{ ...CARD, padding: '12px 16px' }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
            <div style={{
              width: 26, height: 26, borderRadius: 8, background: '#ecfeff',
              border: '1px solid #a5f3fc',
              display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
            }}>
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                <path d="M10 2.5C11.5 1.5 13 2 13 3.5C13 4.5 12 5.5 11 6L9.5 7.5L6.5 4.5L8 3C8.5 2.5 9 3 10 2.5Z"
                      stroke="#0891b2" strokeWidth="1.2" fill="none" strokeLinejoin="round"/>
                <path d="M6.5 4.5L3 8C2.5 8.5 2.5 9.5 3 10.5C3.5 11.5 4.5 11.5 5.5 11L9 7.5"
                      stroke="#0891b2" strokeWidth="1.2" fill="none" strokeLinecap="round"/>
              </svg>
            </div>
            <div>
              <p style={{ fontSize: '13px', fontWeight: 700, color: '#0b1f3a', margin: 0 }}>
                Recommended Actions
              </p>
              <ol style={{ margin: '5px 0 0 0', paddingLeft: 18, fontSize: '11px', color: '#334155', lineHeight: 1.6 }}>
                <li>Increase DB connection pool size</li>
                <li>Check for connection leaks in payment-service</li>
                <li>Review recent deployment</li>
              </ol>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}

/* ── Microservice Node in Service Chain ── */
function ServiceNode({ icon, label, highlight }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4, flexShrink: 0 }}>
      <div style={{
        position: 'relative',
        width: 38, height: 38, borderRadius: '50%',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        background: highlight ? '#fee2e2' : '#f1f5f9',
        border: `1.5px solid ${highlight ? '#fca5a5' : '#e2e8f0'}`,
        boxShadow: highlight ? '0 0 12px rgba(239, 68, 68, 0.25)' : 'none',
      }}>
        {/* If alert node, show red exclamation badge */}
        {highlight && (
          <span style={{
            position: 'absolute',
            top: -2, right: -2,
            width: 13, height: 13, borderRadius: '50%',
            background: '#ef4444', color: '#ffffff',
            fontSize: '9px', fontWeight: 800,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            boxShadow: '0 0 4px rgba(239, 68, 68, 0.8)',
          }}>
            !
          </span>
        )}

        {/* Node SVG Icons */}
        {icon === 'globe' && (
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
            <circle cx="9" cy="9" r="7" stroke="#475569" strokeWidth="1.2"/>
            <ellipse cx="9" cy="9" rx="3" ry="7" stroke="#475569" strokeWidth="1"/>
            <line x1="2" y1="9" x2="16" y2="9" stroke="#475569" strokeWidth="1"/>
          </svg>
        )}

        {icon === 'cube' && (
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
            <path d="M9 2L15 5.5V12.5L9 16L3 12.5V5.5L9 2Z" stroke="#475569" strokeWidth="1.2" strokeLinejoin="round"/>
            <path d="M9 2V16M3 5.5L9 9L15 5.5" stroke="#475569" strokeWidth="1" strokeLinejoin="round"/>
          </svg>
        )}

        {icon === 'cube-alert' && (
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
            <path d="M9 2L15 5.5V12.5L9 16L3 12.5V5.5L9 2Z" stroke="#ef4444" strokeWidth="1.3" strokeLinejoin="round"/>
            <path d="M9 2V16M3 5.5L9 9L15 5.5" stroke="#ef4444" strokeWidth="1.1" strokeLinejoin="round"/>
          </svg>
        )}

        {icon === 'db' && (
          <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
            <ellipse cx="9" cy="4.5" rx="6" ry="2.2" stroke="#8b5cf6" strokeWidth="1.2" fill="#ede9fe"/>
            <path d="M3 4.5 V9.5 C3 10.7 5.7 11.7 9 11.7 C12.3 11.7 15 10.7 15 9.5 V4.5" stroke="#8b5cf6" strokeWidth="1.2"/>
            <path d="M3 9.5 V13.5 C3 14.7 5.7 15.7 9 15.7 C12.3 15.7 15 14.7 15 13.5 V9.5" stroke="#8b5cf6" strokeWidth="1.2"/>
          </svg>
        )}
      </div>

      <span style={{
        fontSize: '9.5px',
        fontWeight: highlight ? 700 : 500,
        color: highlight ? '#ef4444' : '#475569',
        textAlign: 'center',
      }}>
        {label}
      </span>
    </div>
  );
}

function Arrow() {
  return (
    <div style={{ display: 'flex', alignItems: 'center', paddingBottom: 16 }}>
      <svg width="18" height="10" viewBox="0 0 18 10" fill="none">
        <line x1="1" y1="5" x2="14" y2="5" stroke="#a5b4fc" strokeWidth="1.4"/>
        <path d="M12 2L15.5 5L12 8" stroke="#a5b4fc" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/>
      </svg>
    </div>
  );
}
