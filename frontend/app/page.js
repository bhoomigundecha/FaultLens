import Navbar      from '@/components/layout/Navbar';
import HeroSection from '@/components/landing/HeroSection';
import DemoSection from '@/components/landing/DemoSection';

export default function HomePage() {
  return (
    <div className="h-full flex flex-col overflow-hidden relative"
         style={{
           background: 'linear-gradient(148deg, #c5d9ff 0%, #d8e7ff 14%, #e6eeff 32%, #eef4ff 55%, #f5f8ff 78%, #fafbff 100%)',
         }}>

      {/* Decorative background */}
      <svg className="absolute inset-0 w-full h-full pointer-events-none"
           style={{ zIndex: 0 }}
           viewBox="0 0 1440 900" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
        <defs>
          <linearGradient id="l1" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#93c5fd" stopOpacity="0.22"/>
            <stop offset="100%" stopColor="#bfdbfe" stopOpacity="0.04"/>
          </linearGradient>
        </defs>
        <path d="M-80,200 Q300,120 620,210 Q940,300 1200,170 Q1380,80 1520,150"
              stroke="url(#l1)" strokeWidth="1.2" fill="none"/>
        <path d="M-80,360 Q250,280 550,360 Q850,440 1150,320 Q1350,240 1520,300"
              stroke="url(#l1)" strokeWidth="0.8" fill="none"/>
        <path d="M-80,680 Q300,610 600,680 Q900,750 1180,650 Q1360,580 1520,640"
              stroke="url(#l1)" strokeWidth="0.9" fill="none"/>
        {/* Dots */}
        {[100,230,370,510,650,800,950,1100,1250,1390].map((x,i)=>
          [90,200,320,440,570,680,790].map((y,j)=>(
            <circle key={`${i}${j}`} cx={x+(j%2)*18} cy={y} r="1.2"
                    fill="#93c5fd" opacity="0.25"/>
          ))
        )}
      </svg>

      {/* Content — above the bg SVG */}
      <div className="relative flex flex-col h-full" style={{ zIndex: 1 }}>
        <Navbar />
        <div className="flex-none">
          <HeroSection />
        </div>
        <div className="flex-1 min-h-0 overflow-hidden">
          <DemoSection />
        </div>
      </div>
    </div>
  );
}
