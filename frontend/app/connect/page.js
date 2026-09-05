'use client';
import { useState } from 'react';
import Navbar from '@/components/layout/Navbar';
import Step1Environment from '@/components/connect/Step1Environment';
import Step2Details from '@/components/connect/Step2Details';
import Step3Verify from '@/components/connect/Step3Verify';

export default function ConnectPage() {
  const [step, setStep] = useState(1);
  const [selectedEnv, setSelectedEnv] = useState('self-hosted');
  const [selectedLang, setSelectedLang] = useState('nodejs');
  const [selectedDeploy, setSelectedDeploy] = useState('docker');
  const [selectedSignals, setSelectedSignals] = useState(['metrics', 'logs', 'traces']);

  const handleToggleSignal = (id) => {
    setSelectedSignals(prev =>
      prev.includes(id) ? prev.filter(s => s !== id) : [...prev, id]
    );
  };

  return (
    <div className="min-h-screen flex flex-col relative"
         style={{
           background: 'linear-gradient(152deg, #cadcff 0%, #dae7fe 15%, #e8f0fe 35%, #f1f6ff 60%, #f8faff 85%, #ffffff 100%)',
         }}>

      {/* Decorative Canvas Background with Left & Right Radiating Streams */}
      <svg className="absolute inset-0 w-full h-full pointer-events-none"
           style={{ zIndex: 0, minHeight: '100%' }}
           viewBox="0 0 1440 900" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
        <defs>
          <linearGradient id="streamLeft" x1="100%" y1="0%" x2="0%" y2="0%">
            <stop offset="0%" stopColor="#38bdf8" stopOpacity="0.4"/>
            <stop offset="70%" stopColor="#60a5fa" stopOpacity="0.2"/>
            <stop offset="100%" stopColor="#bfdbfe" stopOpacity="0.03"/>
          </linearGradient>

          <linearGradient id="streamRight" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#38bdf8" stopOpacity="0.4"/>
            <stop offset="70%" stopColor="#60a5fa" stopOpacity="0.2"/>
            <stop offset="100%" stopColor="#bfdbfe" stopOpacity="0.03"/>
          </linearGradient>

          <radialGradient id="centerAura" cx="50%" cy="45%" r="50%">
            <stop offset="0%" stopColor="#38bdf8" stopOpacity="0.12"/>
            <stop offset="50%" stopColor="#60a5fa" stopOpacity="0.06"/>
            <stop offset="100%" stopColor="#ffffff" stopOpacity="0"/>
          </radialGradient>
        </defs>

        {/* Ambient Center Glow */}
        <rect x="0" y="0" width="1440" height="900" fill="url(#centerAura)"/>

        {/* Symmetrical sweeping topological waves */}
        <path d="M-60,200 Q360,130 720,200 Q1080,270 1500,200"
              stroke="#93c5fd" strokeWidth="1.2" strokeOpacity="0.28" fill="none"/>
        <path d="M-60,330 Q360,250 720,330 Q1080,410 1500,330"
              stroke="#38bdf8" strokeWidth="1.0" strokeOpacity="0.22" fill="none"/>
        <path d="M-60,540 Q360,460 720,540 Q1080,620 1500,540"
              stroke="#93c5fd" strokeWidth="1.0" strokeOpacity="0.24" fill="none"/>

        {/* Radiating fiber stream lines on the far LEFT */}
        {[
          "M 260,380 C 180,360 100,240 0,220",
          "M 260,420 C 170,410 90,340 0,330",
          "M 260,460 C 180,470 110,480 0,480",
          "M 260,500 C 190,530 120,620 0,640",
          "M 260,540 C 200,580 140,700 0,760",
        ].map((d, i) => (
          <path key={`stream-left-${i}`} d={d}
                stroke="url(#streamLeft)" strokeWidth={1.4} fill="none"/>
        ))}

        {/* Floating node particles on the LEFT */}
        {[
          [80, 240], [40, 360], [110, 480], [60, 620], [130, 680]
        ].map(([cx, cy], i) => (
          <circle key={`p-left-${i}`} cx={cx} cy={cy} r="2.2" fill="#38bdf8" opacity="0.65"/>
        ))}

        {/* Radiating fiber stream lines on the far RIGHT */}
        {[
          "M 1180,380 C 1260,360 1340,240 1440,220",
          "M 1180,420 C 1270,410 1350,340 1440,330",
          "M 1180,460 C 1260,470 1330,480 1440,480",
          "M 1180,500 C 1250,530 1320,620 1440,640",
          "M 1180,540 C 1240,580 1300,700 1440,760",
        ].map((d, i) => (
          <path key={`stream-right-${i}`} d={d}
                stroke="url(#streamRight)" strokeWidth={1.4} fill="none"/>
        ))}

        {/* Floating node particles on the RIGHT */}
        {[
          [1360, 240], [1400, 360], [1330, 480], [1380, 620], [1310, 680]
        ].map(([cx, cy], i) => (
          <circle key={`p-right-${i}`} cx={cx} cy={cy} r="2.2" fill="#38bdf8" opacity="0.65"/>
        ))}
      </svg>

      {/* Content */}
      <div className="relative flex flex-col min-h-screen" style={{ zIndex: 1 }}>
        <Navbar />

        <main style={{
          paddingTop: '74px',
          paddingBottom: '24px',
          paddingLeft: '20px',
          paddingRight: '20px',
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          width: '100%',
          boxSizing: 'border-box',
        }}>
          {step === 1 && (
            <Step1Environment
              selectedEnv={selectedEnv}
              onSelectEnv={setSelectedEnv}
              onContinue={() => setStep(2)}
            />
          )}

          {step === 2 && (
            <Step2Details
              selectedEnv={selectedEnv}
              selectedLang={selectedLang}
              onSelectLang={setSelectedLang}
              selectedDeploy={selectedDeploy}
              onSelectDeploy={setSelectedDeploy}
              selectedSignals={selectedSignals}
              onToggleSignal={handleToggleSignal}
              onBack={() => setStep(1)}
              onContinue={() => setStep(3)}
            />
          )}

          {step === 3 && (
            <Step3Verify
              selectedEnv={selectedEnv}
              selectedLang={selectedLang}
              selectedDeploy={selectedDeploy}
              selectedSignals={selectedSignals}
              onBack={() => setStep(2)}
            />
          )}
        </main>
      </div>

    </div>
  );
}
