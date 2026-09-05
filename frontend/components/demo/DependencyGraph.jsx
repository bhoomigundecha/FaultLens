'use client';

/* ── helpers ─────────────────────────────────────────────────────── */

// Given an incident & services list, build a list of display nodes.
// Priority: use causal_path → fall back to services list.
function buildNodes(incident, services) {
  const causal  = incident?.causal_path ?? [];
  const rootSvc = incident?.service_id ?? '';

  // Ranked suspects map for anomaly scores
  const suspectMap = {};
  (incident?.ranked_suspects ?? []).forEach(s => {
    const key = typeof s === 'string' ? s : s.service_id;
    suspectMap[key] = typeof s === 'string' ? 0 : (s.score ?? 0);
  });

  // Determine the root-cause node — last in causal chain
  const rootCause = causal.length > 0 ? causal[causal.length - 1] : rootSvc;

  // If causal_path exists use it; otherwise fall back to services
  const ids = causal.length > 0 ? causal : services.map(s => s.service_id ?? s.name);

  return ids.map((id, idx) => ({
    id,
    label:       id,
    isRoot:      id === rootCause && causal.length > 0,
    isAnomalous: suspectMap[id] > 0.3 || id === rootCause,
    score:       suspectMap[id] ?? 0,
    // Sparkline differs: red for root cause, amber for degraded, blue for ok
  }));
}

/* ── SparklineSvg ────────────────────────────────────────────────── */
function Sparkline({ anomalous, root }) {
  const color = root ? '#ef4444' : anomalous ? '#f59e0b' : '#60a5fa';
  const fill  = root ? '#fee2e2' : anomalous ? '#fef3c7' : '#dbeafe';
  // Different paths so each service looks slightly different
  const paths = [
    { line: 'M0,18 L12,16 L24,19 L36,12 L48,15 L65,6', area: 'M0,18 L12,16 L24,19 L36,12 L48,15 L65,6 L65,22 L0,22 Z' },
    { line: 'M0,17 L14,18 L28,14 L42,16 L54,10 L65,8', area: 'M0,17 L14,18 L28,14 L42,16 L54,10 L65,8 L65,22 L0,22 Z' },
    { line: 'M0,18 L10,17 L22,14 L34,18 L44,8  L65,4', area: 'M0,18 L10,17 L22,14 L34,18 L44,8  L65,4 L65,22 L0,22 Z' },
    { line: 'M0,16 L15,17 L30,12 L45,15 L56,9  L65,7', area: 'M0,16 L15,17 L30,12 L45,15 L56,9  L65,7 L65,22 L0,22 Z' },
  ];
  const p = paths[Math.floor(Math.random() * paths.length)];
  return (
    <svg width="65" height="22" viewBox="0 0 65 22" fill="none">
      <path d={p.area} fill={fill} opacity="0.7"/>
      <path d={p.line} stroke={color} strokeWidth="1.5" fill="none"/>
    </svg>
  );
}

/* ── ServiceRow ──────────────────────────────────────────────────── */
function ServiceRow({ node }) {
  const dotColor = node.isRoot ? '#ef4444' : node.isAnomalous ? '#f59e0b' : '#10b981';
  const subText  = node.isRoot
    ? 'Root cause'
    : node.isAnomalous
    ? `Anomaly score: ${Math.round(node.score * 100)}%`
    : 'Normal';
  const subColor = node.isRoot ? '#dc2626' : node.isAnomalous ? '#b45309' : '#64748b';

  return (
    <div style={{
      background: node.isRoot ? '#fef2f2' : '#f8fafc',
      border:     node.isRoot ? '1.5px solid #fecaca' : '1px solid #e2e8f0',
      borderRadius: 12, padding: '9px 12px',
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      boxShadow: node.isRoot ? '0 4px 12px rgba(239,68,68,0.08)' : 'none',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <span style={{ width: 8, height: 8, borderRadius: '50%', background: dotColor, flexShrink: 0 }}/>
        <div>
          <p style={{ fontSize: '12.5px', fontWeight: 700, color: '#0b1f3a', margin: 0 }}>{node.label}</p>
          <p style={{ fontSize: '10.5px', color: subColor, fontWeight: node.isRoot ? 700 : 400, margin: '1px 0 0 0' }}>
            {subText}
          </p>
        </div>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <Sparkline anomalous={node.isAnomalous} root={node.isRoot} />
        {node.isRoot && (
          <span style={{
            background: '#ef4444', color: '#fff',
            fontSize: '8.5px', fontWeight: 800, letterSpacing: '0.04em',
            padding: '2px 6px', borderRadius: 9999, whiteSpace: 'nowrap',
          }}>ROOT CAUSE</span>
        )}
      </div>
    </div>
  );
}

/* ── DependencyGraph ─────────────────────────────────────────────── */
export default function DependencyGraph({ incident, services }) {
  const nodes = buildNodes(incident, services ?? []);

  return (
    <div style={{
      background: '#ffffff', borderRadius: 16,
      border: '1px solid rgba(226,232,240,0.95)',
      boxShadow: '0 4px 18px -2px rgba(15,23,42,0.04)',
      padding: '16px 18px', display: 'flex', flexDirection: 'column',
      height: '100%', boxSizing: 'border-box',
    }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 9, marginBottom: 14 }}>
        <IconBox>
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
            <circle cx="6" cy="6"  r="3" stroke="#2563eb" strokeWidth="2"/>
            <circle cx="6" cy="18" r="3" stroke="#2563eb" strokeWidth="2"/>
            <circle cx="18" cy="12" r="3" stroke="#2563eb" strokeWidth="2"/>
            <path d="M9 6H12C13.66 6 15 7.34 15 9V12"  stroke="#2563eb" strokeWidth="1.8"/>
            <path d="M9 18H12C13.66 18 15 16.66 15 15V12" stroke="#2563eb" strokeWidth="1.8"/>
          </svg>
        </IconBox>
        <h3 style={{ fontSize: '13.5px', fontWeight: 700, color: '#0b1f3a', margin: 0 }}>
          Service dependency graph
        </h3>
      </div>

      {/* Nodes */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
        {nodes.length === 0 ? (
          <p style={{ fontSize: 12, color: '#94a3b8', textAlign: 'center', padding: '24px 0' }}>
            No service data yet
          </p>
        ) : nodes.map((node, i) => (
          <div key={node.id}>
            <ServiceRow node={node} />
            {i < nodes.length - 1 && (
              <div style={{ display: 'flex', justifyContent: 'center', color: '#93c5fd', fontSize: 12, margin: '3px 0' }}>↓</div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function IconBox({ children }) {
  return (
    <div style={{
      width: 24, height: 24, borderRadius: 7, background: '#eff6ff',
      border: '1px solid #dbeafe', display: 'flex', alignItems: 'center',
      justifyContent: 'center', color: '#2563eb', flexShrink: 0,
    }}>{children}</div>
  );
}
