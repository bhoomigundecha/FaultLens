'use client';

export default function TelemetryEvidence() {
  return (
    <div style={{
      background: '#ffffff',
      borderRadius: 16,
      border: '1px solid rgba(226, 232, 240, 0.95)',
      boxShadow: '0 4px 18px -2px rgba(15, 23, 42, 0.04)',
      padding: '16px 18px',
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      boxSizing: 'border-box',
    }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 9, marginBottom: 12 }}>
        <div style={{
          width: 24,
          height: 24,
          borderRadius: 7,
          background: '#eff6ff',
          border: '1px solid #dbeafe',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#2563eb',
        }}>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
            <path d="M14 2H6C4.89543 2 4 2.89543 4 4V20C4 21.1046 4.89543 22 6 22H18C19.1046 22 20 21.1046 20 20V8L14 2Z" stroke="#2563eb" strokeWidth="1.8"/>
            <path d="M14 2V8H20" stroke="#2563eb" strokeWidth="1.8"/>
            <line x1="8" y1="13" x2="16" y2="13" stroke="#2563eb" strokeWidth="1.6"/>
            <line x1="8" y1="17" x2="13" y2="17" stroke="#2563eb" strokeWidth="1.6"/>
          </svg>
        </div>
        <h3 style={{ fontSize: '13.5px', fontWeight: 700, color: '#0b1f3a', margin: 0 }}>
          Evidence from telemetry
        </h3>
      </div>

      {/* 5 Evidence items */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>

        {/* 1. Metric anomaly */}
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: 9 }}>
          <div style={{
            width: 15, height: 15, borderRadius: '50%', background: '#10b981',
            color: '#ffffff', fontSize: '9px', fontWeight: 800,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            flexShrink: 0, marginTop: 2,
          }}>
            ✓
          </div>

          <div style={{
            width: 26, height: 26, borderRadius: 8, background: '#eff6ff',
            border: '1px solid #dbeafe', display: 'flex', alignItems: 'center', justifyContent: 'center',
            flexShrink: 0, color: '#2563eb',
          }}>
            <svg width="13" height="13" viewBox="0 0 16 16" fill="none">
              <rect x="1.5" y="8.5" width="3" height="6.5" rx="0.5" fill="#2563eb"/>
              <rect x="6.5" y="5" width="3" height="10" rx="0.5" fill="#2563eb"/>
              <rect x="11.5" y="2" width="3" height="13" rx="0.5" fill="#2563eb"/>
            </svg>
          </div>

          <div style={{ flex: 1, minWidth: 0 }}>
            <p style={{ fontSize: '12px', fontWeight: 700, color: '#0b1f3a', margin: 0 }}>
              Metric anomaly detected
            </p>
            <p style={{ fontSize: '10px', color: '#475569', margin: '1px 0 0 0', fontFamily: 'monospace' }}>
              db.connections.active
            </p>
            <p style={{ fontSize: '10px', color: '#64748b', margin: '1px 0 0 0' }}>
              Z-score: 5.2σ
            </p>
          </div>

          {/* Anomaly rising graph */}
          <div style={{ flexShrink: 0 }}>
            <svg width="60" height="22" viewBox="0 0 60 22" fill="none">
              <path d="M0,18 L15,18 L30,17 L42,16 L52,6 L58,4" stroke="#ef4444" strokeWidth="1.6" fill="none"/>
              <circle cx="58" cy="4" r="2" fill="#ef4444"/>
            </svg>
          </div>
        </div>

        {/* 2. Log anomaly */}
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: 9 }}>
          <div style={{
            width: 15, height: 15, borderRadius: '50%', background: '#10b981',
            color: '#ffffff', fontSize: '9px', fontWeight: 800,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            flexShrink: 0, marginTop: 2,
          }}>
            ✓
          </div>

          <div style={{
            width: 26, height: 26, borderRadius: 8, background: '#f5f3ff',
            border: '1px solid #ddd6fe', display: 'flex', alignItems: 'center', justifyContent: 'center',
            flexShrink: 0, color: '#7c3aed',
          }}>
            <svg width="13" height="13" viewBox="0 0 16 16" fill="none">
              <rect x="2.5" y="1.5" width="11" height="13" rx="1.5" stroke="#7c3aed" strokeWidth="1.3"/>
              <line x1="5" y1="5" x2="11" y2="5" stroke="#7c3aed" strokeWidth="1.2"/>
              <line x1="5" y1="8" x2="11" y2="8" stroke="#7c3aed" strokeWidth="1.2"/>
            </svg>
          </div>

          <div style={{ flex: 1, minWidth: 0 }}>
            <p style={{ fontSize: '12px', fontWeight: 700, color: '#0b1f3a', margin: 0 }}>
              Log anomaly detected
            </p>
            <p style={{ fontSize: '9.5px', color: '#475569', margin: '2px 0 0 0', fontFamily: 'monospace', lineHeight: 1.35 }}>
              <span style={{ color: '#ef4444', fontWeight: 700 }}>ERROR</span> [pool] Connection pool exhausted
            </p>
            <p style={{ fontSize: '9.5px', color: '#475569', margin: '1px 0 0 0', fontFamily: 'monospace', lineHeight: 1.35 }}>
              <span style={{ color: '#ef4444', fontWeight: 700 }}>ERROR</span> [db] Unable to acquire connection
            </p>
            <p style={{ fontSize: '9.5px', color: '#64748b', margin: '2px 0 0 0' }}>
              +12 similar log lines
            </p>
          </div>
        </div>

        {/* 3. Trace anomaly */}
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: 9 }}>
          <div style={{
            width: 15, height: 15, borderRadius: '50%', background: '#10b981',
            color: '#ffffff', fontSize: '9px', fontWeight: 800,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            flexShrink: 0, marginTop: 2,
          }}>
            ✓
          </div>

          <div style={{
            width: 26, height: 26, borderRadius: 8, background: '#ecfeff',
            border: '1px solid #a5f3fc', display: 'flex', alignItems: 'center', justifyContent: 'center',
            flexShrink: 0, color: '#0891b2',
          }}>
            <svg width="13" height="13" viewBox="0 0 16 16" fill="none">
              <circle cx="3.5" cy="8" r="2" stroke="#0891b2" strokeWidth="1.3"/>
              <circle cx="12.5" cy="4" r="2" stroke="#0891b2" strokeWidth="1.3"/>
              <circle cx="12.5" cy="12" r="2" stroke="#0891b2" strokeWidth="1.3"/>
              <path d="M5.5 8H8.5Q10.5 8 10.5 5V4" stroke="#0891b2" strokeWidth="1.2" fill="none"/>
            </svg>
          </div>

          <div style={{ flex: 1, minWidth: 0 }}>
            <p style={{ fontSize: '12px', fontWeight: 700, color: '#0b1f3a', margin: 0 }}>
              Trace anomaly detected
            </p>
            <p style={{ fontSize: '10px', color: '#475569', margin: '2px 0 0 0' }}>
              payment-service latency <span style={{ color: '#ef4444', fontWeight: 700 }}>↑ 488%</span>
            </p>
            <p style={{ fontSize: '10px', color: '#475569', margin: '1px 0 0 0' }}>
              Error rate: <span style={{ color: '#ef4444', fontWeight: 700 }}>32% → 89%</span>
            </p>
          </div>
        </div>

        {/* 4. Dependency evidence */}
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: 9 }}>
          <div style={{
            width: 15, height: 15, borderRadius: '50%', background: '#10b981',
            color: '#ffffff', fontSize: '9px', fontWeight: 800,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            flexShrink: 0, marginTop: 2,
          }}>
            ✓
          </div>

          <div style={{
            width: 26, height: 26, borderRadius: 8, background: '#eff6ff',
            border: '1px solid #dbeafe', display: 'flex', alignItems: 'center', justifyContent: 'center',
            flexShrink: 0, color: '#2563eb',
          }}>
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none">
              <circle cx="6" cy="6" r="3" stroke="#2563eb" strokeWidth="2"/>
              <circle cx="6" cy="18" r="3" stroke="#2563eb" strokeWidth="2"/>
              <circle cx="18" cy="12" r="3" stroke="#2563eb" strokeWidth="2"/>
              <path d="M9 6H12C13.6569 6 15 7.34315 15 9V12" stroke="#2563eb" strokeWidth="1.8"/>
            </svg>
          </div>

          <div style={{ flex: 1, minWidth: 0 }}>
            <p style={{ fontSize: '12px', fontWeight: 700, color: '#0b1f3a', margin: 0 }}>
              Dependency evidence
            </p>
            <p style={{ fontSize: '10px', color: '#0b1f3a', fontWeight: 600, margin: '2px 0 0 0' }}>
              payment-service → database
            </p>
            <p style={{ fontSize: '10px', color: '#64748b', margin: '1px 0 0 0' }}>
              Error propagation in 95% of traces
            </p>
          </div>
        </div>

        {/* 5. Similar incidents */}
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: 9 }}>
          <div style={{
            width: 15, height: 15, borderRadius: '50%', background: '#10b981',
            color: '#ffffff', fontSize: '9px', fontWeight: 800,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            flexShrink: 0, marginTop: 2,
          }}>
            ✓
          </div>

          <div style={{
            width: 26, height: 26, borderRadius: 8, background: '#f5f3ff',
            border: '1px solid #ddd6fe', display: 'flex', alignItems: 'center', justifyContent: 'center',
            flexShrink: 0, color: '#7c3aed',
          }}>
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none">
              <ellipse cx="12" cy="5" rx="9" ry="3" stroke="#7c3aed" strokeWidth="1.6"/>
              <path d="M3 5V12C3 13.66 7.03 15 12 15C16.97 15 21 13.66 21 12V5" stroke="#7c3aed" strokeWidth="1.6"/>
              <path d="M3 12V19C3 20.66 7.03 22 12 22C16.97 22 21 20.66 21 19V12" stroke="#7c3aed" strokeWidth="1.6"/>
            </svg>
          </div>

          <div style={{ flex: 1, minWidth: 0 }}>
            <p style={{ fontSize: '12px', fontWeight: 700, color: '#0b1f3a', margin: 0 }}>
              Similar incidents
            </p>
            <p style={{ fontSize: '10px', color: '#0b1f3a', fontWeight: 600, margin: '2px 0 0 0' }}>
              3 previous incidents matched
            </p>
            <p style={{ fontSize: '10px', color: '#64748b', margin: '1px 0 0 0' }}>
              Last seen 2 weeks ago
            </p>
          </div>
        </div>

      </div>
    </div>
  );
}
