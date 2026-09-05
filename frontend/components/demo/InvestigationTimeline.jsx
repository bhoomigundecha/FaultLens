'use client';

const STEPS = [
  {
    name: 'Signal Scout',
    duration: '4s',
    desc: 'Found anomalies across metrics, logs and traces.',
  },
  {
    name: 'Anomaly Hunter',
    duration: '6s',
    desc: 'Detected abnormal DB connection activity.',
  },
  {
    name: 'Graph Weaver',
    duration: '5s',
    desc: 'Traced dependencies and mapped the causal path.',
  },
  {
    name: 'RCA Investigator',
    duration: '7s',
    desc: 'Analysed evidence and ranked payment-service as root cause.',
  },
  {
    name: 'Triage',
    duration: '4s',
    desc: 'Classified as database connection pool exhaustion.',
  },
  {
    name: 'Reporter',
    duration: '2s',
    desc: 'Generated RCA and recommended actions.',
  },
];

export default function InvestigationTimeline() {
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
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: 14,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 9 }}>
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
              <path d="M12 2L14.5 9.5L22 12L14.5 14.5L12 22L9.5 14.5L2 12L9.5 9.5L12 2Z" fill="#2563eb"/>
            </svg>
          </div>
          <h3 style={{ fontSize: '13.5px', fontWeight: 700, color: '#0b1f3a', margin: 0 }}>
            FaultLens investigation
          </h3>
        </div>

        <span style={{
          background: '#ecfdf5',
          color: '#059669',
          border: '1px solid #a7f3d0',
          fontSize: '10px',
          fontWeight: 600,
          padding: '2px 8px',
          borderRadius: 9999,
        }}>
          Completed in 28s
        </span>
      </div>

      {/* Steps list */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 11 }}>
        {STEPS.map((step, idx) => (
          <div key={idx} style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
            {/* Blue check circle */}
            <div style={{
              width: 16,
              height: 16,
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
              ✓
            </div>

            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{ fontSize: '12px', fontWeight: 700, color: '#0b1f3a' }}>
                  {step.name}
                </span>
                <span style={{ fontSize: '10.5px', color: '#64748b', fontWeight: 500 }}>
                  {step.duration}
                </span>
              </div>
              <p style={{ fontSize: '10.5px', color: '#475569', margin: '2px 0 0 0', lineHeight: 1.35 }}>
                {step.desc}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
