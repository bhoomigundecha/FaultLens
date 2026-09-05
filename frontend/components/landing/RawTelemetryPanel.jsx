'use client';

const MAIN_CARD = {
  background: '#ffffff',
  borderRadius: 14,
  border: '1px solid rgba(226, 232, 240, 0.9)',
  boxShadow: '0 4px 20px -2px rgba(15, 23, 42, 0.07), 0 2px 6px -1px rgba(15, 23, 42, 0.04)',
  padding: '12px 15px',
};

const GHOST_CARD = {
  background: '#ffffff',
  borderRadius: 13,
  border: '1px solid rgba(226, 232, 240, 0.8)',
  boxShadow: '0 4px 16px -2px rgba(15, 23, 42, 0.04)',
  padding: '10px 14px',
  opacity: 0.45,
  pointerEvents: 'none',
};

export default function RawTelemetryPanel() {
  return (
    <div style={{ position: 'relative', width: '100%', userSelect: 'none' }}>

      {/* ── BACKGROUND CONSTELLATION NETWORK ON TOP-LEFT ── */}
      <svg style={{ position: 'absolute', left: -70, top: -10, width: 220, height: 200, pointerEvents: 'none', zIndex: 1 }}
           viewBox="0 0 220 200" fill="none">
        <g stroke="#93c5fd" strokeWidth="0.75" strokeOpacity="0.35">
          <line x1="20"  y1="60"  x2="70"  y2="40"/>
          <line x1="70"  y1="40"  x2="130" y2="25"/>
          <line x1="70"  y1="40"  x2="100" y2="90"/>
          <line x1="20"  y1="60"  x2="60"  y2="110"/>
          <line x1="60"  y1="110" x2="100" y2="90"/>
          <line x1="100" y1="90"  x2="150" y2="80"/>
          <line x1="130" y1="25"  x2="180" y2="45"/>
          <line x1="150" y1="80"  x2="180" y2="45"/>
          <line x1="150" y1="80"  x2="170" y2="130"/>
          <line x1="100" y1="90"  x2="120" y2="150"/>
          <line x1="60"  y1="110" x2="80"  y2="170"/>
        </g>
        {[
          [20,60],[70,40],[130,25],[100,90],[60,110],
          [150,80],[180,45],[170,130],[120,150],[80,170]
        ].map(([cx, cy], i) => (
          <circle key={`node-${i}`} cx={cx} cy={cy} r={i === 1 || i === 3 ? 2.5 : 1.8}
                  fill="#60a5fa" opacity={0.6}/>
        ))}
      </svg>

      {/* ── 3 FLOATING CIRCLE BADGES ON THE FAR LEFT ── */}
      {/* 1. Top File Icon */}
      <div style={{
        position: 'absolute', left: -50, top: 40, zIndex: 30,
        width: 38, height: 38, borderRadius: '50%', background: '#ffffff',
        border: '1px solid rgba(191, 219, 254, 0.8)',
        boxShadow: '0 4px 14px rgba(37, 99, 235, 0.12)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
        <svg width="17" height="17" viewBox="0 0 16 16" fill="none">
          <path d="M3 2C3 1.44772 3.44772 1 4 1H9.58579C9.851 1 10.1054 1.10536 10.2929 1.29289L13.7071 4.70711C13.8946 4.89464 14 5.149 14 5.41421V14C14 14.5523 13.5523 15 13 15H4C3.44772 15 3 14.5523 3 14V2Z"
                stroke="#2563eb" strokeWidth="1.2" fill="none"/>
          <path d="M9 1V5H13" stroke="#2563eb" strokeWidth="1.1" fill="none"/>
          <line x1="5.5" y1="8"   x2="10.5" y2="8"   stroke="#2563eb" strokeWidth="1" strokeLinecap="round"/>
          <line x1="5.5" y1="10.5" x2="9"    y2="10.5" stroke="#2563eb" strokeWidth="1" strokeLinecap="round"/>
        </svg>
      </div>

      {/* 2. Middle Bar Chart Icon */}
      <div style={{
        position: 'absolute', left: -58, top: 172, zIndex: 30,
        width: 38, height: 38, borderRadius: '50%', background: '#ffffff',
        border: '1px solid rgba(191, 219, 254, 0.8)',
        boxShadow: '0 4px 14px rgba(37, 99, 235, 0.12)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
        <svg width="17" height="17" viewBox="0 0 16 16" fill="none">
          <rect x="2"   y="9.5" width="3" height="5.5" rx="0.75" fill="#2563eb"/>
          <rect x="6.5" y="6"   width="3" height="9"   rx="0.75" fill="#2563eb"/>
          <rect x="11"  y="2"   width="3" height="13"  rx="0.75" fill="#2563eb"/>
        </svg>
      </div>

      {/* 3. Lower Branch/Fork Icon */}
      <div style={{
        position: 'absolute', left: -50, top: 296, zIndex: 30,
        width: 38, height: 38, borderRadius: '50%', background: '#ffffff',
        border: '1px solid rgba(191, 219, 254, 0.8)',
        boxShadow: '0 4px 14px rgba(37, 99, 235, 0.12)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
        <svg width="17" height="17" viewBox="0 0 16 16" fill="none">
          <circle cx="3.5" cy="8" r="1.8" stroke="#8b5cf6" strokeWidth="1.3"/>
          <circle cx="12.5" cy="4" r="1.8" stroke="#8b5cf6" strokeWidth="1.3"/>
          <circle cx="12.5" cy="12" r="1.8" stroke="#8b5cf6" strokeWidth="1.3"/>
          <path d="M5.3 8 H8 Q10.5 8 10.7 4.5" stroke="#8b5cf6" strokeWidth="1.2" fill="none"/>
          <path d="M8 8 Q10.5 8 10.7 11.5" stroke="#8b5cf6" strokeWidth="1.2" fill="none"/>
        </svg>
      </div>

      {/* ── FLOATING SMALL BADGES ON THE RIGHT EDGE ── */}
      <div style={{
        position: 'absolute', left: 365, top: 50, zIndex: 25,
        width: 25, height: 25, borderRadius: '50%', background: '#ffffff',
        border: '1px solid #bfdbfe', boxShadow: '0 2px 8px rgba(37, 99, 235, 0.14)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
        <svg width="12" height="12" viewBox="0 0 14 14" fill="none">
          <rect x="2.5" y="1.5" width="9" height="11" rx="1.5" stroke="#2563eb" strokeWidth="1.2"/>
          <line x1="4.5" y1="4.5" x2="9.5" y2="4.5" stroke="#2563eb" strokeWidth="1"/>
          <line x1="4.5" y1="7.5" x2="9.5" y2="7.5" stroke="#2563eb" strokeWidth="1"/>
        </svg>
      </div>

      <div style={{
        position: 'absolute', left: 355, top: 340, zIndex: 25,
        width: 25, height: 25, borderRadius: '50%', background: '#ffffff',
        border: '1px solid #bfdbfe', boxShadow: '0 2px 8px rgba(37, 99, 235, 0.14)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
        <svg width="12" height="12" viewBox="0 0 14 14" fill="none">
          <rect x="2.5" y="1.5" width="9" height="11" rx="1.5" stroke="#2563eb" strokeWidth="1.2"/>
          <line x1="4.5" y1="4.5" x2="9.5" y2="4.5" stroke="#2563eb" strokeWidth="1"/>
          <line x1="4.5" y1="7.5" x2="9.5" y2="7.5" stroke="#2563eb" strokeWidth="1"/>
        </svg>
      </div>

      {/* ── HEADER PILL ── */}
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', marginBottom: 16 }}>
        <span style={{
          background: 'rgba(219, 234, 254, 0.75)',
          color: '#2563eb',
          borderRadius: 9999,
          padding: '4px 14px',
          fontSize: '10px',
          fontWeight: 700,
          letterSpacing: '0.08em',
          border: '1px solid rgba(191, 219, 254, 0.85)',
        }}>
          RAW TELEMETRY
        </span>
        <span style={{ fontSize: '11px', color: '#64748b', marginTop: 4 }}>
          Logs, metrics, traces and more...
        </span>
      </div>

      {/* ── LAYERED COLLAGE CARDS ── */}
      <div style={{ position: 'relative', height: 410, width: '100%' }}>

        {/* 1. TOP-LEFT (Foreground): Log ERROR */}
        <div style={{
          ...MAIN_CARD,
          position: 'absolute', left: 10, top: 0, width: 250, zIndex: 20,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ display: 'flex' }}>
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                  <rect x="1.5" y="1.5" width="11" height="11" rx="2" stroke="#ef4444" strokeWidth="1.3"/>
                  <line x1="4" y1="4.5" x2="10" y2="4.5" stroke="#ef4444" strokeWidth="1.1"/>
                  <line x1="4" y1="7"   x2="10" y2="7"   stroke="#ef4444" strokeWidth="1.1"/>
                  <line x1="4" y1="9.5" x2="7.5" y2="9.5" stroke="#ef4444" strokeWidth="1.1"/>
                </svg>
              </span>
              <span style={{ fontSize: '13px', fontWeight: 700, color: '#0b1f3a' }}>Log</span>
            </div>
            <span style={{ fontSize: '10.5px', color: '#94a3b8' }}>10:24:31</span>
          </div>
          <p style={{ fontSize: '11px', color: '#1e293b', lineHeight: 1.45, margin: 0 }}>
            <span style={{ color: '#ef4444', fontWeight: 700 }}>ERROR</span>{' '}
            <span style={{ color: '#64748b', fontWeight: 600 }}>[db]</span> Connection pool
            <br />
            exhausted for user service
          </p>
          <p style={{ fontSize: '9.5px', color: '#94a3b8', fontFamily: 'monospace', marginTop: 5, marginBottom: 0 }}>
            trace_id: 3f9a2c4e...
          </p>
        </div>

        {/* 2. TOP-RIGHT (Ghost): Log WARN (attempt 2/5) */}
        <div style={{
          ...GHOST_CARD,
          position: 'absolute', left: 185, top: 22, width: 205, zIndex: 8,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 5 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ display: 'flex' }}>
                <svg width="13" height="13" viewBox="0 0 14 14" fill="none">
                  <rect x="1.5" y="1.5" width="11" height="11" rx="2" stroke="#f59e0b" strokeWidth="1.2"/>
                  <line x1="4" y1="4.5" x2="10" y2="4.5" stroke="#f59e0b" strokeWidth="1"/>
                </svg>
              </span>
              <span style={{ fontSize: '12px', fontWeight: 700, color: '#0b1f3a' }}>Log</span>
            </div>
          </div>
          <p style={{ fontSize: '10px', color: '#334155', lineHeight: 1.4, margin: 0 }}>
            <span style={{ color: '#f59e0b', fontWeight: 700 }}>WARN</span> Retrying connection
            <br />
            to database (attempt 2/5)
          </p>
        </div>

        {/* 3. MIDDLE-LEFT (Foreground): Metric duration */}
        <div style={{
          ...MAIN_CARD,
          position: 'absolute', left: 35, top: 100, width: 250, zIndex: 21,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 5 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ display: 'flex' }}>
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                  <rect x="1.5" y="8" width="3" height="5" rx="0.5" fill="#3b82f6"/>
                  <rect x="5.5" y="5" width="3" height="8" rx="0.5" fill="#3b82f6"/>
                  <rect x="9.5" y="2" width="3" height="11" rx="0.5" fill="#3b82f6"/>
                </svg>
              </span>
              <span style={{ fontSize: '13px', fontWeight: 700, color: '#0b1f3a' }}>Metric</span>
            </div>
            <span style={{ fontSize: '10.5px', color: '#94a3b8' }}>10:24:32</span>
          </div>
          <p style={{ fontSize: '11.5px', color: '#0f172a', fontWeight: 600, margin: 0 }}>
            http.server.duration
          </p>
          <p style={{ fontSize: '11px', margin: '4px 0 0 0', display: 'flex', alignItems: 'center', gap: 4 }}>
            <span style={{ color: '#ef4444', fontWeight: 700 }}>↑ 4.8s</span>
            <span style={{ color: '#64748b' }}>(baseline: 320ms)</span>
          </p>
        </div>

        {/* 4. MIDDLE-RIGHT (Ghost): Metric active */}
        <div style={{
          ...GHOST_CARD,
          position: 'absolute', left: 210, top: 152, width: 195, zIndex: 9,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
              <span style={{ display: 'flex' }}>
                <svg width="12" height="12" viewBox="0 0 14 14" fill="none">
                  <rect x="1.5" y="8" width="2.8" height="5" rx="0.5" fill="#8b5cf6"/>
                  <rect x="5.5" y="5" width="2.8" height="8" rx="0.5" fill="#8b5cf6"/>
                  <rect x="9.5" y="2" width="2.8" height="11" rx="0.5" fill="#8b5cf6"/>
                </svg>
              </span>
              <span style={{ fontSize: '11.5px', fontWeight: 700, color: '#0b1f3a' }}>Metric</span>
            </div>
            <span style={{ fontSize: '10px', color: '#94a3b8' }}>10:24:32</span>
          </div>
          <p style={{ fontSize: '10.5px', color: '#334155', margin: 0, fontWeight: 500 }}>
            db.connections.active
          </p>
          <p style={{ fontSize: '10px', color: '#ef4444', fontWeight: 600, margin: '2px 0 0 0' }}>
            ↑ 40 <span style={{ color: '#94a3b8', fontWeight: 400 }}>(baseline: 5)</span>
          </p>
        </div>

        {/* 5. LOWER-LEFT (Foreground): Trace POST */}
        <div style={{
          ...MAIN_CARD,
          position: 'absolute', left: 25, top: 198, width: 260, zIndex: 22,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 5 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ display: 'flex' }}>
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                  <circle cx="3" cy="7" r="1.8" stroke="#8b5cf6" strokeWidth="1.3"/>
                  <circle cx="11" cy="3.5" r="1.8" stroke="#8b5cf6" strokeWidth="1.3"/>
                  <circle cx="11" cy="10.5" r="1.8" stroke="#8b5cf6" strokeWidth="1.3"/>
                  <path d="M4.8 7 H7.5 Q9 7 9 4.8 V3.5" stroke="#8b5cf6" strokeWidth="1.2" fill="none"/>
                  <path d="M7.5 7 Q9 7 9 9.2 V10.5" stroke="#8b5cf6" strokeWidth="1.2" fill="none"/>
                </svg>
              </span>
              <span style={{ fontSize: '13px', fontWeight: 700, color: '#0b1f3a' }}>Trace</span>
            </div>
            <span style={{ fontSize: '10.5px', color: '#94a3b8' }}>10:24:32</span>
          </div>
          <p style={{ fontSize: '11.5px', color: '#0f172a', margin: 0, fontWeight: 500 }}>
            <span style={{ color: '#ef4444', fontWeight: 700 }}>POST</span> /api/payment
          </p>
          <p style={{ fontSize: '11.5px', color: '#ef4444', fontWeight: 700, margin: '2px 0 0 0' }}>
            503 Service Unavailable
          </p>
          <p style={{ fontSize: '9.5px', color: '#94a3b8', fontFamily: 'monospace', margin: '3px 0 0 0' }}>
            trace_id: 7ac9e1d2...
          </p>
        </div>

        {/* 6. LOWER-RIGHT (Ghost): Trace orders */}
        <div style={{
          ...GHOST_CARD,
          position: 'absolute', left: 180, top: 260, width: 205, zIndex: 10,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 5, marginBottom: 3 }}>
            <span style={{ display: 'flex' }}>
              <svg width="12" height="12" viewBox="0 0 14 14" fill="none">
                <circle cx="3" cy="7" r="1.8" stroke="#8b5cf6" strokeWidth="1.2"/>
                <circle cx="11" cy="4" r="1.8" stroke="#8b5cf6" strokeWidth="1.2"/>
                <path d="M4.8 7H7.5V4" stroke="#8b5cf6" strokeWidth="1.1" fill="none"/>
              </svg>
            </span>
            <span style={{ fontSize: '11.5px', fontWeight: 700, color: '#0b1f3a' }}>Trace</span>
          </div>
          <p style={{ fontSize: '10px', color: '#334155', margin: 0 }}>GET /api/orders</p>
          <p style={{ fontSize: '10px', color: '#ef4444', margin: '2px 0 0 0', fontWeight: 600 }}>
            504 Gateway Timeout
          </p>
        </div>

        {/* 7. BOTTOM-LEFT (Foreground): Log WARN */}
        <div style={{
          ...MAIN_CARD,
          position: 'absolute', left: 0, top: 312, width: 245, zIndex: 23,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 5 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ display: 'flex' }}>
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                  <rect x="1.5" y="1.5" width="11" height="11" rx="2" stroke="#8b5cf6" strokeWidth="1.3"/>
                  <line x1="4" y1="4.5" x2="10" y2="4.5" stroke="#8b5cf6" strokeWidth="1.1"/>
                  <line x1="4" y1="7"   x2="10" y2="7"   stroke="#8b5cf6" strokeWidth="1.1"/>
                  <line x1="4" y1="9.5" x2="7.5" y2="9.5" stroke="#8b5cf6" strokeWidth="1.1"/>
                </svg>
              </span>
              <span style={{ fontSize: '13px', fontWeight: 700, color: '#0b1f3a' }}>Log</span>
            </div>
            <span style={{ fontSize: '10.5px', color: '#94a3b8' }}>10:24:33</span>
          </div>
          <p style={{ fontSize: '11px', color: '#1e293b', lineHeight: 1.45, margin: 0 }}>
            <span style={{ color: '#f59e0b', fontWeight: 700 }}>WARN</span> Retrying connection
            <br />
            to database (attempt 3/5)
          </p>
        </div>

      </div>
    </div>
  );
}
