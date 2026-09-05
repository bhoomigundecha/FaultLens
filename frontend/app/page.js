import Navbar      from '@/components/layout/Navbar';
import HeroSection from '@/components/landing/HeroSection';
import DemoSection from '@/components/landing/DemoSection';

export default function HomePage() {
  return (
    <div className="min-h-screen flex flex-col relative"
         style={{
           background: 'linear-gradient(152deg, #cadcff 0%, #dae7fe 15%, #e8f0fe 35%, #f1f6ff 60%, #f8faff 85%, #ffffff 100%)',
         }}>

      {/* Decorative Canvas Background (Symmetrical & Uniform) */}
      <svg className="absolute inset-0 w-full h-full pointer-events-none"
           style={{ zIndex: 0, minHeight: '100%' }}
           viewBox="0 0 1440 900" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
        <defs>
          <linearGradient id="curveGrad1" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#60a5fa" stopOpacity="0.25"/>
            <stop offset="50%" stopColor="#93c5fd" stopOpacity="0.14"/>
            <stop offset="100%" stopColor="#bfdbfe" stopOpacity="0.04"/>
          </linearGradient>

          <linearGradient id="curveGrad2" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#38bdf8" stopOpacity="0.22"/>
            <stop offset="60%" stopColor="#93c5fd" stopOpacity="0.12"/>
            <stop offset="100%" stopColor="#bfdbfe" stopOpacity="0.03"/>
          </linearGradient>

          <radialGradient id="centerBacklight" cx="50%" cy="58%" r="45%">
            <stop offset="0%" stopColor="#38bdf8" stopOpacity="0.14"/>
            <stop offset="35%" stopColor="#60a5fa" stopOpacity="0.07"/>
            <stop offset="70%" stopColor="#93c5fd" stopOpacity="0.02"/>
            <stop offset="100%" stopColor="#ffffff" stopOpacity="0"/>
          </radialGradient>
        </defs>

        {/* Ambient Center Glow */}
        <rect x="0" y="0" width="1440" height="900" fill="url(#centerBacklight)"/>

        {/* Uniform Symmetrical Contour Waves (Centered around x=720) */}
        <path d="M-60,220 Q360,140 720,220 Q1080,300 1500,220"
              stroke="url(#curveGrad1)" strokeWidth="1.2" fill="none"/>
        <path d="M-60,340 Q360,260 720,340 Q1080,420 1500,340"
              stroke="url(#curveGrad2)" strokeWidth="1.0" fill="none"/>
        <path d="M-60,470 Q360,390 720,470 Q1080,550 1500,470"
              stroke="url(#curveGrad1)" strokeWidth="1.1" fill="none"/>
        <path d="M-60,610 Q360,530 720,610 Q1080,690 1500,610"
              stroke="url(#curveGrad2)" strokeWidth="1.0" fill="none"/>
        <path d="M-60,750 Q360,680 720,750 Q1080,820 1500,750"
              stroke="url(#curveGrad1)" strokeWidth="0.9" fill="none"/>

        {/* UNIFORM PLEXUS NETWORK — LEFT (Raw Telemetry side) */}
        <g stroke="#93c5fd" strokeWidth="0.7" strokeOpacity="0.28">
          <line x1="80"  y1="380" x2="150" y2="420"/>
          <line x1="150" y1="420" x2="110" y2="490"/>
          <line x1="110" y1="490" x2="180" y2="530"/>
          <line x1="180" y1="530" x2="240" y2="470"/>
          <line x1="150" y1="420" x2="240" y2="470"/>
          <line x1="240" y1="470" x2="210" y2="580"/>
          <line x1="180" y1="530" x2="210" y2="580"/>
          <line x1="110" y1="490" x2="130" y2="590"/>
        </g>
        {[
          [80,380],[150,420],[110,490],[180,530],[240,470],[210,580],[130,590]
        ].map(([cx, cy], i) => (
          <circle key={`plexus-left-${i}`} cx={cx} cy={cy} r="2.0"
                  fill="#60a5fa" opacity="0.5"/>
        ))}

        {/* UNIFORM PLEXUS NETWORK — RIGHT (Clear Answers side) */}
        <g stroke="#93c5fd" strokeWidth="0.7" strokeOpacity="0.28">
          <line x1="1360" y1="380" x2="1290" y2="420"/>
          <line x1="1290" y1="420" x2="1330" y2="490"/>
          <line x1="1330" y1="490" x2="1260" y2="530"/>
          <line x1="1260" y1="530" x2="1200" y2="470"/>
          <line x1="1290" y1="420" x2="1200" y2="470"/>
          <line x1="1200" y1="470" x2="1230" y2="580"/>
          <line x1="1260" y1="530" x2="1230" y2="580"/>
          <line x1="1330" y1="490" x2="1310" y2="590"/>
        </g>
        {[
          [1360,380],[1290,420],[1330,490],[1260,530],[1200,470],[1230,580],[1310,590]
        ].map(([cx, cy], i) => (
          <circle key={`plexus-right-${i}`} cx={cx} cy={cy} r="2.0"
                  fill="#60a5fa" opacity="0.5"/>
        ))}

        {/* Balanced Grid Constellation across the whole canvas */}
        {[140, 280, 420, 560, 700, 840, 980, 1120, 1260, 1380].map((x, i) =>
          [100, 220, 360, 500, 640, 780].map((y, j) => (
            <circle key={`dot-${i}-${j}`} cx={x + (j % 2) * 16} cy={y} r="1.3"
                    fill="#93c5fd" opacity="0.22"/>
          ))
        )}
      </svg>

      {/* Content Layer */}
      <div className="relative flex flex-col min-h-screen pb-8" style={{ zIndex: 1 }}>
        <Navbar />
        <div className="flex-none">
          <HeroSection />
        </div>
        <div className="flex-1">
          <DemoSection />
        </div>
      </div>
    </div>
  );
}
