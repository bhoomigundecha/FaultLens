import LogCard    from '@/components/ui/LogCard';
import MetricCard from '@/components/ui/MetricCard';
import TraceCard  from '@/components/ui/TraceCard';

const SideIcon = ({ children, delay }) => (
  <div className="anim-float" style={{
    animationDelay: delay,
    width: 38, height: 38, borderRadius: 12,
    background: '#ffffff',
    border: '1px solid rgba(147,197,253,0.5)',
    boxShadow: '0 3px 14px rgba(37,99,235,0.12)',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    flexShrink: 0,
  }}>
    {children}
  </div>
);

export default function RawTelemetryPanel() {
  return (
    <div className="anim-slide-l" style={{ position: 'relative', height: '100%', display: 'flex', flexDirection: 'column' }}>

      {/* Floating left sidebar icons */}
      <div style={{
        position: 'absolute', left: -48, top: '50%', transform: 'translateY(-50%)',
        display: 'flex', flexDirection: 'column', gap: 14, zIndex: 10,
      }}>
        <SideIcon delay="0s">
          <svg width="17" height="17" viewBox="0 0 17 17" fill="none">
            <rect x="2" y="1" width="11" height="15" rx="2" stroke="#2563eb" strokeWidth="1.3"/>
            <line x1="4.5" y1="5.5"  x2="11" y2="5.5"  stroke="#2563eb" strokeWidth="1.1"/>
            <line x1="4.5" y1="8.5"  x2="11" y2="8.5"  stroke="#2563eb" strokeWidth="1.1"/>
            <line x1="4.5" y1="11.5" x2="8"  y2="11.5" stroke="#2563eb" strokeWidth="1.1"/>
          </svg>
        </SideIcon>
        <SideIcon delay="0.7s">
          <svg width="17" height="17" viewBox="0 0 17 17" fill="none">
            <rect x="1"  y="10" width="4" height="6"  rx="1" fill="#3b82f6"/>
            <rect x="6.5" y="7"  width="4" height="9"  rx="1" fill="#3b82f6"/>
            <rect x="12" y="3.5" width="4" height="12.5" rx="1" fill="#3b82f6"/>
          </svg>
        </SideIcon>
        <SideIcon delay="1.4s">
          <svg width="17" height="17" viewBox="0 0 17 17" fill="none">
            <circle cx="3.5"  cy="8.5" r="2.2" stroke="#8b5cf6" strokeWidth="1.3"/>
            <circle cx="13.5" cy="8.5" r="2.2" stroke="#8b5cf6" strokeWidth="1.3"/>
            <path d="M5.7 8.5 Q8.5 4 11.3 8.5" stroke="#8b5cf6" strokeWidth="1.2" fill="none" strokeLinecap="round"/>
            <path d="M5.7 8.5 Q8.5 13 11.3 8.5" stroke="#8b5cf6" strokeWidth="1.2" fill="none" strokeLinecap="round" strokeDasharray="2 1.5"/>
          </svg>
        </SideIcon>
      </div>

      {/* Panel header */}
      <div style={{ marginBottom: 10 }}>
        <p style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.18em', textTransform: 'uppercase', color: '#2563eb' }}>
          Raw Telemetry
        </p>
        <p style={{ fontSize: 11, color: '#9ca3af', marginTop: 3 }}>Logs, metrics, traces and more...</p>
      </div>

      {/* Cards */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8, position: 'relative' }}>

        <LogCard level="ERROR" message="[db] Connection pool exhausted for user service"
                 traceId="3f9a2c4e..." timestamp="10:24:31"
                 className="anim-fade-up d2" style={{ position: 'relative', zIndex: 30 }}/>

        {/* Ghost metric */}
        <div style={{ opacity: 0.42, filter: 'blur(1px)', transform: 'scale(0.96)',
                      marginTop: -4, pointerEvents: 'none', zIndex: 10 }}>
          <MetricCard name="db.connections.active" value="48" baseline="5"
                      trend="up" timestamp="10:24:31"/>
        </div>

        <MetricCard name="http.server.duration" value="4.8s" baseline="320ms"
                    trend="up" timestamp="10:24:32"
                    className="anim-fade-up d3" style={{ position: 'relative', zIndex: 30 }}/>

        <TraceCard method="POST" path="/api/payment" status={503}
                   statusText="Service Unavailable" traceId="7ac9e1d2..."
                   timestamp="10:24:32"
                   className="anim-fade-up d4" style={{ position: 'relative', zIndex: 30 }}/>

        {/* Log WARN + ghost trace behind */}
        <div style={{ position: 'relative' }}>
          <div style={{
            position: 'absolute', right: -12, top: 8,
            width: '75%', opacity: 0.38, filter: 'blur(1.5px)',
            transform: 'scale(0.91)', pointerEvents: 'none', zIndex: 10,
          }}>
            <TraceCard method="GET" path="/api/orders" status={504} statusText="Gateway Timeout" timestamp="10:24:33"/>
          </div>
          <LogCard level="WARN" message="Retrying connection to database (attempt 3/5)"
                   timestamp="10:24:33"
                   className="anim-fade-up d5" style={{ position: 'relative', zIndex: 30 }}/>
        </div>

      </div>
    </div>
  );
}
