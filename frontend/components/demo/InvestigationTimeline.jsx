'use client';

// The 6 agent nodes in order, with a human-readable description for each
const AGENT_META = {
  signal_scout: {
    label: 'Signal Scout',
    desc:  'Assessed available telemetry and chose analysis strategy.',
  },
  anomaly_hunter: {
    label: 'Anomaly Hunter',
    desc:  'Ran ML models (Z-score + Isolation Forest) on metrics and logs.',
  },
  graph_weaver: {
    label: 'Graph Weaver',
    desc:  'Built service dependency graph and detected trace anomalies.',
  },
  rca_investigator: {
    label: 'RCA Investigator',
    desc:  'Ran autonomous ReAct loop to identify root cause.',
  },
  triage: {
    label: 'Triage',
    desc:  'Classified failure type and routed to engineering team.',
  },
  reporter: {
    label: 'Reporter',
    desc:  'Generated RCA report and persisted the incident.',
  },
};

const PIPELINE_ORDER = [
  'signal_scout',
  'anomaly_hunter',
  'graph_weaver',
  'rca_investigator',
  'triage',
  'reporter',
];

function timeBetween(start, end) {
  if (!start || !end) return null;
  const s = Math.round((new Date(end) - new Date(start)) / 1000);
  return s > 0 ? `${s}s` : null;
}

/* ── InvestigationTimeline ───────────────────────────────────────── */
export default function InvestigationTimeline({ incident }) {
  const executed    = incident?.nodes_executed ?? [];
  const status      = incident?.status ?? 'open';
  const createdAt   = incident?.created_at;

  // Build display steps: executed steps are "done", rest are pending/skipped
  const executedSet = new Set(
    Array.isArray(executed) ? executed : []
  );

  const steps = PIPELINE_ORDER.map(key => ({
    key,
    ...(AGENT_META[key] ?? { label: key, desc: '' }),
    done: executedSet.has(key),
  }));

  const doneCount = steps.filter(s => s.done).length;
  const isComplete = status === 'open' && doneCount === 6;

  return (
    <div style={{
      background: '#ffffff', borderRadius: 16,
      border: '1px solid rgba(226,232,240,0.95)',
      boxShadow: '0 4px 18px -2px rgba(15,23,42,0.04)',
      padding: '16px 18px', display: 'flex', flexDirection: 'column',
      height: '100%', boxSizing: 'border-box',
    }}>
      {/* Header */}
      <div style={{
        display: 'flex', alignItems: 'center',
        justifyContent: 'space-between', marginBottom: 14,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 9 }}>
          <div style={{
            width: 24, height: 24, borderRadius: 7, background: '#eff6ff',
            border: '1px solid #dbeafe', display: 'flex', alignItems: 'center',
            justifyContent: 'center',
          }}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
              <path d="M12 2L14.5 9.5L22 12L14.5 14.5L12 22L9.5 14.5L2 12L9.5 9.5L12 2Z" fill="#2563eb"/>
            </svg>
          </div>
          <h3 style={{ fontSize: '13.5px', fontWeight: 700, color: '#0b1f3a', margin: 0 }}>
            FaultLens investigation
          </h3>
        </div>

        {/* Status badge */}
        {doneCount === 6 ? (
          <span style={{
            background: '#ecfdf5', color: '#059669',
            border: '1px solid #a7f3d0',
            fontSize: 10, fontWeight: 600,
            padding: '2px 8px', borderRadius: 9999,
          }}>
            Completed
          </span>
        ) : doneCount > 0 ? (
          <span style={{
            background: '#eff6ff', color: '#2563eb',
            border: '1px solid #bfdbfe',
            fontSize: 10, fontWeight: 600,
            padding: '2px 8px', borderRadius: 9999,
          }}>
            {doneCount}/6 agents ran
          </span>
        ) : (
          <span style={{
            background: '#fef3c7', color: '#b45309',
            border: '1px solid #fde68a',
            fontSize: 10, fontWeight: 600,
            padding: '2px 8px', borderRadius: 9999,
          }}>
            Pending
          </span>
        )}
      </div>

      {/* Progress bar */}
      <div style={{ height: 3, borderRadius: 9999, background: '#e2e8f0', overflow: 'hidden', marginBottom: 14 }}>
        <div style={{
          height: '100%', borderRadius: 9999,
          width: `${Math.round((doneCount / 6) * 100)}%`,
          background: doneCount === 6
            ? 'linear-gradient(90deg,#10b981,#06b6d4)'
            : 'linear-gradient(90deg,#2563eb,#06b6d4)',
          transition: 'width 0.6s ease',
        }}/>
      </div>

      {/* Steps */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 11 }}>
        {steps.map(step => (
          <div key={step.key} style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
            {/* Circle */}
            <div style={{
              width: 16, height: 16, borderRadius: '50%',
              background: step.done ? '#eff6ff' : '#f8fafc',
              border: step.done ? '1px solid #bfdbfe' : '1px solid #e2e8f0',
              color: step.done ? '#2563eb' : '#cbd5e1',
              fontSize: '9.5px', fontWeight: 800,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              flexShrink: 0, marginTop: 1,
            }}>
              {step.done ? '✓' : '·'}
            </div>

            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span style={{
                  fontSize: 12, fontWeight: 700,
                  color: step.done ? '#0b1f3a' : '#94a3b8',
                }}>
                  {step.label}
                </span>
                {!step.done && (
                  <span style={{ fontSize: 10, color: '#cbd5e1', fontStyle: 'italic' }}>waiting</span>
                )}
              </div>
              <p style={{
                fontSize: '10.5px',
                color: step.done ? '#475569' : '#cbd5e1',
                margin: '2px 0 0 0', lineHeight: 1.35,
              }}>
                {step.desc}
              </p>
            </div>
          </div>
        ))}
      </div>

      {/* Incident ID footer */}
      {incident?.incident_id && (
        <p style={{
          fontSize: '9.5px', color: '#cbd5e1', fontFamily: 'monospace',
          marginTop: 14, borderTop: '1px solid #f1f5f9', paddingTop: 10,
          overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
        }}>
          ID: {incident.incident_id}
        </p>
      )}
    </div>
  );
}
