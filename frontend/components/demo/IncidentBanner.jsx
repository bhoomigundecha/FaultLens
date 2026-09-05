'use client';

export default function IncidentBanner() {
  return (
    <div style={{
      background: '#ffffff',
      borderRadius: 16,
      border: '1px solid rgba(226, 232, 240, 0.95)',
      boxShadow: '0 4px 20px -2px rgba(15, 23, 42, 0.04), 0 2px 6px -1px rgba(15, 23, 42, 0.02)',
      padding: '18px 24px',
      display: 'grid',
      gridTemplateColumns: '1.45fr 1fr',
      gap: 28,
      alignItems: 'center',
      marginBottom: 16,
    }}>
      {/* Left Column: Active Incident Report */}
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 14 }}>
        {/* Red exclamation mark circle */}
        <div style={{
          width: 36,
          height: 36,
          borderRadius: '50%',
          background: '#fee2e2',
          border: '1px solid #fecaca',
          color: '#ef4444',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontWeight: 800,
          fontSize: '17px',
          flexShrink: 0,
        }}>
          !
        </div>

        <div>
          {/* Badge & Detection time */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
            <span style={{
              background: '#fee2e2',
              color: '#dc2626',
              fontSize: '9.5px',
              fontWeight: 800,
              letterSpacing: '0.04em',
              padding: '2px 7px',
              borderRadius: 9999,
              textTransform: 'uppercase',
            }}>
              Incident Detected
            </span>
            <span style={{ fontSize: '11.5px', color: '#64748b' }}>
              Detected 42 seconds ago
            </span>
          </div>

          {/* Title */}
          <h2 style={{
            fontSize: '19px',
            fontWeight: 800,
            color: '#0b1f3a',
            margin: '0 0 6px 0',
            letterSpacing: '-0.02em',
          }}>
            Database Connection Pool Exhausted
          </h2>

          {/* Target Service Badge */}
          <div style={{ marginBottom: 8 }}>
            <span style={{
              background: '#eff6ff',
              color: '#2563eb',
              border: '1px solid #dbeafe',
              borderRadius: 9999,
              padding: '2px 10px',
              fontSize: '11.5px',
              fontWeight: 700,
            }}>
              payment-service
            </span>
          </div>

          {/* Summary description */}
          <p style={{
            fontSize: '12px',
            color: '#475569',
            lineHeight: 1.45,
            margin: '0 0 12px 0',
          }}>
            Database connection pool exhaustion is causing payment requests to time out, propagating failures upstream to order-service and api-gateway.
          </p>

          {/* Incident metadata tags */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 14, flexWrap: 'wrap' }}>
            {/* Severity */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ fontSize: '11px', color: '#64748b', fontWeight: 500 }}>Severity</span>
              <span style={{
                background: '#fee2e2',
                color: '#dc2626',
                fontSize: '11px',
                fontWeight: 700,
                padding: '2px 8px',
                borderRadius: 9999,
              }}>
                High
              </span>
            </div>

            {/* Confidence */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ fontSize: '11px', color: '#64748b', fontWeight: 500 }}>Confidence</span>
              <span style={{
                background: '#eff6ff',
                color: '#2563eb',
                fontSize: '11px',
                fontWeight: 700,
                padding: '2px 8px',
                borderRadius: 9999,
              }}>
                92%
              </span>
            </div>

            {/* Routed to */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ fontSize: '11px', color: '#64748b', fontWeight: 500 }}>Routed to</span>
              <span style={{
                background: '#eff6ff',
                color: '#2563eb',
                border: '1px solid #dbeafe',
                fontSize: '11px',
                fontWeight: 600,
                padding: '2px 10px',
                borderRadius: 9999,
                display: 'inline-flex',
                alignItems: 'center',
                gap: 5,
              }}>
                <svg width="13" height="13" viewBox="0 0 20 20" fill="none">
                  <path d="M7 10C8.65685 10 10 8.65685 10 7C10 5.34315 8.65685 4 7 4C5.34315 4 4 5.34315 4 7C4 8.65685 5.34315 10 7 10Z" stroke="#2563eb" strokeWidth="1.4"/>
                  <path d="M14 8C15.1046 8 16 7.10457 16 6C16 4.89543 15.1046 4 14 4" stroke="#2563eb" strokeWidth="1.4" strokeLinecap="round"/>
                  <path d="M1 16C1 13.7909 3.68629 12 7 12C10.3137 12 13 13.7909 13 16" stroke="#2563eb" strokeWidth="1.4"/>
                  <path d="M14 12C16.2091 12 18 13.3431 18 15" stroke="#2563eb" strokeWidth="1.4" strokeLinecap="round"/>
                </svg>
                Backend Engineering
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Right Column: Root Cause Diagnosis */}
      <div style={{
        borderLeft: '1px solid #f1f5f9',
        paddingLeft: 24,
        display: 'flex',
        alignItems: 'flex-start',
        gap: 12,
      }}>
        {/* Crosshair / Target Radar icon */}
        <div style={{
          width: 32,
          height: 32,
          borderRadius: '50%',
          background: '#eff6ff',
          border: '1px solid #dbeafe',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#2563eb',
          flexShrink: 0,
        }}>
          <svg width="16" height="16" viewBox="0 0 20 20" fill="none">
            <circle cx="10" cy="10" r="6" stroke="#2563eb" strokeWidth="1.4"/>
            <circle cx="10" cy="10" r="2" fill="#2563eb"/>
            <line x1="10" y1="1" x2="10" y2="4" stroke="#2563eb" strokeWidth="1.4" strokeLinecap="round"/>
            <line x1="10" y1="16" x2="10" y2="19" stroke="#2563eb" strokeWidth="1.4" strokeLinecap="round"/>
            <line x1="1" y1="10" x2="4" y2="10" stroke="#2563eb" strokeWidth="1.4" strokeLinecap="round"/>
            <line x1="16" y1="10" x2="19" y2="10" stroke="#2563eb" strokeWidth="1.4" strokeLinecap="round"/>
          </svg>
        </div>

        <div>
          <h3 style={{
            fontSize: '13px',
            fontWeight: 700,
            color: '#0b1f3a',
            margin: 0,
          }}>
            Root cause
          </h3>

          <div style={{ margin: '6px 0 6px 0' }}>
            <span style={{
              background: '#eff6ff',
              color: '#2563eb',
              border: '1px solid #bfdbfe',
              borderRadius: 9999,
              padding: '3px 12px',
              fontSize: '12px',
              fontWeight: 700,
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6,
            }}>
              payment-service → database
            </span>
          </div>

          <p style={{
            fontSize: '11.5px',
            color: '#475569',
            lineHeight: 1.4,
            margin: '0 0 10px 0',
          }}>
            Database connection pool exhaustion is the most probable root cause.
          </p>

          <a href="#rca" style={{
            color: '#2563eb',
            fontSize: '11.5px',
            fontWeight: 600,
            textDecoration: 'none',
            display: 'inline-flex',
            alignItems: 'center',
            gap: 4,
          }}>
            View full RCA →
          </a>
        </div>
      </div>
    </div>
  );
}
