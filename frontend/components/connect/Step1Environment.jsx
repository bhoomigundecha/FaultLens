'use client';

const ENVIRONMENTS = [
  {
    id: 'self-hosted',
    index: '01',
    title: 'Self-hosted',
    subtitle: 'Docker · Kubernetes · VPS',
    description: 'Connect your application using OpenTelemetry.',
    tags: ['Metrics', 'Logs', 'Traces'],
    icon: 'cube',
  },
  {
    id: 'serverless',
    index: '02',
    title: 'Serverless',
    subtitle: 'Vercel · Netlify · Cloudflare',
    description: "Connect through your platform's log integration.",
    tags: ['Logs'],
    icon: 'cloud',
  },
  {
    id: 'cloud-paas',
    index: '03',
    title: 'Cloud / PaaS',
    subtitle: 'AWS · GCP · Azure · Render · Railway',
    description: 'Connect your existing observability data through OpenTelemetry.',
    tags: ['Metrics', 'Logs', 'Traces'],
    icon: 'stack',
  },
];

export default function Step1Environment({ selectedEnv, onSelectEnv, onContinue }) {
  return (
    <div style={{ maxWidth: 1040, margin: '0 auto', width: '100%', userSelect: 'none' }}>

      {/* Heading matching Image 1: 2 distinct lines */}
      <div style={{ textAlign: 'center', marginBottom: 12 }}>
        <h1 style={{
          fontSize: 'clamp(1.75rem, 2.5vw, 2.25rem)',
          fontWeight: 800,
          color: '#0b1f3a',
          letterSpacing: '-0.025em',
          lineHeight: 1.15,
          margin: 0,
        }}>
          Connect <span style={{ color: '#2563eb' }}>your application</span>{' '}
          <br />
          to FaultLens.
        </h1>
        <p style={{ fontSize: '12.5px', color: '#64748b', marginTop: 5, marginBottom: 0, fontWeight: 400 }}>
          Choose how your application runs. We&apos;ll handle the rest.
        </p>
      </div>

      {/* Stepper (01 active, 02, 03) */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {/* Step 01 */}
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4, minWidth: 26 }}>
            <div style={{
              width: 13, height: 13, borderRadius: '50%', background: '#2563eb',
            }}/>
            <span style={{ fontSize: '10.5px', fontWeight: 700, color: '#2563eb' }}>01</span>
          </div>

          <div style={{ width: 60, height: 1.5, background: '#e2e8f0', marginBottom: 16 }}/>

          {/* Step 02 */}
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4, minWidth: 26 }}>
            <div style={{
              width: 13, height: 13, borderRadius: '50%', background: '#ffffff',
              border: '1.5px solid #cbd5e1',
            }}/>
            <span style={{ fontSize: '10.5px', fontWeight: 500, color: '#94a3b8' }}>02</span>
          </div>

          <div style={{ width: 60, height: 1.5, background: '#e2e8f0', marginBottom: 16 }}/>

          {/* Step 03 */}
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4, minWidth: 26 }}>
            <div style={{
              width: 13, height: 13, borderRadius: '50%', background: '#ffffff',
              border: '1.5px solid #cbd5e1',
            }}/>
            <span style={{ fontSize: '10.5px', fontWeight: 500, color: '#94a3b8' }}>03</span>
          </div>
        </div>
      </div>

      {/* 3 Interactive Cards (Compact) */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(3, 1fr)',
        gap: 16,
        marginBottom: 20,
      }}>
        {ENVIRONMENTS.map(env => {
          const isSelected = selectedEnv === env.id;
          return (
            <div
              key={env.id}
              onClick={() => onSelectEnv(env.id)}
              style={{
                background: '#ffffff',
                borderRadius: 16,
                padding: '18px 18px',
                border: isSelected ? '1.5px solid #2563eb' : '1px solid rgba(226, 232, 240, 0.9)',
                boxShadow: isSelected
                  ? '0 10px 30px -4px rgba(37, 99, 235, 0.15), 0 3px 10px rgba(0,0,0,0.03)'
                  : '0 4px 18px -2px rgba(15, 23, 42, 0.04), 0 2px 5px -1px rgba(15, 23, 42, 0.02)',
                cursor: 'pointer',
                transition: 'all 0.2s ease',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                minHeight: 220,
              }}
            >
              <div>
                {/* Icon in top circle */}
                <div style={{
                  width: 36, height: 36, borderRadius: 10,
                  background: '#eff6ff',
                  border: '1px solid #dbeafe',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  marginBottom: 12,
                }}>
                  {env.icon === 'cube' && (
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                      <path d="M12 2L21 7V17L12 22L3 17V7L12 2Z" stroke="#2563eb" strokeWidth="1.6" strokeLinejoin="round"/>
                      <path d="M12 2V22M3 7L12 12L21 7" stroke="#2563eb" strokeWidth="1.4" strokeLinejoin="round"/>
                    </svg>
                  )}
                  {env.icon === 'cloud' && (
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                      <path d="M17.5 19H6.5C4.01472 19 2 16.9853 2 14.5C2 12.1564 3.79151 10.2313 6.08259 10.0209C6.54959 6.64211 9.44841 4 13 4C16.9761 4 20.2478 7.04231 20.6241 11.0083C21.9962 11.666 23 13.0673 23 14.7C23 17.0748 21.0748 19 18.7 19H17.5Z"
                            stroke="#2563eb" strokeWidth="1.6" strokeLinejoin="round"/>
                    </svg>
                  )}
                  {env.icon === 'stack' && (
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
                      <path d="M12 2L2 7L12 12L22 7L12 2Z" stroke="#2563eb" strokeWidth="1.6" strokeLinejoin="round"/>
                      <path d="M2 12L12 17L22 12" stroke="#2563eb" strokeWidth="1.6" strokeLinejoin="round"/>
                      <path d="M2 17L12 22L22 17" stroke="#2563eb" strokeWidth="1.6" strokeLinejoin="round"/>
                    </svg>
                  )}
                </div>

                {/* Index & Title */}
                <p style={{ fontSize: '10.5px', fontWeight: 700, color: '#2563eb', margin: 0, letterSpacing: '0.04em' }}>
                  {env.index}
                </p>
                <h3 style={{ fontSize: '18px', fontWeight: 700, color: '#0b1f3a', margin: '3px 0 3px 0' }}>
                  {env.title}
                </h3>
                <p style={{ fontSize: '11.5px', color: '#64748b', margin: 0, fontWeight: 500 }}>
                  {env.subtitle}
                </p>

                {/* Description */}
                <p style={{ fontSize: '12px', color: '#475569', marginTop: 10, marginBottom: 14, lineHeight: 1.45 }}>
                  {env.description}
                </p>
              </div>

              {/* Bottom Tags and Arrow */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingTop: 6 }}>
                <div style={{ display: 'flex', gap: 5, flexWrap: 'wrap' }}>
                  {env.tags.map(tag => (
                    <span key={tag} style={{
                      fontSize: '10.5px',
                      fontWeight: 600,
                      color: '#2563eb',
                      background: '#eff6ff',
                      border: '1px solid #dbeafe',
                      padding: '2.5px 8px',
                      borderRadius: 9999,
                    }}>
                      {tag}
                    </span>
                  ))}
                </div>

                <div style={{
                  width: 28, height: 28, borderRadius: '50%',
                  background: '#eff6ff',
                  border: '1px solid #dbeafe',
                  color: '#2563eb',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: '13px', flexShrink: 0,
                }}>
                  →
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Continue Button */}
      <div style={{ display: 'flex', justifyContent: 'center' }}>
        <button
          onClick={onContinue}
          style={{
            background: selectedEnv ? '#0b1f3a' : 'rgba(203, 213, 225, 0.65)',
            color: '#ffffff',
            padding: '11px 40px',
            borderRadius: 9999,
            fontSize: '13.5px',
            fontWeight: 600,
            border: 'none',
            cursor: selectedEnv ? 'pointer' : 'default',
            boxShadow: selectedEnv ? '0 6px 20px -2px rgba(11, 31, 58, 0.3)' : 'none',
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            transition: 'all 0.2s ease',
          }}
        >
          Continue <span>→</span>
        </button>
      </div>

    </div>
  );
}
