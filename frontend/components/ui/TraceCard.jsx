const CARD = {
  background: '#ffffff',
  borderRadius: 14,
  border: '1px solid rgba(147,197,253,0.35)',
  boxShadow: '0 4px 20px rgba(37,99,235,0.08), 0 1px 4px rgba(0,0,0,0.05)',
  padding: '10px 14px',
};

export default function TraceCard({ method='POST', path, status, statusText, traceId, timestamp, className='', style={} }) {
  const statusColor = status >= 500 ? '#ef4444' : status >= 400 ? '#f59e0b' : '#22c55e';
  return (
    <div style={{ ...CARD, ...style }} className={className}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{ width: 22, height: 22, borderRadius: 6, background: '#f5f3ff',
                        display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
              <circle cx="2"  cy="6" r="1.5" stroke="#8b5cf6" strokeWidth="1"/>
              <circle cx="10" cy="6" r="1.5" stroke="#8b5cf6" strokeWidth="1"/>
              <path d="M3.5 6 Q6 2.5 8.5 6"  stroke="#8b5cf6" strokeWidth="1" fill="none" strokeLinecap="round"/>
              <path d="M3.5 6 Q6 9.5 8.5 6"  stroke="#8b5cf6" strokeWidth="1" fill="none" strokeLinecap="round" strokeDasharray="1.5 1.2"/>
            </svg>
          </div>
          <span style={{ fontSize: 12, fontWeight: 600, color: '#0b1f3a' }}>Trace</span>
        </div>
        <span style={{ fontSize: 10.5, color: '#9ca3af', fontFamily: 'monospace' }}>{timestamp}</span>
      </div>
      <p style={{ fontSize: 11.5, fontFamily: 'monospace', color: '#374151', marginBottom: 2 }}>
        <span style={{ color: '#3b82f6', fontWeight: 700, marginRight: 4 }}>{method}</span>
        {path}
      </p>
      <p style={{ fontSize: 11.5, fontWeight: 600, color: statusColor }}>{status} {statusText}</p>
      {traceId && (
        <p style={{ fontSize: 10, color: '#9ca3af', fontFamily: 'monospace', marginTop: 3 }}>
          trace_id: {traceId}
        </p>
      )}
    </div>
  );
}
