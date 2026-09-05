'use client';

export default function RecommendedActions() {
  return (
    <div style={{
      background: '#ffffff',
      borderRadius: 16,
      border: '1px solid rgba(226, 232, 240, 0.95)',
      boxShadow: '0 4px 18px -2px rgba(15, 23, 42, 0.04)',
      padding: '14px 18px',
      marginTop: 16,
      display: 'flex',
      alignItems: 'center',
      gap: 14,
    }}>
      {/* Wrench icon & Section label */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0, paddingRight: 4 }}>
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
            <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"
                  stroke="#2563eb" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </div>
        <span style={{ fontSize: '12.5px', fontWeight: 700, color: '#0b1f3a', whiteSpace: 'nowrap' }}>
          Recommended actions
        </span>
      </div>

      {/* 3 Action Cards */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, flex: 1, minWidth: 0 }}>

        {/* Card 1: 01 */}
        <div style={{
          background: '#f8fafc',
          border: '1px solid #e2e8f0',
          borderRadius: 12,
          padding: '8px 12px',
          display: 'flex',
          alignItems: 'flex-start',
          gap: 9,
          flex: 1,
          minWidth: 0,
        }}>
          <div style={{
            width: 20,
            height: 20,
            borderRadius: '50%',
            background: '#eff6ff',
            border: '1px solid #bfdbfe',
            color: '#2563eb',
            fontSize: '9.5px',
            fontWeight: 800,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
            marginTop: 1,
          }}>
            01
          </div>
          <div style={{ minWidth: 0 }}>
            <p style={{
              fontSize: '11px',
              fontWeight: 700,
              color: '#0b1f3a',
              margin: 0,
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}>
              Increase database connection pool size
            </p>
            <p style={{
              fontSize: '10px',
              color: '#64748b',
              margin: '1px 0 0 0',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}>
              Scale the connection pool or enable auto-scaling based on load.
            </p>
          </div>
        </div>

        {/* Card 2: Check leaks */}
        <div style={{
          background: '#f8fafc',
          border: '1px solid #e2e8f0',
          borderRadius: 12,
          padding: '8px 12px',
          display: 'flex',
          alignItems: 'flex-start',
          gap: 9,
          flex: 1,
          minWidth: 0,
        }}>
          <div style={{
            width: 20,
            height: 20,
            borderRadius: 6,
            background: '#eff6ff',
            border: '1px solid #bfdbfe',
            color: '#2563eb',
            fontSize: '10px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
            marginTop: 1,
          }}>
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none">
              <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67" stroke="#2563eb" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          <div style={{ minWidth: 0 }}>
            <p style={{
              fontSize: '11px',
              fontWeight: 700,
              color: '#0b1f3a',
              margin: 0,
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}>
              Check for connection leaks in payment-service
            </p>
            <p style={{
              fontSize: '10px',
              color: '#64748b',
              margin: '1px 0 0 0',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}>
              Review connection handling and ensure proper cleanup.
            </p>
          </div>
        </div>

        {/* Card 3: Recent deployments */}
        <div style={{
          background: '#f8fafc',
          border: '1px solid #e2e8f0',
          borderRadius: 12,
          padding: '8px 12px',
          display: 'flex',
          alignItems: 'flex-start',
          gap: 9,
          flex: 1,
          minWidth: 0,
        }}>
          <div style={{
            width: 20,
            height: 20,
            borderRadius: 6,
            background: '#eff6ff',
            border: '1px solid #bfdbfe',
            color: '#2563eb',
            fontSize: '10px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            flexShrink: 0,
            marginTop: 1,
          }}>
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none">
              <ellipse cx="12" cy="5" rx="9" ry="3" stroke="#2563eb" strokeWidth="1.8"/>
              <path d="M3 5V12C3 13.66 7.03 15 12 15C16.97 15 21 13.66 21 12V5" stroke="#2563eb" strokeWidth="1.8"/>
              <path d="M3 12V19C3 20.66 7.03 22 12 22C16.97 22 21 20.66 21 19V12" stroke="#2563eb" strokeWidth="1.8"/>
            </svg>
          </div>
          <div style={{ minWidth: 0 }}>
            <p style={{
              fontSize: '11px',
              fontWeight: 700,
              color: '#0b1f3a',
              margin: 0,
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}>
              Review recent deployment changes
            </p>
            <p style={{
              fontSize: '10px',
              color: '#64748b',
              margin: '1px 0 0 0',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}>
              Check for any recent releases that might have introduced connection leaks.
            </p>
          </div>
        </div>

      </div>

      {/* View full RCA button */}
      <a
        href="#rca"
        style={{
          background: '#0b1f3a',
          color: '#ffffff',
          borderRadius: 9999,
          padding: '8px 18px',
          fontSize: '11.5px',
          fontWeight: 600,
          textDecoration: 'none',
          whiteSpace: 'nowrap',
          flexShrink: 0,
          boxShadow: '0 4px 14px rgba(11, 31, 58, 0.25)',
          display: 'inline-flex',
          alignItems: 'center',
          gap: 5,
        }}
      >
        View full RCA →
      </a>
    </div>
  );
}
