/* Shared card style */
const CARD = {
  background: '#ffffff',
  borderRadius: 14,
  border: '1px solid rgba(147,197,253,0.35)',
  boxShadow: '0 4px 20px rgba(37,99,235,0.08), 0 1px 4px rgba(0,0,0,0.05)',
  padding: '10px 14px',
};

const LEVEL_CONFIG = {
  ERROR: { iconBg: '#fef2f2', stroke: '#ef4444', textColor: '#ef4444', label: 'ERROR' },
  WARN:  { iconBg: '#fffbeb', stroke: '#f59e0b', textColor: '#f59e0b', label: 'WARN'  },
  INFO:  { iconBg: '#eff6ff', stroke: '#3b82f6', textColor: '#3b82f6', label: 'INFO'  },
};

export default function LogCard({ level = 'ERROR', message, traceId, timestamp, className = '', style = {} }) {
  const cfg = LEVEL_CONFIG[level] ?? LEVEL_CONFIG.INFO;

  return (
    <div style={{ ...CARD, ...style }} className={className}>
      {/* Header row */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {/* Icon */}
          <div style={{ width: 22, height: 22, borderRadius: 6, background: cfg.iconBg,
                        display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
              <rect x="1" y="1" width="10" height="10" rx="1.5" stroke={cfg.stroke} strokeWidth="1.1"/>
              <line x1="2.5" y1="4"   x2="9.5" y2="4"   stroke={cfg.stroke} strokeWidth="0.9"/>
              <line x1="2.5" y1="6.3" x2="9.5" y2="6.3" stroke={cfg.stroke} strokeWidth="0.9"/>
              <line x1="2.5" y1="8.5" x2="6"   y2="8.5" stroke={cfg.stroke} strokeWidth="0.9"/>
            </svg>
          </div>
          <span style={{ fontSize: 12, fontWeight: 600, color: '#0b1f3a' }}>Log</span>
        </div>
        <span style={{ fontSize: 10.5, color: '#9ca3af', fontFamily: 'monospace' }}>{timestamp}</span>
      </div>
      {/* Content */}
      <p style={{ fontSize: 11.5, fontWeight: 600, color: cfg.textColor, lineHeight: 1.45 }}>
        {cfg.label} {message}
      </p>
      {traceId && (
        <p style={{ fontSize: 10, color: '#9ca3af', fontFamily: 'monospace', marginTop: 3 }}>
          trace_id: {traceId}
        </p>
      )}
    </div>
  );
}
