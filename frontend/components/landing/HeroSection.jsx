'use client';
export default function HeroSection() {
  return (
    <section className="flex flex-col items-center text-center select-none"
             style={{ paddingTop: '86px', paddingBottom: '20px', paddingLeft: '24px', paddingRight: '24px' }}>

      {/* Badge */}
      <div className="anim-fade-in" style={{ marginBottom: '16px' }}>
        <span className="inline-flex items-center gap-2 rounded-full font-bold uppercase"
              style={{
                padding: '6px 16px',
                fontSize: '10.5px',
                letterSpacing: '0.14em',
                background: 'rgba(219,234,254,0.9)',
                border: '1.5px solid rgba(147,197,253,0.8)',
                color: '#1d4ed8',
              }}>
          <span className="anim-dot rounded-full inline-block"
                style={{ width: 7, height: 7, background: '#2563eb', flexShrink: 0 }}/>
          AI-Powered Incident Investigation
        </span>
      </div>

      {/* Headline */}
      <h1 className="anim-fade-up d1 font-extrabold"
          style={{
            fontSize: 'clamp(2.2rem, 4.5vw, 3.4rem)',
            lineHeight: 1.12,
            letterSpacing: '-0.025em',
            color: '#0b1f3a',
            maxWidth: 680,
          }}>
        Turning{' '}
        <span style={{ color: '#2563eb' }}>complex&nbsp;telemetry</span>
        <br/>
        into clear answers
      </h1>

      {/* CTA button */}
      <a href="#connect"
         className="anim-fade-up d3 inline-flex items-center gap-2 rounded-full font-semibold
                    transition-all duration-200 hover:-translate-y-0.5"
         style={{
           marginTop: '28px',
           padding: '14px 28px',
           fontSize: '14.5px',
           background: '#0b1f3a',
           color: '#ffffff',
           boxShadow: '0 6px 24px rgba(11,31,58,0.32)',
         }}
         onMouseEnter={e => {
           e.currentTarget.style.background = '#162d50';
           e.currentTarget.style.boxShadow = '0 10px 32px rgba(11,31,58,0.42)';
         }}
         onMouseLeave={e => {
           e.currentTarget.style.background = '#0b1f3a';
           e.currentTarget.style.boxShadow = '0 6px 24px rgba(11,31,58,0.32)';
         }}>
        Connect your application <span style={{ fontSize: '16px' }}>→</span>
      </a>

      {/* Sub-link */}
      <p className="anim-fade-up d4" style={{ marginTop: '12px', fontSize: '13px', color: '#6b7280' }}>
        or explore the{' '}
        <a href="#demo"
           style={{ color: '#2563eb', fontWeight: 600 }}
           onMouseEnter={e => (e.target.style.textDecoration='underline')}
           onMouseLeave={e => (e.target.style.textDecoration='none')}>
          ShopFlow demo
        </a>
      </p>
    </section>
  );
}
