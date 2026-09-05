'use client';

import { useState, useEffect } from 'react';
import Navbar            from '@/components/layout/Navbar';
import ShopflowHeader    from '@/components/demo/ShopflowHeader';
import IncidentBanner    from '@/components/demo/IncidentBanner';
import DependencyGraph   from '@/components/demo/DependencyGraph';
import TelemetryEvidence from '@/components/demo/TelemetryEvidence';
import InvestigationTimeline from '@/components/demo/InvestigationTimeline';
import RecommendedActions from '@/components/demo/RecommendedActions';
import { useFaultLens }  from '@/hooks/useFaultLens';

/* ── tiny "last updated" ticker ─────────────────────────────────── */
function LastUpdated({ date, error }) {
  const [label, setLabel] = useState('');
  useEffect(() => {
    if (!date) return;
    const tick = () => {
      const s = Math.round((Date.now() - date.getTime()) / 1000);
      setLabel(s < 5 ? 'just now' : `${s}s ago`);
    };
    tick();
    const id = setInterval(tick, 5000);
    return () => clearInterval(id);
  }, [date]);

  if (error) return (
    <span style={{ fontSize: 11, color: '#ef4444', fontWeight: 600 }}>
      ⚠ Backend unreachable
    </span>
  );
  if (!date) return null;
  return (
    <span style={{ fontSize: 11, color: '#94a3b8' }}>
      Updated {label}
    </span>
  );
}

/* ── skeleton card ───────────────────────────────────────────────── */
function Skeleton({ height = 180 }) {
  return (
    <div style={{
      height,
      borderRadius: 16,
      background: 'linear-gradient(90deg,#f1f5f9 25%,#e2e8f0 50%,#f1f5f9 75%)',
      backgroundSize: '200% 100%',
      animation: 'shimmer 1.4s infinite linear',
    }} />
  );
}

/* ── EmptyState ──────────────────────────────────────────────────── */
function EmptyState() {
  return (
    <div style={{
      textAlign: 'center', padding: '48px 24px',
      background: '#fff', borderRadius: 16,
      border: '1px solid #e2e8f0',
    }}>
      <div style={{ fontSize: 32, marginBottom: 12 }}>🔍</div>
      <p style={{ fontSize: 15, fontWeight: 700, color: '#0b1f3a', marginBottom: 6 }}>
        No incidents yet
      </p>
      <p style={{ fontSize: 13, color: '#64748b', maxWidth: 360, margin: '0 auto' }}>
        FaultLens is monitoring your services. Inject a fault scenario above or wait
        for the agent worker to detect anomalies automatically.
      </p>
    </div>
  );
}

/* ── DemoPage ────────────────────────────────────────────────────── */
export default function DemoPage() {
  const { incidents, services, loading, error, lastUpdated, refetch } = useFaultLens();

  // Auto-select newest incident; let the user pick another from the header
  const [selectedId, setSelectedId] = useState(null);
  useEffect(() => {
    if (incidents.length > 0 && selectedId === null) {
      setSelectedId(incidents[0].incident_id);
    }
  }, [incidents, selectedId]);

  const incident = incidents.find(i => i.incident_id === selectedId) ?? incidents[0] ?? null;

  return (
    <div className="min-h-screen flex flex-col relative"
         style={{
           background:
             'linear-gradient(152deg,#cadcff 0%,#dae7fe 15%,#e8f0fe 35%,#f1f6ff 60%,#f8faff 85%,#ffffff 100%)',
         }}>

      {/* ── Background decoration (unchanged) ── */}
      <svg className="absolute inset-0 w-full h-full pointer-events-none"
           style={{ zIndex: 0, minHeight: '100%' }}
           viewBox="0 0 1440 900" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
        <defs>
          <linearGradient id="sl" x1="100%" y1="0%" x2="0%" y2="0%">
            <stop offset="0%"   stopColor="#38bdf8" stopOpacity="0.35"/>
            <stop offset="70%"  stopColor="#60a5fa" stopOpacity="0.18"/>
            <stop offset="100%" stopColor="#bfdbfe" stopOpacity="0.03"/>
          </linearGradient>
          <linearGradient id="sr" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%"   stopColor="#38bdf8" stopOpacity="0.35"/>
            <stop offset="70%"  stopColor="#60a5fa" stopOpacity="0.18"/>
            <stop offset="100%" stopColor="#bfdbfe" stopOpacity="0.03"/>
          </linearGradient>
          <radialGradient id="ca" cx="50%" cy="40%" r="50%">
            <stop offset="0%"   stopColor="#38bdf8" stopOpacity="0.12"/>
            <stop offset="50%"  stopColor="#60a5fa" stopOpacity="0.05"/>
            <stop offset="100%" stopColor="#ffffff" stopOpacity="0"/>
          </radialGradient>
        </defs>
        <rect x="0" y="0" width="1440" height="900" fill="url(#ca)"/>
        <path d="M-60,180 Q360,120 720,180 Q1080,240 1500,180" stroke="#93c5fd" strokeWidth="1.2" strokeOpacity="0.25" fill="none"/>
        <path d="M-60,480 Q360,410 720,480 Q1080,550 1500,480" stroke="#38bdf8" strokeWidth="1.0" strokeOpacity="0.2"  fill="none"/>
        {["M 220,320 C 150,300 80,200 0,180","M 220,450 C 150,460 90,470 0,470","M 220,580 C 160,620 110,720 0,770"]
          .map((d,i) => <path key={i} d={d} stroke="url(#sl)" strokeWidth="1.4" fill="none"/>)}
        {["M 1220,320 C 1290,300 1360,200 1440,180","M 1220,450 C 1290,460 1350,470 1440,470","M 1220,580 C 1280,620 1330,720 1440,770"]
          .map((d,i) => <path key={i} d={d} stroke="url(#sr)" strokeWidth="1.4" fill="none"/>)}
      </svg>

      {/* ── shimmer keyframe ── */}
      <style>{`@keyframes shimmer{0%{background-position:200% 0}100%{background-position:-200% 0}}`}</style>

      {/* ── Content ── */}
      <div className="relative flex flex-col min-h-screen" style={{ zIndex: 1 }}>
        <Navbar />

        <main style={{
          maxWidth: 1140, margin: '0 auto', width: '100%',
          paddingTop: 82, paddingBottom: 32,
          paddingLeft: 20, paddingRight: 20, boxSizing: 'border-box',
        }}>

          {/* Back link + live status */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
            <a href="/" style={{ fontSize: 12, fontWeight: 600, color: '#475569', textDecoration: 'none' }}
               onMouseEnter={e => (e.currentTarget.style.color = '#2563eb')}
               onMouseLeave={e => (e.currentTarget.style.color = '#475569')}>
              ← Back to home
            </a>
            <LastUpdated date={lastUpdated} error={error} />
          </div>

          {/* Header */}
          <ShopflowHeader
            incidents={incidents}
            services={services}
            selectedId={selectedId}
            onSelectIncident={setSelectedId}
            onRefresh={refetch}
          />

          {/* Loading skeleton */}
          {loading && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              <Skeleton height={140} />
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 16 }}>
                <Skeleton height={320} /><Skeleton height={320} /><Skeleton height={320} />
              </div>
              <Skeleton height={80} />
            </div>
          )}

          {/* No data yet */}
          {!loading && !incident && <EmptyState />}

          {/* Live dashboard */}
          {!loading && incident && (
            <>
              <IncidentBanner incident={incident} />

              <div style={{
                display: 'grid',
                gridTemplateColumns: '1.02fr 1.16fr 1fr',
                gap: 16, alignItems: 'stretch',
              }}>
                <DependencyGraph incident={incident} services={services} />
                <TelemetryEvidence incident={incident} />
                <InvestigationTimeline incident={incident} />
              </div>

              <RecommendedActions incident={incident} />
            </>
          )}

        </main>
      </div>
    </div>
  );
}
