'use client';

// ── Pipeline definition (order + descriptions) ────────────────────────────
const PIPELINE = [
  {
    key:   'signal_scout',
    label: 'Signal Scout',
    desc:  'Assessed available telemetry and chose analysis strategy.',
  },
  {
    key:   'anomaly_hunter',
    label: 'Anomaly Hunter',
    desc:  'Ran ML models (Z-score + Isolation Forest) on metrics and logs.',
  },
  {
    key:   'graph_weaver',
    label: 'Graph Weaver',
    desc:  'Built service dependency graph and detected trace anomalies.',
  },
  {
    key:   'rca_investigator',
    label: 'RCA Investigator',
    desc:  'Ran autonomous ReAct loop to identify root cause.',
  },
  {
    key:   'triage',
    label: 'Triage',
    desc:  'Classified failure type and routed to engineering team.',
  },
  {
    key:   'reporter',
    label: 'Reporter',
    desc:  'Generated RCA report and persisted the incident.',
  },
];

// ── Helpers ───────────────────────────────────────────────────────────────
function elapsedSeconds(start, end) {
  if (!start) return null;
  const s = new Date(end ?? Date.now());
  const e = new Date(start);
  const diff = Math.round((s - e) / 1000);
  return diff > 0 ? diff : null;
}

function formatDuration(seconds) {
  if (seconds === null) return null;
  if (seconds < 60) return `${seconds}s`;
  return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
}

// ── InvestigationTimeline ─────────────────────────────────────────────────
export default function InvestigationTimeline({ incident }) {
  if (!incident) return null;

  // nodes_executed is already a parsed array thanks to useFaultLens normaliser
  const executed   = Array.isArray(incident.nodes_executed) ? incident.nodes_executed : [];
  const runStatus  = incident.run_status;   // 'success' | 'running' | 'failed' | null
  const startedAt  = incident.run_started_at;
  const finishedAt = incident.run_finished_at;

  const executedSet  = new Set(executed);
  const doneCount    = PIPELINE.filter(s => executedSet.has(s.key)).length;
  const isRunning    = runStatus === 'running';
  const isComplete   = runStatus === 'success' && doneCount === PIPELINE.length;
  const isFailed     = runStatus === 'failed';

  const totalSecs = isComplete ? elapsedSeconds(startedAt, finishedAt) : null;

  // Status badge
  let badge;
  if (isComplete) {
    badge = {
      label: totalSecs ? `Completed in ${formatDuration(totalSecs)}` : 'Completed',
      bg: '#ecfdf5', color: '#059669', border: '#a7f3d0',
    };
  } else if (isFailed) {
    badge = { label: 'Failed', bg: '#fef2f2', color: '#dc2626', border: '#fecaca' };
  } else if (isRunning || (doneCount > 0 && doneCount < PIPELINE.length)) {
    badge = { label: `${doneCount}/6 running…`, bg: '#eff6ff', color: '#2563eb', border: '#bfdbfe' };
  } else {
    badge = { label: 'Pending', bg: '#fef3c7', color: '#b45309', border: '#fde68a' };
  }

  return (
    <div style={{
      background: '#ffffff', borderRadius: 16,
      border: '1px solid rgba(226,232,240,0.95)',
      boxShadow: '0 4px 18px -2px rgba(15,23,42,0.04)',
      padding: '16px 18px', display: 'flex', flexDirection: 'column',
      height: '100%', boxSizing: 'border-box',
    }}>

      {/* ── Header ── */}
      <div style={{
        display: 'flex', alignItems: 'center',
        justifyContent: 'space-between', marginBottom: 14,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 9 }}>
          <div style={{
            width: 24, height: 24, borderRadius: 7,
            background: '#eff6ff', border: '1px solid #dbeafe',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
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
          background: badge.bg, color: badge.color,
          border: `1px solid ${badge.border}`,
          fontSize: 10, fontWeight: 600,
          padding: '2px 8px', borderRadius: 9999, whiteSpace: 'nowrap',
        }}>
          {badge.label}
        </span>
      </div>

      {/* ── Progress bar ── */}
      <div style={{
        height: 3, borderRadius: 9999, background: '#e2e8f0',
        overflow: 'hidden', marginBottom: 14,
      }}>
        <div style={{
          height: '100%', borderRadius: 9999,
          width: `${Math.round((doneCount / PIPELINE.length) * 100)}%`,
          background: isComplete
            ? 'linear-gradient(90deg,#10b981,#06b6d4)'
            : isFailed
            ? '#ef4444'
            : 'linear-gradient(90deg,#2563eb,#06b6d4)',
          transition: 'width 0.6s ease',
        }}/>
      </div>

      {/* ── Steps ── */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10, flex: 1 }}>
        {PIPELINE.map((step, idx) => {
          const done      = executedSet.has(step.key);
          // "active" = previous step done but this one not yet, while run is in progress
          const prevDone  = idx === 0 || executedSet.has(PIPELINE[idx - 1].key);
          const active    = !done && prevDone && isRunning;

          return (
            <div key={step.key} style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
              {/* Step indicator */}
              <div style={{
                width: 16, height: 16, borderRadius: '50%', flexShrink: 0, marginTop: 1,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: '9.5px', fontWeight: 800,
                ...(done ? {
                  background: '#eff6ff', border: '1px solid #bfdbfe', color: '#2563eb',
                } : active ? {
                  background: '#fef3c7', border: '1px solid #fde68a', color: '#b45309',
                } : {
                  background: '#f8fafc', border: '1px solid #e2e8f0', color: '#cbd5e1',
                }),
              }}>
                {done ? '✓' : active ? '…' : '·'}
              </div>

              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{
                    fontSize: 12, fontWeight: 700,
                    color: done ? '#0b1f3a' : active ? '#b45309' : '#94a3b8',
                  }}>
                    {step.label}
                  </span>
                  {active && (
                    <span style={{ fontSize: 10, color: '#b45309', fontStyle: 'italic' }}>
                      running
                    </span>
                  )}
                  {!done && !active && (
                    <span style={{ fontSize: 10, color: '#cbd5e1', fontStyle: 'italic' }}>
                      waiting
                    </span>
                  )}
                </div>
                <p style={{
                  fontSize: '10.5px', margin: '2px 0 0 0', lineHeight: 1.35,
                  color: done ? '#475569' : active ? '#92400e' : '#cbd5e1',
                }}>
                  {step.desc}
                </p>
              </div>
            </div>
          );
        })}
      </div>

      {/* ── Footer: incident ID ── */}
      {incident.incident_id && (
        <p style={{
          fontSize: '9.5px', color: '#cbd5e1', fontFamily: 'monospace',
          marginTop: 12, borderTop: '1px solid #f1f5f9', paddingTop: 10,
          overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
        }}>
          ID: {incident.incident_id}
        </p>
      )}
    </div>
  );
}
