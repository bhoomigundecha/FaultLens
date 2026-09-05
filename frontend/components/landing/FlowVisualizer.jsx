'use client';
export default function FlowVisualizer() {
  return (
    <div style={{ position: 'relative', width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>

      {/* Central glowing bar */}
      <div className="anim-glow" style={{
        position: 'absolute',
        left: '50%', transform: 'translateX(-50%)',
        top: '8%', bottom: '8%',
        width: 3, borderRadius: 9999,
        background: 'linear-gradient(to bottom, #06b6d4, #3b82f6, #06b6d4)',
        boxShadow: '0 0 14px 3px rgba(6,182,212,0.55), 0 0 36px 8px rgba(59,130,246,0.28)',
        zIndex: 20,
      }}/>

      {/* Animated lines */}
      <svg style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }}
           viewBox="0 0 200 500" preserveAspectRatio="none" aria-hidden="true">
        <defs>
          <linearGradient id="g1" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%"   stopColor="#06b6d4" stopOpacity="0.85"/>
            <stop offset="50%"  stopColor="#3b82f6" stopOpacity="1"/>
            <stop offset="100%" stopColor="#06b6d4" stopOpacity="0.85"/>
          </linearGradient>
          <linearGradient id="g2" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%"   stopColor="#818cf8" stopOpacity="0.7"/>
            <stop offset="50%"  stopColor="#3b82f6" stopOpacity="1"/>
            <stop offset="100%" stopColor="#818cf8" stopOpacity="0.7"/>
          </linearGradient>
          <linearGradient id="g3" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%"   stopColor="#06b6d4" stopOpacity="0.5"/>
            <stop offset="50%"  stopColor="#60a5fa" stopOpacity="0.9"/>
            <stop offset="100%" stopColor="#06b6d4" stopOpacity="0.5"/>
          </linearGradient>
          <filter id="glow">
            <feGaussianBlur in="SourceGraphic" stdDeviation="2.5" result="b"/>
            <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
          </filter>
        </defs>

        {[
          { d:"M0,45  Q100,90  100,250 Q100,410 200,455", g:"g1", w:1.9, off:900, t:"2.8s", delay:"0s"    },
          { d:"M0,90  Q100,135 100,250 Q100,370 200,400", g:"g2", w:1.5, off:800, t:"2.8s", delay:"0.3s"  },
          { d:"M0,140 Q100,175 100,250 Q100,330 200,360", g:"g3", w:1.2, off:700, t:"2.8s", delay:"0.6s"  },
          { d:"M0,205 Q100,228 100,250 Q100,278 200,300", g:"g2", w:2.0, off:600, t:"2.4s", delay:"0.15s" },
          { d:"M0,250 L200,250",                          g:"g1", w:2.3, off:500, t:"2.4s", delay:"0s"    },
          { d:"M0,295 Q100,272 100,250 Q100,222 200,200", g:"g3", w:1.7, off:600, t:"2.4s", delay:"0.45s" },
          { d:"M0,355 Q100,312 100,250 Q100,185 200,150", g:"g1", w:1.2, off:700, t:"2.8s", delay:"0.8s"  },
          { d:"M0,405 Q100,355 100,250 Q100,148 200,100", g:"g2", w:1.5, off:800, t:"2.8s", delay:"1.1s"  },
          { d:"M0,450 Q100,390 100,250 Q100,115 200,55",  g:"g3", w:1.9, off:900, t:"2.8s", delay:"1.4s"  },
        ].map(({ d, g, w, off, t, delay }, i) => (
          <path key={i} d={d} stroke={`url(#${g})`} strokeWidth={w} fill="none" filter="url(#glow)"
                style={{ strokeDasharray: off, strokeDashoffset: off,
                         animation: `flowLine ${t} ease-in-out ${delay} infinite` }}/>
        ))}
      </svg>

      {/* Floating doc icons on edges */}
      {[{ top: '25%', right: 4 }, { bottom: '25%', left: 4 }].map((pos, i) => (
        <div key={i} className="anim-float" style={{
          animationDelay: `${i * 0.8}s`,
          position: 'absolute', ...pos,
          width: 30, height: 30, borderRadius: '50%',
          background: 'rgba(255,255,255,0.88)',
          border: '1px solid rgba(147,197,253,0.5)',
          boxShadow: '0 2px 10px rgba(37,99,235,0.1)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 10,
        }}>
          <svg width="13" height="13" viewBox="0 0 13 13" fill="none">
            <rect x="1.5" y="1" width="9" height="11" rx="1.5" stroke="#3b82f6" strokeWidth="1.1"/>
            <line x1="3.5" y1="4.5" x2="9" y2="4.5" stroke="#3b82f6" strokeWidth="0.85"/>
            <line x1="3.5" y1="6.5" x2="9" y2="6.5" stroke="#3b82f6" strokeWidth="0.85"/>
            <line x1="3.5" y1="8.5" x2="6.5" y2="8.5" stroke="#3b82f6" strokeWidth="0.85"/>
          </svg>
        </div>
      ))}
    </div>
  );
}
