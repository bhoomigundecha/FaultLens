'use client';

import { useState } from 'react';

/* ── ENV TYPE → colour ───────────────────────────────────────────── */
function envBadge(envType) {
  const map = {
    rich:    { bg: '#ecfdf5', color: '#059669', border: '#a7f3d0', label: 'Rich telemetry'   },
    medium:  { bg: '#eff6ff', color: '#2563eb', border: '#bfdbfe', label: 'Medium telemetry' },
    thin:    { bg: '#fef3c7', color: '#b45309', border: '#fde68a', label: 'Thin telemetry'   },
    unknown: { bg: '#f8fafc', color: '#64748b', border: '#e2e8f0', label: 'Unknown'          },
  };
  return map[envType] ?? map.unknown;
}

/* ── Pulse dot ───────────────────────────────────────────────────── */
function PulseDot() {
  return (
    <span style={{ position: 'relative', width: 8, height: 8, flexShrink: 0, display: 'inline-flex' }}>
      <span style={{
        position: 'absolute', inset: 0, borderRadius: '50%',
        background: '#10b981', opacity: 0.5,
        animation: 'ping 1.4s cubic-bezier(0,0,0.2,1) infinite',
      }}/>
      <span style={{
        position: 'relative', width: 8, height: 8,
        borderRadius: '50%', background: '#10b981',
      }}/>
      <style>{`@keyframes ping{75%,100%{transform:scale(2);opacity:0}}`}</style>
    </span>
  );
}

/* ── IncidentSelector dropdown ───────────────────────────────────── */
function IncidentSelector({ incidents, selectedId, onSelect }) {
  const [open, setOpen] = useState(false);

  const selected = incidents.find(i => i.incident_id === selectedId);
  const label    = selected
    ? `${selected.failure_type ?? 'Incident'} — ${selected.service_id}`
    : 'Select an incident';

  function humanise(type) {
    if (!type) return 'Anomaly';
    return type.split('_').map(w => w.charAt(0) + w.slice(1).toLowerCase()).join(' ');
  }

  function timeAgo(iso) {
    if (!iso) return '';
    const s = Math.round((Date.now() - new Date(iso).getTime()) / 1000);
    if (s < 60) return `${s}s ago`;
    const m = Math.floor(s / 60);
    if (m < 60) return `${m}m ago`;
    return `${Math.floor(m / 60)}h ago`;
  }

  return (
    <div style={{ position: 'relative' }}>
      <button
        onClick={() => setOpen(o => !o)}
        style={{
          display: 'flex', alignItems: 'center', gap: 8,
          background: '#fff', border: '1px solid #e2e8f0',
          borderRadius: 10, padding: '7px 12px',
          fontSize: 12, fontWeight: 600, color: '#0b1f3a',
          cursor: 'pointer', boxShadow: '0 1px 4px rgba(0,0,0,0.04)',
          minWidth: 240,
        }}
      >
        <svg width="13" height="13" viewBox="0 0 20 20" fill="none">
          <circle cx="10" cy="10" r="8" stroke="#ef4444" strokeWidth="1.8"/>
          <line x1="10" y1="6" x2="10" y2="11" stroke="#ef4444" strokeWidth="1.8" strokeLinecap="round"/>
          <circle cx="10" cy="14" r="1" fill="#ef4444"/>
        </svg>
        <span style={{ flex: 1, textAlign: 'left', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {label}
        </span>
        <span style={{ color: '#94a3b8', fontSize: 10 }}>{open ? '▲' : '▼'}</span>
      </button>

      {open && incidents.length > 0 && (
        <div style={{
          position: 'absolute', top: '100%', left: 0, marginTop: 4,
          background: '#fff', border: '1px solid #e2e8f0',
          borderRadius: 12, boxShadow: '0 8px 24px rgba(15,23,42,0.12)',
          zIndex: 50, minWidth: 300, maxHeight: 320, overflowY: 'auto',
        }}>
          {incidents.map(inc => (
            <button
              key={inc.incident_id}
              onClick={() => { onSelect(inc.incident_id); setOpen(false); }}
              style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                width: '100%', padding: '9px 14px',
                background: inc.incident_id === selectedId ? '#eff6ff' : 'transparent',
                border: 'none', borderBottom: '1px solid #f1f5f9',
                cursor: 'pointer', textAlign: 'left', gap: 8,
              }}
              onMouseEnter={e => { if (inc.incident_id !== selectedId) e.currentTarget.style.background = '#f8fafc'; }}
              onMouseLeave={e => { if (inc.incident_id !== selectedId) e.currentTarget.style.background = 'transparent'; }}
            >
              <div style={{ minWidth: 0 }}>
                <p style={{ fontSize: 12, fontWeight: 700, color: '#0b1f3a', margin: 0,
                             overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {humanise(inc.failure_type)}
                </p>
                <p style={{ fontSize: 10, color: '#64748b', margin: '1px 0 0 0' }}>
                  {inc.service_id}
                </p>
              </div>
              <span style={{ fontSize: 10, color: '#94a3b8', flexShrink: 0 }}>
                {timeAgo(inc.created_at)}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

/* ── ShopflowHeader ──────────────────────────────────────────────── */
export default function ShopflowHeader({ incidents, services, selectedId, onSelectIncident, onRefresh }) {
  const svcCount   = services?.length ?? 5;
  const openCount  = (incidents ?? []).filter(i => i.status === 'open').length;

  // Determine overall env type from services
  const envTypes   = (services ?? []).map(s => s.env_type);
  const primaryEnv = envTypes.includes('rich') ? 'rich'
    : envTypes.includes('medium') ? 'medium'
    : envTypes.includes('thin') ? 'thin' : 'unknown';
  const env = envBadge(primaryEnv);

  return (
    <div style={{
      display: 'flex', alignItems: 'flex-start',
      justifyContent: 'space-between', marginBottom: 16, gap: 16,
    }}>
      {/* ── Left: identity ── */}
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 14 }}>
        {/* Cart icon */}
        <div style={{
          width: 44, height: 44, borderRadius: 12, background: '#eff6ff',
          border: '1px solid #dbeafe', display: 'flex', alignItems: 'center',
          justifyContent: 'center', flexShrink: 0,
        }}>
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
            <path d="M3 3H5L6.68 14.39C6.77 15.02 7.31 15.5 7.95 15.5H19.05C19.69 15.5 20.23 15.02 20.32 14.39L21.5 6.5H6"
                  stroke="#2563eb" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
            <circle cx="9"  cy="20" r="1.5" fill="#2563eb"/>
            <circle cx="18" cy="20" r="1.5" fill="#2563eb"/>
          </svg>
        </div>

        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <h1 style={{ fontSize: 20, fontWeight: 800, color: '#0b1f3a', margin: 0, letterSpacing: '-0.02em' }}>
              ShopFlow
            </h1>
            <span style={{
              background: '#eff6ff', color: '#2563eb', border: '1px solid #dbeafe',
              fontSize: 11, fontWeight: 600, padding: '2px 8px', borderRadius: 9999,
            }}>
              Demo environment
            </span>
          </div>

          <p style={{ fontSize: '12.5px', color: '#64748b', margin: '2px 0 6px 0' }}>
            An e-commerce platform to showcase FaultLens
          </p>

          {/* Service metadata — live counts */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
            <Chip color="#3b82f6" label={`${svcCount} service${svcCount !== 1 ? 's' : ''}`} />
            <Chip
              color={env.color.replace(')', '').replace('rgb', 'rgb')}
              label={env.label}
            />
            <Chip color="#3b82f6" label="OpenTelemetry" />
            {openCount > 0 && (
              <Chip color="#ef4444" label={`${openCount} open incident${openCount !== 1 ? 's' : ''}`} />
            )}
          </div>
        </div>
      </div>

      {/* ── Right: controls ── */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexShrink: 0 }}>
        {/* Live badge */}
        <div style={{
          background: '#ecfdf5', border: '1px solid #a7f3d0', color: '#059669',
          fontSize: '11.5px', fontWeight: 600, padding: '5px 11px',
          borderRadius: 9999, display: 'flex', alignItems: 'center', gap: 5,
        }}>
          <PulseDot />
          Live
        </div>

        {/* Incident selector */}
        {incidents && incidents.length > 0 && (
          <IncidentSelector
            incidents={incidents}
            selectedId={selectedId}
            onSelect={onSelectIncident}
          />
        )}

        {/* Refresh */}
        <button
          onClick={onRefresh}
          title="Refresh now"
          style={{
            background: '#fff', border: '1px solid #e2e8f0',
            borderRadius: 9999, width: 34, height: 34,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            cursor: 'pointer', color: '#475569',
            boxShadow: '0 1px 4px rgba(0,0,0,0.04)',
          }}
          onMouseEnter={e => (e.currentTarget.style.borderColor = '#93c5fd')}
          onMouseLeave={e => (e.currentTarget.style.borderColor = '#e2e8f0')}
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
            <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"
                  stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </button>
      </div>
    </div>
  );
}

function Chip({ color, label }) {
  return (
    <span style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: '11.5px', color: '#475569', fontWeight: 500 }}>
      <span style={{ width: 6, height: 6, borderRadius: '50%', background: color, flexShrink: 0 }}/>
      {label}
    </span>
  );
}
