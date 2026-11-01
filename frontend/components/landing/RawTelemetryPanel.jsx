'use client';

const CARD = {
  background: '#ffffff',
  borderRadius: 14,
  border: '1px solid rgba(219, 234, 254, 0.8)',
  boxShadow: '0 4px 20px rgba(37, 99, 235, 0.08), 0 1px 4px rgba(0, 0, 0, 0.04)',
};

export default function RawTelemetryPanel() {
  return (
    <div className="anim-slide-l" style={{ position: 'relative', width: '100%' }}>
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
          RAW TELEMETRY
        </span>
        <span style={{ fontSize: '11px', color: '#64748b', marginTop: 4 }}>
          Thousands of signals from your system.
        </span>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        <div style={{ ...CARD, padding: '12px 16px' }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
            <div style={{
              width: 26, height: 26, borderRadius: 8, background: '#fef3c7',
              border: '1px solid #fde68a',
              display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
            }}>
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                <path d="M2 7H5L7 3L9 11L11 7H12" stroke="#d97706" strokeWidth="1.5"
                      strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </div>
            <div style={{ flex: 1 }}>
              <p style={{ fontSize: '13px', fontWeight: 700, color: '#0b1f3a', margin: 0 }}>
                Traces
              </p>
              <p style={{ fontSize: '11px', color: '#64748b', margin: '3px 0 0 0' }}>
                24,832 spans collected
              </p>
            </div>
            <span style={{
              padding: '3px 8px', borderRadius: 9999,
              background: '#fef3c7', border: '1px solid #fde68a',
              fontSize: '10px', fontWeight: 600, color: '#d97706',
            }}>
              Active
            </span>
          </div>
        </div>
        <div style={{ ...CARD, padding: '12px 16px' }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
            <div style={{
              width: 26, height: 26, borderRadius: 8, background: '#dbeafe',
              border: '1px solid #bfdbfe',
              display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
            }}>
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                <rect x="2" y="8" width="2.5" height="4" rx="0.5" fill="#2563eb"/>
                <rect x="5.75" y="5" width="2.5" height="7" rx="0.5" fill="#2563eb"/>
                <rect x="9.5" y="2" width="2.5" height="10" rx="0.5" fill="#2563eb"/>
              </svg>
            </div>
            <div style={{ flex: 1 }}>
              <p style={{ fontSize: '13px', fontWeight: 700, color: '#0b1f3a', margin: 0 }}>
                Metrics
              </p>
              <p style={{ fontSize: '11px', color: '#64748b', margin: '3px 0 0 0' }}>
                156,428 data points
              </p>
            </div>
            <span style={{
              padding: '3px 8px', borderRadius: 9999,
              background: '#dbeafe', border: '1px solid #bfdbfe',
              fontSize: '10px', fontWeight: 600, color: '#2563eb',
            }}>
              Live
            </span>
          </div>
        </div>
        <div style={{ ...CARD, padding: '12px 16px' }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
            <div style={{
              width: 26, height: 26, borderRadius: 8, background: '#f3e8ff',
              border: '1px solid #e9d5ff',
              display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
            }}>
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                <rect x="2" y="2" width="10" height="10" rx="1.5" stroke="#9333ea" strokeWidth="1.2"/>
                <line x1="4" y1="5" x2="10" y2="5" stroke="#9333ea" strokeWidth="1"/>
                <line x1="4" y1="7.5" x2="8" y2="7.5" stroke="#9333ea" strokeWidth="1"/>
                <line x1="4" y1="10" x2="9" y2="10" stroke="#9333ea" strokeWidth="1"/>
              </svg>
            </div>
            <div style={{ flex: 1 }}>
              <p style={{ fontSize: '13px', fontWeight: 700, color: '#0b1f3a', margin: 0 }}>
                Logs
              </p>
              <p style={{ fontSize: '11px', color: '#64748b', margin: '3px 0 0 0' }}>
                2.4M entries/hour
              </p>
            </div>
            <span style={{
              padding: '3px 8px', borderRadius: 9999,
              background: '#f3e8ff', border: '1px solid #e9d5ff',
              fontSize: '10px', fontWeight: 600, color: '#9333ea',
            }}>
              Streaming
            </span>
          </div>
        </div>
        <div style={{ ...CARD, padding: '12px 16px' }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
            <div style={{
              width: 26, height: 26, borderRadius: 8, background: '#fee2e2',
              border: '1px solid #fecaca',
              display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
            }}>
              <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                <circle cx="7" cy="7" r="5" stroke="#dc2626" strokeWidth="1.2"/>
                <circle cx="7" cy="7" r="2" fill="#dc2626"/>
                <circle cx="7" cy="7" r="3.5" stroke="#dc2626" strokeWidth="0.8" strokeOpacity="0.4"/>
              </svg>
            </div>
            <div style={{ flex: 1 }}>
              <p style={{ fontSize: '13px', fontWeight: 700, color: '#0b1f3a', margin: 0 }}>
                Events
              </p>
              <p style={{ fontSize: '11px', color: '#64748b', margin: '3px 0 0 0' }}>
                8,432 anomalies detected
              </p>
            </div>
            <span style={{
              padding: '3px 8px', borderRadius: 9999,
              background: '#fee2e2', border: '1px solid #fecaca',
              fontSize: '10px', fontWeight: 600, color: '#dc2626',
            }}>
              Alert
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}