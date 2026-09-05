'use client';
import { useState } from 'react';

const INCIDENT_PRESETS = [
  'Database connection pool exhaustion',
  'Payment service timeout',
  'AI service rate limiting',
  'Redis cache stampede',
  'Inventory deadlock',
  'Incident wave (multiple services)',
  'Rolling chaos',
];

export default function ShopflowHeader({ selectedIncident = 'Database connection pool exhaustion', onSelectIncident }) {
  const [dropdownOpen, setDropdownOpen] = useState(true);

  return (
    <div style={{
      display: 'flex',
      alignItems: 'flex-start',
      justifyContent: 'space-between',
      marginBottom: 16,
      position: 'relative',
    }}>
      {/* Left: Platform identity */}
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 14 }}>
        {/* Blue shopping cart icon */}
        <div style={{
          width: 44,
          height: 44,
          borderRadius: 12,
          background: '#eff6ff',
          border: '1px solid #dbeafe',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#2563eb',
          flexShrink: 0,
        }}>
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
            <path d="M3 3H5L6.68 14.39C6.77 15.02 7.31 15.5 7.95 15.5H19.05C19.69 15.5 20.23 15.02 20.32 14.39L21.5 6.5H6"
                  stroke="#2563eb" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
            <circle cx="9" cy="20" r="1.5" fill="#2563eb"/>
            <circle cx="18" cy="20" r="1.5" fill="#2563eb"/>
          </svg>
        </div>

        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <h1 style={{
              fontSize: '20px',
              fontWeight: 800,
              color: '#0b1f3a',
              margin: 0,
              letterSpacing: '-0.02em',
            }}>
              ShopFlow
            </h1>
            <span style={{
              background: '#eff6ff',
              color: '#2563eb',
              border: '1px solid #dbeafe',
              fontSize: '11px',
              fontWeight: 600,
              padding: '2px 8px',
              borderRadius: 9999,
            }}>
              Demo environment
            </span>
          </div>

          <p style={{
            fontSize: '12.5px',
            color: '#64748b',
            margin: '2px 0 6px 0',
          }}>
            An e-commerce platform to showcase FaultLens
          </p>

          <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: '11.5px', color: '#475569', fontWeight: 500 }}>
              <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#3b82f6' }}/>
              5 services
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: '11.5px', color: '#475569', fontWeight: 500 }}>
              <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#3b82f6' }}/>
              Rich telemetry
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: '11.5px', color: '#475569', fontWeight: 500 }}>
              <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#3b82f6' }}/>
              OpenTelemetry
            </span>
          </div>
        </div>
      </div>

      {/* Right: Status & Action Buttons */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, position: 'relative' }}>
        {/* Live demo badge */}
        <div style={{
          background: '#ecfdf5',
          border: '1px solid #a7f3d0',
          color: '#059669',
          fontSize: '11.5px',
          fontWeight: 600,
          padding: '5px 11px',
          borderRadius: 9999,
          display: 'flex',
          alignItems: 'center',
          gap: 6,
        }}>
          <span style={{
            width: 7,
            height: 7,
            borderRadius: '50%',
            background: '#10b981',
            boxShadow: '0 0 8px rgba(16, 185, 129, 0.6)',
          }}/>
          Live demo
        </div>

        {/* Inject incident button */}
        <div style={{ position: 'relative' }}>
          <button
            onClick={() => setDropdownOpen(prev => !prev)}
            style={{
              background: '#3b82f6',
              color: '#ffffff',
              border: 'none',
              borderRadius: 9999,
              padding: '6px 14px',
              fontSize: '12.5px',
              fontWeight: 600,
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              cursor: 'pointer',
              boxShadow: '0 2px 8px rgba(59, 130, 246, 0.25)',
              transition: 'all 0.15s ease',
            }}
          >
            Inject incident <span style={{ fontSize: '10px' }}>{dropdownOpen ? '▲' : '▼'}</span>
          </button>

          {/* Incident Preset Dropdown */}
          {dropdownOpen && (
            <div style={{
              position: 'absolute',
              top: 'calc(100% + 8px)',
              right: 0,
              width: 250,
              background: '#ffffff',
              borderRadius: 14,
              padding: '6px',
              border: '1px solid rgba(226, 232, 240, 0.95)',
              boxShadow: '0 10px 30px -4px rgba(15, 23, 42, 0.1), 0 4px 10px rgba(0,0,0,0.03)',
              zIndex: 40,
              display: 'flex',
              flexDirection: 'column',
              gap: 2,
            }}>
              {INCIDENT_PRESETS.map((preset) => {
                const isSelected = selectedIncident === preset;
                return (
                  <div
                    key={preset}
                    onClick={() => {
                      if (onSelectIncident) onSelectIncident(preset);
                      setDropdownOpen(false);
                    }}
                    style={{
                      padding: '7px 11px',
                      borderRadius: 8,
                      fontSize: '11.5px',
                      fontWeight: isSelected ? 600 : 500,
                      color: isSelected ? '#2563eb' : '#334155',
                      background: isSelected ? '#eff6ff' : 'transparent',
                      cursor: 'pointer',
                      transition: 'background 0.12s ease',
                    }}
                    onMouseEnter={e => {
                      if (!isSelected) e.currentTarget.style.background = '#f8fafc';
                    }}
                    onMouseLeave={e => {
                      if (!isSelected) e.currentTarget.style.background = 'transparent';
                    }}
                  >
                    {preset}
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Reset button */}
        <button
          onClick={() => {
            if (onSelectIncident) onSelectIncident('Database connection pool exhaustion');
          }}
          style={{
            background: '#ffffff',
            color: '#475569',
            border: '1px solid #cbd5e1',
            borderRadius: 9999,
            padding: '6px 12px',
            fontSize: '12.5px',
            fontWeight: 600,
            display: 'flex',
            alignItems: 'center',
            gap: 5,
            cursor: 'pointer',
            boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
            transition: 'all 0.15s ease',
          }}
          onMouseEnter={e => e.currentTarget.style.background = '#f8fafc'}
          onMouseLeave={e => e.currentTarget.style.background = '#ffffff'}
        >
          <span style={{ fontSize: '12px' }}>↻</span> Reset
        </button>
      </div>
    </div>
  );
}
