'use client';

/* ── helpers ─────────────────────────────────────────────────────── */
function timeAgo(isoString) {
  if (!isoString) return '';
  const diff = Math.round((Date.now() - new Date(isoString).getTime()) / 1000);
  if (diff < 60)  return `${diff} second${diff !== 1 ? 's' : ''} ago`;
  if (diff < 3600) {
    const m = Math.floor(diff / 60);
    return `${m} minute${m !== 1 ? 's' : ''} ago`;
  }
  const h = Math.floor(diff / 3600);
  return `${h} hour${h !== 1 ? 's' : ''} ago`;
}

function severityFromScore(confidence) {
  if (!confidence) return { label: 'Unknown', bg: '#f1f5f9', color: '#64748b' };
  if (confidence >= 0.7) return { label: 'High',   bg: '#fee2e2', color: '#dc2626' };
  if (confidence >= 0.4) return { label: 'Medium', bg: '#fef3c7', color: '#b45309' };
  return                        { label: 'Low',    bg: '#f0fdf4', color: '#15803d' };
}

function humaniseFailureType(type) {
  if (!type) return 'Anomaly Detected';
  return type
    .split('_')
    .map(w => w.charAt(0) + w.slice(1).toLowerCase())
    .join(' ');
}

function causalRoot(incident) {
  const path = incident.causal_path ?? [];
  if (path.length > 0) return path[path.length - 1];
  const suspects = incident.ranked_suspects ?? [];
  if (suspects.length > 0) return suspects[0].service_id ?? suspects[0];
  return incident.service_id ?? '—';
}

/* ── IncidentBanner ──────────────────────────────────────────────── */
export default function IncidentBanner({ incident }) {
  if (!incident) return null;

  const sev       = severityFromScore(incident.confidence);
  const root      = causalRoot(incident);
  const causal    = incident.causal_path ?? [];
  const chainText = causal.length > 1 ? causal.join(' → ') : root;
  const pct       = incident.confidence != null
    ? `${Math.round(incident.confidence * 100)}%`
    : '—';

  return (
    <div style={{
      background: '#ffffff',
      borderRadius: 16,
      border: '1px solid rgba(226,232,240,0.95)',
      boxShadow: '0 4px 20px -2px rgba(15,23,42,0.04),0 2px 6px -1px rgba(15,23,42,0.02)',
      padding: '18px 24px',
      display: 'grid',
      gridTemplateColumns: '1.45fr 1fr',
      gap: 28,
      alignItems: 'center',
      marginBottom: 16,
    }}>

      {/* ── Left: incident summary ── */}
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 14 }}>
        {/* Red alert circle */}
        <div style={{
          width: 36, height: 36, borderRadius: '50%',
          background: '#fee2e2', border: '1px solid #fecaca',
          color: '#ef4444', display: 'flex', alignItems: 'center',
          justifyContent: 'center', fontWeight: 800, fontSize: 17, flexShrink: 0,
        }}>!</div>

        <div>
          {/* badge + timestamp */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
            <span style={{
              background: '#fee2e2', color: '#dc2626',
              fontSize: '9.5px', fontWeight: 800, letterSpacing: '0.04em',
              padding: '2px 7px', borderRadius: 9999, textTransform: 'uppercase',
            }}>
              Incident Detected
            </span>
            {incident.created_at && (
              <span style={{ fontSize: '11.5px', color: '#64748b' }}>
                Detected {timeAgo(incident.created_at)}
              </span>
            )}
          </div>

          {/* Title */}
          <h2 style={{
            fontSize: 19, fontWeight: 800, color: '#0b1f3a',
            margin: '0 0 6px 0', letterSpacing: '-0.02em',
          }}>
            {humaniseFailureType(incident.failure_type)}
          </h2>

          {/* Service badge */}
          <div style={{ marginBottom: 8 }}>
            <span style={{
              background: '#eff6ff', color: '#2563eb',
              border: '1px solid #dbeafe', borderRadius: 9999,
              padding: '2px 10px', fontSize: '11.5px', fontWeight: 700,
            }}>
              {incident.service_id}
            </span>
          </div>

          {/* Description — use start of rca_report if available */}
          <p style={{ fontSize: 12, color: '#475569', lineHeight: 1.45, margin: '0 0 12px 0' }}>
            {incident.rca_report
              ? incident.rca_report
                  .replace(/#{1,3}\s[^\n]+\n/g, '')  // strip markdown headers
                  .replace(/\*\*/g, '')               // strip bold markers
                  .trim()
                  .slice(0, 200)
                  .concat('…')
              : `Anomaly detected on ${incident.service_id}. FaultLens is analysing the incident.`
            }
          </p>

          {/* Meta tags */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 14, flexWrap: 'wrap' }}>
            <MetaTag label="Severity" value={sev.label} bg={sev.bg} color={sev.color} />
            <MetaTag
              label="Confidence"
              value={pct}
              bg="#eff6ff" color="#2563eb"
            />
            {incident.team_routing && (
              <MetaTag
                label="Routed to"
                value={incident.team_routing}
                bg="#eff6ff" color="#2563eb"
                border="1px solid #dbeafe"
              />
            )}
          </div>
        </div>
      </div>

      {/* ── Right: root cause ── */}
      <div style={{
        borderLeft: '1px solid #f1f5f9', paddingLeft: 24,
        display: 'flex', alignItems: 'flex-start', gap: 12,
      }}>
        {/* Crosshair icon */}
        <div style={{
          width: 32, height: 32, borderRadius: '50%',
          background: '#eff6ff', border: '1px solid #dbeafe',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          color: '#2563eb', flexShrink: 0,
        }}>
          <svg width="16" height="16" viewBox="0 0 20 20" fill="none">
            <circle cx="10" cy="10" r="6" stroke="#2563eb" strokeWidth="1.4"/>
            <circle cx="10" cy="10" r="2" fill="#2563eb"/>
            <line x1="10" y1="1"  x2="10" y2="4"  stroke="#2563eb" strokeWidth="1.4" strokeLinecap="round"/>
            <line x1="10" y1="16" x2="10" y2="19" stroke="#2563eb" strokeWidth="1.4" strokeLinecap="round"/>
            <line x1="1"  y1="10" x2="4"  y2="10" stroke="#2563eb" strokeWidth="1.4" strokeLinecap="round"/>
            <line x1="16" y1="10" x2="19" y2="10" stroke="#2563eb" strokeWidth="1.4" strokeLinecap="round"/>
          </svg>
        </div>

        <div>
          <h3 style={{ fontSize: 13, fontWeight: 700, color: '#0b1f3a', margin: 0 }}>
            Root cause
          </h3>

          <div style={{ margin: '6px 0' }}>
            <span style={{
              background: '#eff6ff', color: '#2563eb',
              border: '1px solid #bfdbfe', borderRadius: 9999,
              padding: '3px 12px', fontSize: 12, fontWeight: 700,
              display: 'inline-block',
            }}>
              {chainText || root}
            </span>
          </div>

          {/* Confidence bar */}
          {incident.confidence != null && (
            <div style={{ marginBottom: 8 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                <span style={{ fontSize: 11, color: '#64748b' }}>Confidence</span>
                <span style={{ fontSize: 11, fontWeight: 700, color: '#2563eb' }}>{pct}</span>
              </div>
              <div style={{ height: 4, borderRadius: 9999, background: '#e2e8f0', overflow: 'hidden' }}>
                <div style={{
                  height: '100%', borderRadius: 9999,
                  width: `${Math.round(incident.confidence * 100)}%`,
                  background: 'linear-gradient(90deg,#2563eb,#06b6d4)',
                  transition: 'width 0.6s ease',
                }}/>
              </div>
            </div>
          )}

          <p style={{ fontSize: '11.5px', color: '#475569', lineHeight: 1.4, margin: '0 0 10px 0' }}>
            {incident.failure_type
              ? `${humaniseFailureType(incident.failure_type)} identified as the most probable root cause.`
              : 'Investigation in progress…'}
          </p>
        </div>
      </div>
    </div>
  );
}

/* ── small helper ────────────────────────────────────────────────── */
function MetaTag({ label, value, bg, color, border }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
      <span style={{ fontSize: 11, color: '#64748b', fontWeight: 500 }}>{label}</span>
      <span style={{
        background: bg, color, border: border ?? 'none',
        fontSize: 11, fontWeight: 700, padding: '2px 8px', borderRadius: 9999,
      }}>{value}</span>
    </div>
  );
}
