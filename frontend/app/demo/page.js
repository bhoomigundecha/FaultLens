'use client';
import { useState } from 'react';
import Navbar from '@/components/layout/Navbar';
import ShopflowHeader from '@/components/demo/ShopflowHeader';
import IncidentBanner from '@/components/demo/IncidentBanner';
import DependencyGraph from '@/components/demo/DependencyGraph';
import TelemetryEvidence from '@/components/demo/TelemetryEvidence';
import InvestigationTimeline from '@/components/demo/InvestigationTimeline';
import RecommendedActions from '@/components/demo/RecommendedActions';

export default function DemoPage() {
  const [selectedIncident, setSelectedIncident] = useState('Database connection pool exhaustion');

  return (
    <div className="min-h-screen flex flex-col relative"
         style={{
           background: 'linear-gradient(152deg, #cadcff 0%, #dae7fe 15%, #e8f0fe 35%, #f1f6ff 60%, #f8faff 85%, #ffffff 100%)',
         }}>

      {/* Decorative Canvas Background with Ambient Streams */}
      <svg className="absolute inset-0 w-full h-full pointer-events-none"
           style={{ zIndex: 0, minHeight: '100%' }}
           viewBox="0 0 1440 900" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
        <defs>
          <linearGradient id="demoStreamLeft" x1="100%" y1="0%" x2="0%" y2="0%">
            <stop offset="0%" stopColor="#38bdf8" stopOpacity="0.35"/>
            <stop offset="70%" stopColor="#60a5fa" stopOpacity="0.18"/>
            <stop offset="100%" stopColor="#bfdbfe" stopOpacity="0.03"/>
          </linearGradient>

          <linearGradient id="demoStreamRight" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#38bdf8" stopOpacity="0.35"/>
            <stop offset="70%" stopColor="#60a5fa" stopOpacity="0.18"/>
            <stop offset="100%" stopColor="#bfdbfe" stopOpacity="0.03"/>
          </linearGradient>

          <radialGradient id="demoCenterAura" cx="50%" cy="40%" r="50%">
            <stop offset="0%" stopColor="#38bdf8" stopOpacity="0.12"/>
            <stop offset="50%" stopColor="#60a5fa" stopOpacity="0.05"/>
            <stop offset="100%" stopColor="#ffffff" stopOpacity="0"/>
          </radialGradient>
        </defs>

        {/* Ambient Center Glow */}
        <rect x="0" y="0" width="1440" height="900" fill="url(#demoCenterAura)"/>

        {/* Topological gentle waves */}
        <path d="M-60,180 Q360,120 720,180 Q1080,240 1500,180"
              stroke="#93c5fd" strokeWidth="1.2" strokeOpacity="0.25" fill="none"/>
        <path d="M-60,480 Q360,410 720,480 Q1080,550 1500,480"
              stroke="#38bdf8" strokeWidth="1.0" strokeOpacity="0.2" fill="none"/>

        {/* Radiating streams & floating particles on edges */}
        {[
          "M 220,320 C 150,300 80,200 0,180",
          "M 220,450 C 150,460 90,470 0,470",
          "M 220,580 C 160,620 110,720 0,770",
        ].map((d, i) => (
          <path key={`s-left-${i}`} d={d} stroke="url(#demoStreamLeft)" strokeWidth={1.4} fill="none"/>
        ))}
        {[[60, 200], [90, 470], [120, 710]].map(([cx, cy], i) => (
          <circle key={`p-l-${i}`} cx={cx} cy={cy} r="2.2" fill="#38bdf8" opacity="0.6"/>
        ))}

        {[
          "M 1220,320 C 1290,300 1360,200 1440,180",
          "M 1220,450 C 1290,460 1350,470 1440,470",
          "M 1220,580 C 1280,620 1330,720 1440,770",
        ].map((d, i) => (
          <path key={`s-right-${i}`} d={d} stroke="url(#demoStreamRight)" strokeWidth={1.4} fill="none"/>
        ))}
        {[[1380, 200], [1350, 470], [1320, 710]].map(([cx, cy], i) => (
          <circle key={`p-r-${i}`} cx={cx} cy={cy} r="2.2" fill="#38bdf8" opacity="0.6"/>
        ))}
      </svg>

      {/* Main Content */}
      <div className="relative flex flex-col min-h-screen" style={{ zIndex: 1 }}>
        <Navbar />

        <main style={{
          maxWidth: 1140,
          margin: '0 auto',
          width: '100%',
          paddingTop: '82px',
          paddingBottom: '32px',
          paddingLeft: '20px',
          paddingRight: '20px',
          boxSizing: 'border-box',
        }}>
          {/* Back to home link */}
          <div style={{ marginBottom: 10 }}>
            <a
              href="/"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 5,
                fontSize: '12px',
                fontWeight: 600,
                color: '#475569',
                textDecoration: 'none',
                transition: 'color 0.15s ease',
              }}
              onMouseEnter={e => e.currentTarget.style.color = '#2563eb'}
              onMouseLeave={e => e.currentTarget.style.color = '#475569'}
            >
              ← Back to home
            </a>
          </div>

          {/* Top Platform Identity & Controls */}
          <ShopflowHeader
            selectedIncident={selectedIncident}
            onSelectIncident={setSelectedIncident}
          />

          {/* Active Incident Banner */}
          <IncidentBanner />

          {/* Middle 3-Column Diagnostic Dashboard */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: '1.02fr 1.16fr 1fr',
            gap: 16,
            alignItems: 'stretch',
          }}>
            {/* Column 1: Dependency Graph */}
            <DependencyGraph />

            {/* Column 2: Evidence from telemetry */}
            <TelemetryEvidence />

            {/* Column 3: FaultLens investigation */}
            <InvestigationTimeline />
          </div>

          {/* Bottom Row: Recommended Actions */}
          <RecommendedActions />
        </main>
      </div>

    </div>
  );
}
