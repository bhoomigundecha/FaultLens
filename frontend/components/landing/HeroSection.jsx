'use client';

export default function HeroSection() {
  return (
    <section className="flex flex-col items-center text-center select-none"
             style={{ paddingTop: '98px', paddingBottom: '16px', paddingLeft: '24px', paddingRight: '24px' }}>

      {/* Badge */}
      <div className="anim-fade-in" style={{ marginBottom: '16px' }}>
        <span className="inline-flex items-center rounded-full font-bold uppercase"
              style={{
                padding: '5px 16px',
                fontSize: '10.5px',
                letterSpacing: '0.12em',
                background: 'rgba(219, 234, 254, 0.75)',
                border: '1px solid rgba(191, 219, 254, 0.9)',
                color: '#2563eb',
              }}>
          AI-POWERED INCIDENT INVESTIGATION
        </span>
      </div>

      {/* Headline */}
      <h1 className="anim-fade-up d1 font-extrabold"
          style={{
            fontSize: 'clamp(2.1rem, 3.8vw, 3.25rem)',
            lineHeight: 1.15,
            letterSpacing: '-0.025em',
            color: '#0b1f3a',
            maxWidth: 820,
            margin: '0 auto',
          }}>
        <span style={{ display: 'inline-block', whiteSpace: 'nowrap' }}>
          Turning <span style={{ color: '#2563eb' }}>complex telemetry</span>
        </span>{' '}
        <br/>
        <span style={{ display: 'inline-block', whiteSpace: 'nowrap' }}>
          into clear answers
        </span>
      </h1>

      {/* CTA button */}
      <a href="/connect"
         className="anim-fade-up d3 inline-flex items-center gap-2 rounded-full font-semibold
                    transition-all duration-200 hover:opacity-90"
         style={{
           marginTop: '22px',
           padding: '11px 26px',
           fontSize: '14px',
           background: '#0b1f3a',
           color: '#ffffff',
           boxShadow: '0 6px 20px -2px rgba(11,31,58,0.3)',
         }}
         onMouseEnter={e => {
           e.currentTarget.style.background = '#162d50';
         }}
         onMouseLeave={e => {
           e.currentTarget.style.background = '#0b1f3a';
         }}>
        Connect your application <span style={{ fontSize: '15px', marginLeft: 2 }}>→</span>
      </a>

      {/* Sub-link */}
      <p className="anim-fade-up d4" style={{ marginTop: '10px', fontSize: '12.5px', color: '#64748b' }}>
        or explore the{' '}
        <a href="/demo"
           style={{ color: '#2563eb', fontWeight: 600, textDecoration: 'underline' }}>
          ShopFlow demo
        </a>
      </p>
    </section>
  );
}
