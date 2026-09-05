'use client';

export default function DependencyGraph() {
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
      <div style={{ display: 'flex', alignItems: 'center', gap: 9, marginBottom: 14 }}>
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
            <circle cx="6" cy="6" r="3" stroke="#2563eb" strokeWidth="2"/>
            <circle cx="6" cy="18" r="3" stroke="#2563eb" strokeWidth="2"/>
            <circle cx="18" cy="12" r="3" stroke="#2563eb" strokeWidth="2"/>
            <path d="M9 6H12C13.6569 6 15 7.34315 15 9V12" stroke="#2563eb" strokeWidth="1.8"/>
            <path d="M9 18H12C13.6569 18 15 16.6569 15 15V12" stroke="#2563eb" strokeWidth="1.8"/>
          </svg>
        </div>
        <h3 style={{ fontSize: '13.5px', fontWeight: 700, color: '#0b1f3a', margin: 0 }}>
          Service dependency graph
        </h3>
      </div>

      {/* Services flow */}
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'stretch', gap: 0 }}>

        {/* 1. api-gateway */}
        <div style={{
          background: '#f8fafc',
          border: '1px solid #e2e8f0',
          borderRadius: 12,
          padding: '9px 12px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#10b981', flexShrink: 0 }}/>
            <div>
              <p style={{ fontSize: '12.5px', fontWeight: 700, color: '#0b1f3a', margin: 0 }}>
                api-gateway
              </p>
              <p style={{ fontSize: '10.5px', color: '#64748b', margin: '1px 0 0 0' }}>
                503 errors <span style={{ color: '#ef4444', fontWeight: 700 }}>↑</span>
              </p>
            </div>
          </div>

          {/* Mini blue sparkline */}
          <svg width="65" height="22" viewBox="0 0 65 22" fill="none">
            <path d="M0,18 L12,16 L24,19 L36,12 L48,15 L65,6 L65,22 L0,22 Z" fill="#dbeafe" opacity="0.6"/>
            <path d="M0,18 L12,16 L24,19 L36,12 L48,15 L65,6" stroke="#60a5fa" strokeWidth="1.5" fill="none"/>
          </svg>
        </div>

        {/* Down arrow */}
        <div style={{ display: 'flex', justifyContent: 'center', color: '#93c5fd', fontSize: '12px', margin: '3px 0' }}>
          ↓
        </div>

        {/* 2. order-service */}
        <div style={{
          background: '#f8fafc',
          border: '1px solid #e2e8f0',
          borderRadius: 12,
          padding: '9px 12px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#f59e0b', flexShrink: 0 }}/>
            <div>
              <p style={{ fontSize: '12.5px', fontWeight: 700, color: '#0b1f3a', margin: 0 }}>
                order-service
              </p>
              <p style={{ fontSize: '10.5px', color: '#64748b', margin: '1px 0 0 0' }}>
                Increased errors
              </p>
            </div>
          </div>

          {/* Mini blue sparkline */}
          <svg width="65" height="22" viewBox="0 0 65 22" fill="none">
            <path d="M0,17 L14,18 L28,14 L42,16 L54,10 L65,8 L65,22 L0,22 Z" fill="#dbeafe" opacity="0.6"/>
            <path d="M0,17 L14,18 L28,14 L42,16 L54,10 L65,8" stroke="#60a5fa" strokeWidth="1.5" fill="none"/>
          </svg>
        </div>

        {/* Down arrow */}
        <div style={{ display: 'flex', justifyContent: 'center', color: '#93c5fd', fontSize: '12px', margin: '3px 0' }}>
          ↓
        </div>

        {/* 3. payment-service (ROOT CAUSE) */}
        <div style={{ position: 'relative' }}>
          <div style={{
            background: '#fef2f2',
            border: '1.5px solid #fecaca',
            borderRadius: 12,
            padding: '9px 12px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            boxShadow: '0 4px 12px rgba(239, 68, 68, 0.08)',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#ef4444', flexShrink: 0 }}/>
              <div>
                <p style={{ fontSize: '12.5px', fontWeight: 700, color: '#0b1f3a', margin: 0 }}>
                  payment-service
                </p>
                <p style={{ fontSize: '10.5px', color: '#dc2626', fontWeight: 600, margin: '1px 0 0 0' }}>
                  High error rate
                </p>
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              {/* Mini red sparkline */}
              <svg width="55" height="22" viewBox="0 0 55 22" fill="none">
                <path d="M0,18 L10,17 L22,14 L34,18 L44,8 L55,4 L55,22 L0,22 Z" fill="#fee2e2" opacity="0.8"/>
                <path d="M0,18 L10,17 L22,14 L34,18 L44,8 L55,4" stroke="#ef4444" strokeWidth="1.5" fill="none"/>
              </svg>

              {/* ROOT CAUSE Badge */}
              <span style={{
                background: '#ef4444',
                color: '#ffffff',
                fontSize: '8.5px',
                fontWeight: 800,
                letterSpacing: '0.04em',
                padding: '2px 6px',
                borderRadius: 9999,
                whiteSpace: 'nowrap',
              }}>
                ROOT CAUSE
              </span>
            </div>
          </div>
        </div>

        {/* Down arrow */}
        <div style={{ display: 'flex', justifyContent: 'center', color: '#93c5fd', fontSize: '12px', margin: '3px 0' }}>
          ↓
        </div>

        {/* 4. database */}
        <div style={{
          background: '#f8fafc',
          border: '1px solid #e2e8f0',
          borderRadius: 12,
          padding: '9px 12px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#ef4444', flexShrink: 0 }}/>
            <div>
              <p style={{ fontSize: '12.5px', fontWeight: 700, color: '#0b1f3a', margin: 0 }}>
                database
              </p>
              <p style={{ fontSize: '10.5px', color: '#64748b', margin: '1px 0 0 0' }}>
                Connection pool exhausted
              </p>
            </div>
          </div>

          {/* Mini blue sparkline */}
          <svg width="65" height="22" viewBox="0 0 65 22" fill="none">
            <path d="M0,16 L15,17 L30,12 L45,15 L56,9 L65,7 L65,22 L0,22 Z" fill="#dbeafe" opacity="0.6"/>
            <path d="M0,16 L15,17 L30,12 L45,15 L56,9 L65,7" stroke="#60a5fa" strokeWidth="1.5" fill="none"/>
          </svg>
        </div>

      </div>
    </div>
  );
}
