const CARD = {
  background: '#ffffff',
  borderRadius: 14,
  border: '1px solid rgba(147,197,253,0.35)',
  boxShadow: '0 4px 20px rgba(37,99,235,0.08), 0 1px 4px rgba(0,0,0,0.05)',
  padding: '10px 14px',
};

export default function MetricCard({ name, value, baseline, trend = 'up', timestamp, className = '', style = {} }) {
  const isUp = trend === 'up';
  return (
    <div style={{ ...CARD, ...style }} className={className}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{ width: 22, height: 22, borderRadius: 6, background: '#eff6ff',
                        display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
              <rect x="0.5" y="7"   width="3" height="4.5" rx="0.7" fill="#3b82f6"/>
              <rect x="4.5" y="4.5" width="3" height="7"   rx="0.7" fill="#3b82f6"/>
              <rect x="8.5" y="1"   width="3" height="10.5" rx="0.7" fill="#3b82f6"/>
            </svg>
          </div>
          <span style={{ fontSize: 12, fontWeight: 600, color: '#0b1f3a' }}>Metric</span>
        </div>
        <span style={{ fontSize: 10.5, color: '#9ca3af', fontFamily: 'monospace' }}>{timestamp}</span>
      </div>
      <p style={{ fontSize: 11, color: '#6b7280', marginBottom: 2 }}>{name}</p>
      <p style={{ fontSize: 12, fontWeight: 700, color: isUp ? '#ef4444' : '#22c55e' }}>
        {isUp ? '↑' : '↓'} {value}
        {baseline && (
          <span style={{ fontSize: 10.5, fontWeight: 400, color: '#9ca3af', marginLeft: 4 }}>
            (baseline: {baseline})
          </span>
        )}
      </p>
    </div>
  );
}
