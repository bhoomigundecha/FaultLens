import RawTelemetryPanel from '@/components/landing/RawTelemetryPanel';
import FlowVisualizer    from '@/components/landing/FlowVisualizer';
import ClearAnswersPanel from '@/components/landing/ClearAnswersPanel';

export default function DemoSection() {
  return (
    <section id="demo" className="w-full"
             style={{ position: 'relative' }}>
      {/* Soft center glow */}
      <div style={{
        position: 'absolute', inset: 0, pointerEvents: 'none', zIndex: 0,
        background: 'radial-gradient(ellipse 70% 80% at 50% 50%, rgba(59,130,246,0.06) 0%, transparent 70%)',
      }}/>

      <div className="relative"
           style={{
             zIndex: 1,
             maxWidth: 1280,
             margin: '0 auto',
             padding: '0 8px',
             display: 'grid',
             gridTemplateColumns: '1fr 200px 1fr',
             alignItems: 'stretch',
           }}>
        {/* LEFT */}
        <div style={{ paddingLeft: 52, paddingRight: 12, paddingTop: 4 }}>
          <RawTelemetryPanel />
        </div>
        {/* CENTER */}
        <div style={{ minHeight: 480, display: 'flex' }}>
          <FlowVisualizer />
        </div>
        {/* RIGHT */}
        <div style={{ paddingLeft: 12, paddingRight: 8, paddingTop: 4 }}>
          <ClearAnswersPanel />
        </div>
      </div>
    </section>
  );
}
