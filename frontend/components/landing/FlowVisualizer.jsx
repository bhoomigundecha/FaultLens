'use client';

export default function FlowVisualizer() {
  return (
    <div style={{
      position: 'relative',
      width: '100%',
      height: '100%',
      minHeight: 420,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      overflow: 'visible',
    }}>

      {/* ── 1. LUMINOUS BACKGROUND BACKLIGHT AURA ── */}
      {/* Outer ambient cyan-blue haze */}
      <div style={{
        position: 'absolute',
        left: '50%',
        top: '50%',
        transform: 'translate(-50%, -50%)',
        width: 380,
        height: 420,
        borderRadius: '50%',
        background: 'radial-gradient(ellipse 65% 75% at 50% 50%, rgba(6, 182, 212, 0.16) 0%, rgba(59, 130, 246, 0.10) 35%, rgba(147, 197, 253, 0.04) 65%, transparent 80%)',
        filter: 'blur(30px)',
        pointerEvents: 'none',
        zIndex: 0,
      }}/>

      {/* Core intense bright backlight glow behind the bar */}
      <div style={{
        position: 'absolute',
        left: '50%',
        top: '50%',
        transform: 'translate(-50%, -50%)',
        width: 140,
        height: 280,
        borderRadius: '50%',
        background: 'radial-gradient(ellipse 50% 70% at 50% 50%, rgba(6, 182, 212, 0.32) 0%, rgba(37, 99, 235, 0.22) 50%, transparent 80%)',
        filter: 'blur(16px)',
        pointerEvents: 'none',
        zIndex: 0,
      }}/>

      {/* ── 2. CENTER GLOWING BLUE VERTICAL BAR ── */}
      <div style={{
        position: 'absolute',
        left: '50%',
        transform: 'translateX(-50%)',
        top: '16%',
        bottom: '16%',
        width: 6.5,
        borderRadius: 9999,
        background: '#0062ff',
        boxShadow: '0 0 12px 2px rgba(0, 98, 255, 0.8), 0 0 28px 6px rgba(6, 182, 212, 0.5), 0 0 50px 10px rgba(59, 130, 246, 0.25)',
        zIndex: 20,
      }}/>

      {/* ── 3. STATIC FIBER OPTIC STREAMS & PARTICLES ── */}
      <svg style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', zIndex: 10 }}
           viewBox="0 0 220 440" preserveAspectRatio="none" aria-hidden="true">
        <defs>
          {/* Gradients for Left-to-Center */}
          <linearGradient id="glowLeftCyan" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#38bdf8" stopOpacity="0.3"/>
            <stop offset="60%" stopColor="#06b6d4" stopOpacity="0.85"/>
            <stop offset="100%" stopColor="#0062ff" stopOpacity="1"/>
          </linearGradient>

          <linearGradient id="glowLeftBlue" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#93c5fd" stopOpacity="0.25"/>
            <stop offset="50%" stopColor="#3b82f6" stopOpacity="0.8"/>
            <stop offset="100%" stopColor="#0062ff" stopOpacity="1"/>
          </linearGradient>

          <linearGradient id="glowLeftBright" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#e0f2fe" stopOpacity="0.45"/>
            <stop offset="65%" stopColor="#06b6d4" stopOpacity="0.95"/>
            <stop offset="100%" stopColor="#2563eb" stopOpacity="1"/>
          </linearGradient>

          {/* Gradients for Center-to-Right */}
          <linearGradient id="glowRightCyan" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#0062ff" stopOpacity="1"/>
            <stop offset="40%" stopColor="#06b6d4" stopOpacity="0.85"/>
            <stop offset="100%" stopColor="#38bdf8" stopOpacity="0.3"/>
          </linearGradient>

          <linearGradient id="glowRightBlue" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#0062ff" stopOpacity="1"/>
            <stop offset="50%" stopColor="#3b82f6" stopOpacity="0.8"/>
            <stop offset="100%" stopColor="#93c5fd" stopOpacity="0.25"/>
          </linearGradient>

          <linearGradient id="glowRightBright" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#2563eb" stopOpacity="1"/>
            <stop offset="35%" stopColor="#06b6d4" stopOpacity="0.95"/>
            <stop offset="100%" stopColor="#e0f2fe" stopOpacity="0.45"/>
          </linearGradient>

          {/* Soft blur filter for fiber depth */}
          <filter id="fiberGlow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur in="SourceGraphic" stdDeviation="1.6" result="blur"/>
            <feMerge>
              <feMergeNode in="blur"/>
              <feMergeNode in="SourceGraphic"/>
            </feMerge>
          </filter>

          {/* Core high-intensity blur */}
          <filter id="intenseGlow" x="-25%" y="-25%" width="150%" height="150%">
            <feGaussianBlur in="SourceGraphic" stdDeviation="2.5" result="b1"/>
            <feGaussianBlur in="SourceGraphic" stdDeviation="1.0" result="b2"/>
            <feMerge>
              <feMergeNode in="b1"/>
              <feMergeNode in="b2"/>
              <feMergeNode in="SourceGraphic"/>
            </feMerge>
          </filter>
        </defs>

        {/* ── BACKGROUND SUBTLE CONTOUR CURVES (Deep ambient layer) ── */}
        {[
          "M 0,20   C 60,20   80,120  110,150 C 140,180 170,20   220,20",
          "M 0,90   C 60,90   85,165  110,185 C 135,205 170,90   220,90",
          "M 0,350  C 60,350  85,275  110,255 C 135,235 170,350  220,350",
          "M 0,420  C 60,420  80,320  110,290 C 140,260 170,420  220,420",
        ].map((d, i) => (
          <path key={`ambient-bg-${i}`} d={d}
                stroke="#93c5fd" strokeWidth="0.8" strokeOpacity="0.25" fill="none"
                strokeDasharray="4 6"/>
        ))}

        {/* ── LEFT CONVERGING FIBER STREAM (STATIC) ── */}
        {[
          // Upper fan
          { d: "M 0,35   C 55,35   80,140  110,165", g: "glowLeftCyan",   w: 1.2, op: 0.60 },
          { d: "M 0,60   C 55,60   80,150  110,175", g: "glowLeftBlue",   w: 1.4, op: 0.72 },
          { d: "M 0,95   C 60,95   85,165  110,185", g: "glowLeftBright", w: 1.8, op: 0.95 },
          { d: "M 0,130  C 65,130  88,180  110,195", g: "glowLeftCyan",   w: 1.5, op: 0.88 },
          { d: "M 0,165  C 70,165  90,195  110,205", g: "glowLeftBright", w: 2.1, op: 1.00 },

          // Middle core
          { d: "M 0,200  C 70,200  92,210  110,212", g: "glowLeftCyan",   w: 2.3, op: 1.00 },
          { d: "M 0,225  C 70,225  92,218  110,218", g: "glowLeftBright", w: 2.2, op: 1.00 },
          { d: "M 0,250  C 70,250  90,228  110,225", g: "glowLeftCyan",   w: 2.0, op: 0.92 },

          // Lower fan
          { d: "M 0,285  C 65,285  88,240  110,235", g: "glowLeftBlue",   w: 1.6, op: 0.85 },
          { d: "M 0,320  C 60,320  85,255  110,245", g: "glowLeftBright", w: 1.8, op: 0.95 },
          { d: "M 0,355  C 55,355  80,270  110,255", g: "glowLeftCyan",   w: 1.4, op: 0.72 },
          { d: "M 0,385  C 55,385  80,285  110,265", g: "glowLeftBlue",   w: 1.2, op: 0.60 },
        ].map(({ d, g, w, op }, i) => (
          <path key={`left-fiber-${i}`} d={d}
                stroke={`url(#${g})`} strokeWidth={w} strokeOpacity={op} fill="none"
                filter="url(#fiberGlow)"/>
        ))}

        {/* ── RIGHT FANNING FIBER STREAM (STATIC) ── */}
        {[
          // Upper fan
          { d: "M 110,165 C 140,140 165,35   220,35",  g: "glowRightCyan",   w: 1.2, op: 0.60 },
          { d: "M 110,175 C 140,150 165,60   220,60",  g: "glowRightBlue",   w: 1.4, op: 0.72 },
          { d: "M 110,185 C 135,165 160,95   220,95",  g: "glowRightBright", w: 1.8, op: 0.95 },
          { d: "M 110,195 C 132,180 155,130  220,130", g: "glowRightCyan",   w: 1.5, op: 0.88 },
          { d: "M 110,205 C 130,195 150,165  220,165", g: "glowRightBright", w: 2.1, op: 1.00 },

          // Middle core
          { d: "M 110,212 C 128,210 150,200  220,200", g: "glowRightCyan",   w: 2.3, op: 1.00 },
          { d: "M 110,218 C 128,218 150,225  220,225", g: "glowRightBright", w: 2.2, op: 1.00 },
          { d: "M 110,225 C 130,228 150,250  220,250", g: "glowRightCyan",   w: 2.0, op: 0.92 },

          // Lower fan
          { d: "M 110,235 C 132,240 155,285  220,285", g: "glowRightBlue",   w: 1.6, op: 0.85 },
          { d: "M 110,245 C 135,255 160,320  220,320", g: "glowRightBright", w: 1.8, op: 0.95 },
          { d: "M 110,255 C 140,270 165,355  220,355", g: "glowRightCyan",   w: 1.4, op: 0.72 },
          { d: "M 110,265 C 140,285 165,385  220,385", g: "glowRightBlue",   w: 1.2, op: 0.60 },
        ].map(({ d, g, w, op }, i) => (
          <path key={`right-fiber-${i}`} d={d}
                stroke={`url(#${g})`} strokeWidth={w} strokeOpacity={op} fill="none"
                filter="url(#fiberGlow)"/>
        ))}

        {/* ── 4. STATIC GLOWING PARTICLES / NODES ── */}
        {[
          // Left points
          { cx: 35,  cy: 90,  r: 2.2, fill: "#38bdf8", op: 0.85 },
          { cx: 68,  cy: 145, r: 2.0, fill: "#06b6d4", op: 0.9  },
          { cx: 48,  cy: 195, r: 2.4, fill: "#ffffff", op: 1.0  },
          { cx: 80,  cy: 215, r: 2.2, fill: "#60a5fa", op: 0.95 },
          { cx: 55,  cy: 265, r: 2.0, fill: "#38bdf8", op: 0.85 },
          { cx: 38,  cy: 330, r: 2.2, fill: "#06b6d4", op: 0.8  },

          // Center bar convergence points
          { cx: 104, cy: 190, r: 2.6, fill: "#ffffff", op: 1.0  },
          { cx: 106, cy: 215, r: 2.8, fill: "#e0f2fe", op: 1.0  },
          { cx: 104, cy: 240, r: 2.6, fill: "#ffffff", op: 1.0  },

          // Right points
          { cx: 135, cy: 185, r: 2.2, fill: "#ffffff", op: 1.0  },
          { cx: 165, cy: 125, r: 2.0, fill: "#38bdf8", op: 0.85 },
          { cx: 155, cy: 230, r: 2.4, fill: "#60a5fa", op: 0.95 },
          { cx: 175, cy: 290, r: 2.2, fill: "#06b6d4", op: 0.9  },
          { cx: 185, cy: 350, r: 2.0, fill: "#38bdf8", op: 0.8  },
        ].map(({ cx, cy, r, fill, op }, i) => (
          <circle key={`particle-${i}`} cx={cx} cy={cy} r={r} fill={fill} opacity={op}
                  filter="url(#intenseGlow)"/>
        ))}
      </svg>
    </div>
  );
}
