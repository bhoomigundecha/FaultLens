'use client';
import { useState, useEffect } from 'react';

export default function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  useEffect(() => {
    const fn = () => setScrolled(window.scrollY > 8);
    window.addEventListener('scroll', fn, { passive: true });
    return () => window.removeEventListener('scroll', fn);
  }, []);

  return (
    <div className="fixed top-0 left-0 right-0 z-50 flex justify-center px-6"
         style={{ pointerEvents: 'none', top: '24px' }}>
      <nav style={{
             pointerEvents: 'auto',
             background: scrolled ? 'rgba(255, 255, 255, 0.94)' : 'rgba(255, 255, 255, 0.88)',
             backdropFilter: 'blur(20px)',
             border: '1px solid rgba(255, 255, 255, 0.8)',
             boxShadow: '0 4px 24px -2px rgba(37, 99, 235, 0.08), 0 2px 8px rgba(0, 0, 0, 0.04)',
             borderRadius: '9999px',
             padding: '6px 8px 6px 18px',
             display: 'flex',
             alignItems: 'center',
             gap: '24px',
             transition: 'all 0.3s ease',
           }}>

        {/* Logo */}
        <a href="/" className="flex items-center gap-2.5 group flex-shrink-0">
          <div className="w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0"
               style={{
                 background: 'radial-gradient(circle, rgba(37,99,235,0.12) 0%, rgba(37,99,235,0.02) 70%)',
                 border: '1.5px solid #2563eb',
                 position: 'relative',
               }}>
            <svg width="18" height="18" viewBox="0 0 20 20" fill="none">
              <circle cx="10" cy="10" r="5" stroke="#2563eb" strokeWidth="1.4"/>
              <circle cx="10" cy="10" r="2" fill="#2563eb"/>
              <line x1="10" y1="2" x2="10" y2="4" stroke="#2563eb" strokeWidth="1.4" strokeLinecap="round"/>
              <line x1="10" y1="16" x2="10" y2="18" stroke="#2563eb" strokeWidth="1.4" strokeLinecap="round"/>
              <line x1="2" y1="10" x2="4" y2="10" stroke="#2563eb" strokeWidth="1.4" strokeLinecap="round"/>
              <line x1="16" y1="10" x2="18" y2="10" stroke="#2563eb" strokeWidth="1.4" strokeLinecap="round"/>
            </svg>
          </div>
          <span className="text-[15.5px] font-bold tracking-tight select-none"
                style={{ color: '#0b1f3a' }}>FaultLens</span>
        </a>

        {/* CTA */}
        <a href="/connect"
           className="flex items-center gap-1.5 rounded-full font-semibold text-[13px] whitespace-nowrap
                      transition-all duration-200 hover:opacity-95"
           style={{
             background: '#0b1f3a',
             color: '#ffffff',
             padding: '8px 20px',
             boxShadow: '0 2px 10px rgba(11,31,58,0.25)',
           }}
           onMouseEnter={e => (e.currentTarget.style.background = '#162d50')}
           onMouseLeave={e => (e.currentTarget.style.background = '#0b1f3a')}>
          Connect your application <span style={{ marginLeft: 2 }}>→</span>
        </a>
      </nav>
    </div>
  );
}
