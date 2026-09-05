'use client';
import {
  NodeLogo,
  PythonLogo,
  JavaLogo,
  GoLogo,
  DotNetLogo,
  RubyLogo,
  DockerLogo,
  KubernetesLogo,
  VpsLogo,
} from './TechLogos';

const LANGUAGES = [
  { id: 'nodejs', name: 'Node.js', component: NodeLogo },
  { id: 'python', name: 'Python',  component: PythonLogo },
  { id: 'java',   name: 'Java',    component: JavaLogo },
  { id: 'go',     name: 'Go',      component: GoLogo },
  { id: 'dotnet', name: '.NET',    component: DotNetLogo },
  { id: 'ruby',   name: 'Ruby',    component: RubyLogo },
];

const DEPLOYMENTS = [
  { id: 'docker',     name: 'Docker',     component: DockerLogo },
  { id: 'kubernetes', name: 'Kubernetes', component: KubernetesLogo },
  { id: 'vps',        name: 'VPS',        component: VpsLogo },
];

const SIGNALS = [
  { id: 'metrics', name: 'Metrics', type: 'metric' },
  { id: 'logs',    name: 'Logs',    type: 'log' },
  { id: 'traces',  name: 'Traces',  type: 'trace' },
];

export default function Step2Details({
  selectedEnv,
  selectedLang,
  onSelectLang,
  selectedDeploy,
  onSelectDeploy,
  selectedSignals,
  onToggleSignal,
  onBack,
  onContinue,
}) {
  return (
    <div style={{ maxWidth: 980, margin: '0 auto', width: '100%', userSelect: 'none' }}>

      {/* Top Header Row with Back Button */}
      <div style={{ display: 'flex', alignItems: 'center', marginBottom: 6 }}>
        <button
          onClick={onBack}
          style={{
            background: 'none',
            border: 'none',
            fontSize: '12.5px',
            fontWeight: 600,
            color: '#475569',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            padding: '2px 4px',
          }}
        >
          ← Back
        </button>
      </div>

      {/* Stepper (01 check, 02 active, 03) */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 10 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {/* Step 01 (Checked) */}
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 3, minWidth: 26 }}>
            <div style={{
              width: 14, height: 14, borderRadius: '50%', background: '#93c5fd',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              color: '#ffffff', fontSize: '9px', fontWeight: 800,
            }}>
              ✓
            </div>
            <span style={{ fontSize: '10px', fontWeight: 700, color: '#2563eb' }}>01</span>
          </div>

          <div style={{ width: 50, height: 1.5, background: '#2563eb', marginBottom: 14 }}/>

          {/* Step 02 (Active) */}
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 3, minWidth: 26 }}>
            <div style={{
              width: 12, height: 12, borderRadius: '50%', background: '#2563eb',
            }}/>
            <span style={{ fontSize: '10px', fontWeight: 700, color: '#2563eb' }}>02</span>
          </div>

          <div style={{ width: 50, height: 1.5, background: '#e2e8f0', marginBottom: 14 }}/>

          {/* Step 03 (Upcoming) */}
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 3, minWidth: 26 }}>
            <div style={{
              width: 12, height: 12, borderRadius: '50%', background: '#ffffff',
              border: '1.5px solid #cbd5e1',
            }}/>
            <span style={{ fontSize: '10px', fontWeight: 500, color: '#94a3b8' }}>03</span>
          </div>
        </div>
      </div>

      {/* Title */}
      <div style={{ textAlign: 'center', marginBottom: 14 }}>
        <h1 style={{
          fontSize: 'clamp(1.7rem, 2.5vw, 2.15rem)',
          fontWeight: 800,
          color: '#0b1f3a',
          letterSpacing: '-0.025em',
          lineHeight: 1.2,
          margin: 0,
        }}>
          Tell us about <span style={{ color: '#2563eb' }}>your application.</span>
        </h1>
        <p style={{ fontSize: '12px', color: '#64748b', marginTop: 4, marginBottom: 0 }}>
          A couple of details so we can generate the right connection setup.
        </p>
      </div>

      {/* ── 3 SECTIONS (Compact Cards) ── */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 16 }}>

        {/* Section 01: Language */}
        <div style={{
          background: '#ffffff',
          borderRadius: 14,
          padding: '11px 18px',
          border: '1px solid rgba(226, 232, 240, 0.9)',
          boxShadow: '0 4px 18px -2px rgba(15, 23, 42, 0.04)',
          display: 'grid',
          gridTemplateColumns: '250px 1fr',
          gap: 20,
          alignItems: 'center',
        }}>
          {/* Left Title */}
          <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
            <div style={{
              width: 34, height: 34, borderRadius: 10, background: '#eff6ff',
              border: '1px solid #dbeafe', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
            }}>
              <span style={{ color: '#2563eb', fontWeight: 700, fontSize: '13px' }}>&lt;/&gt;</span>
            </div>
            <div>
              <p style={{ fontSize: '10px', fontWeight: 700, color: '#2563eb', margin: 0 }}>01</p>
              <h3 style={{ fontSize: '14px', fontWeight: 700, color: '#0b1f3a', margin: '1px 0 2px 0' }}>
                What language does your application use?
              </h3>
              <p style={{ fontSize: '11.5px', color: '#64748b', margin: 0, lineHeight: 1.35 }}>
                We&apos;ll provide language-specific configuration.
              </p>
            </div>
          </div>

          {/* Options Grid */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8 }}>
            {LANGUAGES.map(lang => {
              const isSelected = selectedLang === lang.id;
              const LogoComp = lang.component;
              return (
                <div
                  key={lang.id}
                  onClick={() => onSelectLang(lang.id)}
                  style={{
                    background: '#ffffff',
                    borderRadius: 10,
                    padding: '8px 10px',
                    border: isSelected ? '1.5px solid #2563eb' : '1px solid #e2e8f0',
                    boxShadow: isSelected ? '0 2px 8px rgba(37, 99, 235, 0.12)' : 'none',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
                    <LogoComp />
                    <span style={{ fontSize: '12.5px', fontWeight: 600, color: '#0b1f3a' }}>
                      {lang.name}
                    </span>
                  </div>
                  {isSelected && (
                    <div style={{
                      width: 14, height: 14, borderRadius: '50%', background: '#2563eb',
                      display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#ffffff',
                      fontSize: '9px', fontWeight: 800,
                    }}>
                      ✓
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Section 02: Deployment */}
        <div style={{
          background: '#ffffff',
          borderRadius: 14,
          padding: '11px 18px',
          border: '1px solid rgba(226, 232, 240, 0.9)',
          boxShadow: '0 4px 18px -2px rgba(15, 23, 42, 0.04)',
          display: 'grid',
          gridTemplateColumns: '250px 1fr',
          gap: 20,
          alignItems: 'center',
        }}>
          {/* Left Title */}
          <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
            <div style={{
              width: 30, height: 30, borderRadius: 8, background: '#eff6ff',
              border: '1px solid #dbeafe', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
            }}>
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
                <rect x="2" y="3"  width="20" height="5" rx="1.5" stroke="#2563eb" strokeWidth="1.6"/>
                <rect x="2" y="10" width="20" height="5" rx="1.5" stroke="#2563eb" strokeWidth="1.6"/>
                <rect x="2" y="17" width="20" height="5" rx="1.5" stroke="#2563eb" strokeWidth="1.6"/>
                <circle cx="6" cy="5.5"  r="1" fill="#2563eb"/>
                <circle cx="6" cy="12.5" r="1" fill="#2563eb"/>
                <circle cx="6" cy="19.5" r="1" fill="#2563eb"/>
              </svg>
            </div>
            <div>
              <p style={{ fontSize: '10px', fontWeight: 700, color: '#2563eb', margin: 0 }}>02</p>
              <h3 style={{ fontSize: '13.5px', fontWeight: 700, color: '#0b1f3a', margin: '1px 0 2px 0' }}>
                How is it deployed?
              </h3>
              <p style={{ fontSize: '11px', color: '#64748b', margin: 0, lineHeight: 1.35 }}>
                Choose the infrastructure that runs your application.
              </p>
            </div>
          </div>

          {/* Options Grid */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8 }}>
            {DEPLOYMENTS.map(deploy => {
              const isSelected = selectedDeploy === deploy.id;
              const DeployLogoComp = deploy.component;
              return (
                <div
                  key={deploy.id}
                  onClick={() => onSelectDeploy(deploy.id)}
                  style={{
                    background: '#ffffff',
                    borderRadius: 9,
                    padding: '7px 11px',
                    border: isSelected ? '1.5px solid #2563eb' : '1px solid #e2e8f0',
                    boxShadow: isSelected ? '0 2px 8px rgba(37, 99, 235, 0.12)' : 'none',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    cursor: 'pointer',
                    transition: 'all 0.15s ease',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
                    <DeployLogoComp />
                    <span style={{ fontSize: '12px', fontWeight: 600, color: '#0b1f3a' }}>
                      {deploy.name}
                    </span>
                  </div>
                  {isSelected && (
                    <div style={{
                      width: 14, height: 14, borderRadius: '50%', background: '#2563eb',
                      display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#ffffff',
                      fontSize: '9px', fontWeight: 800,
                    }}>
                      ✓
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Section 03: Telemetry Signals */}
        <div style={{
          background: '#ffffff',
          borderRadius: 14,
          padding: '11px 18px',
          border: '1px solid rgba(226, 232, 240, 0.9)',
          boxShadow: '0 4px 18px -2px rgba(15, 23, 42, 0.04)',
          display: 'grid',
          gridTemplateColumns: '250px 1fr',
          gap: 20,
          alignItems: 'center',
        }}>
          {/* Left Title */}
          <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
            <div style={{
              width: 30, height: 30, borderRadius: 8, background: '#eff6ff',
              border: '1px solid #dbeafe', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
            }}>
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none">
                <rect x="3" y="12" width="4" height="9" rx="1" fill="#2563eb"/>
                <rect x="10" y="7" width="4" height="14" rx="1" fill="#2563eb"/>
                <rect x="17" y="3" width="4" height="18" rx="1" fill="#2563eb"/>
              </svg>
            </div>
            <div>
              <p style={{ fontSize: '10px', fontWeight: 700, color: '#2563eb', margin: 0 }}>03</p>
              <h3 style={{ fontSize: '13.5px', fontWeight: 700, color: '#0b1f3a', margin: '1px 0 2px 0' }}>
                What would you like FaultLens to observe?
              </h3>
              <p style={{ fontSize: '11px', color: '#64748b', margin: 0, lineHeight: 1.35 }}>
                Select the telemetry signals you want to send.
              </p>
            </div>
          </div>

          {/* Options Grid + Callout */}
          <div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8, marginBottom: 4 }}>
              {SIGNALS.map(sig => {
                const isSelected = selectedSignals.includes(sig.id);
                return (
                  <div
                    key={sig.id}
                    onClick={() => onToggleSignal(sig.id)}
                    style={{
                      background: '#ffffff',
                      borderRadius: 9,
                      padding: '7px 11px',
                      border: isSelected ? '1.5px solid #2563eb' : '1px solid #e2e8f0',
                      boxShadow: isSelected ? '0 2px 8px rgba(37, 99, 235, 0.12)' : 'none',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      cursor: 'pointer',
                      transition: 'all 0.15s ease',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
                      {sig.type === 'metric' && (
                        <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
                          <rect x="1.5" y="9" width="3" height="6" rx="0.5" fill="#2563eb"/>
                          <rect x="6.5" y="5.5" width="3" height="9.5" rx="0.5" fill="#2563eb"/>
                          <rect x="11.5" y="2" width="3" height="13" rx="0.5" fill="#2563eb"/>
                        </svg>
                      )}
                      {sig.type === 'log' && (
                        <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
                          <rect x="2.5" y="1.5" width="11" height="13" rx="1.5" stroke="#2563eb" strokeWidth="1.3"/>
                          <line x1="5" y1="5" x2="11" y2="5" stroke="#2563eb" strokeWidth="1.2"/>
                        </svg>
                      )}
                      {sig.type === 'trace' && (
                        <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
                          <circle cx="3.5" cy="8" r="2" stroke="#2563eb" strokeWidth="1.3"/>
                          <circle cx="12.5" cy="4" r="2" stroke="#2563eb" strokeWidth="1.3"/>
                          <circle cx="12.5" cy="12" r="2" stroke="#2563eb" strokeWidth="1.3"/>
                          <path d="M5.5 8H8.5Q10.5 8 10.5 5V4" stroke="#2563eb" strokeWidth="1.2" fill="none"/>
                        </svg>
                      )}
                      <span style={{ fontSize: '12px', fontWeight: 600, color: '#0b1f3a' }}>
                        {sig.name}
                      </span>
                    </div>
                    {isSelected && (
                      <div style={{
                        width: 14, height: 14, borderRadius: '50%', background: '#2563eb',
                        display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#ffffff',
                        fontSize: '9px', fontWeight: 800,
                      }}>
                        ✓
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 5, paddingLeft: 2 }}>
              <span style={{ color: '#2563eb', fontSize: '10.5px' }}>ⓘ</span>
              <span style={{ fontSize: '10px', color: '#64748b' }}>
                FaultLens works best when it can correlate metrics, logs and traces.
              </span>
            </div>
          </div>
        </div>

      </div>

      {/* Continue Button */}
      <div style={{ display: 'flex', justifyContent: 'center' }}>
        <button
          onClick={onContinue}
          style={{
            background: '#0b1f3a',
            color: '#ffffff',
            padding: '10px 36px',
            borderRadius: 9999,
            fontSize: '13px',
            fontWeight: 600,
            border: 'none',
            cursor: 'pointer',
            boxShadow: '0 6px 20px -2px rgba(11, 31, 58, 0.3)',
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
