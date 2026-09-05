'use client';
import { useState, useEffect } from 'react';

const NAV_LINKS = [
  { label: 'Features',     href: '#features' },
  { label: 'How it works', href: '#how-it-works' },
  { label: 'Integrations', href: '#integrations' },
  { label: 'Blog',         href: '#blog' },
  { label: 'FAQs',         href: '#faqs' },
];

export default function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  useEffect(() => {
    const fn = () => setScrolled(window.scrollY > 8);
    window.addEventListener('scroll', fn, { passive: true });
    return () => window.removeEventListener('scroll', fn);
  }, []);

  return (
    <div className="fixed top-0 left-0 right-0 z-50 flex justify-center mt-90 px-6"
         style={{ pointerEvents: 'none' }}>
      <nav style={{ pointerEvents: 'auto' }}
           className={[
             'flex items-center gap-6 px-20 py-2.5 rounded-full',
             'border border-white/70',
             'transition-all duration-300',
             scrolled
               ? 'bg-white/85 backdrop-blur-2xl shadow-[0_8px_32px_rgba(37,99,235,0.18)]'
               : 'bg-white/80 backdrop-blur-xl  shadow-[0_4px_24px_rgba(37,99,235,0.13)]',
           ].join(' ')}>

        {/* Logo */}
        <a href="/" className="flex items-center gap-2 group flex-shrink-0">
          <div className="w-8 h-12 rounded-full flex items-center justify-center shadow-sm
                          group-hover:scale-105 transition-transform duration-200"
               style={{ background: 'linear-gradient(135deg,#3b82f6,#06b6d4)' }}>
            <svg width="18" height="18" viewBox="0 0 20 20" fill="none">
              <circle cx="10" cy="10" r="7"   stroke="white" strokeWidth="1.5"/>
              <circle cx="10" cy="10" r="3.8" stroke="white" strokeWidth="1.3" opacity=".7"/>
              <circle cx="10" cy="10" r="1.7" fill="white"/>
              <line x1="10" y1="3" x2="10" y2="1" stroke="white" strokeWidth="1.5" strokeLinecap="round"/>
              <line x1="17" y1="10" x2="19" y2="10" stroke="white" strokeWidth="1.5" strokeLinecap="round"/>
            </svg>
          </div>
          <span className="text-[15px] font-bold tracking-tight select-none"
                style={{ color: '#0b1f3a' }}>FaultLens</span>
        </a>

        {/* Links */}
        <ul className="flex items-center gap-6">
          {NAV_LINKS.map(l => (
            <li key={l.href}>
              <a href={l.href}
                 className="text-[13.5px] font-medium transition-colors duration-200"
                 style={{ color: '#4b5563' }}
                 onMouseEnter={e => (e.target.style.color = '#2563eb')}
                 onMouseLeave={e => (e.target.style.color = '#4b5563')}>
                {l.label}
              </a>
            </li>
          ))}
        </ul>

        {/* CTA */}
        <a href="#connect"
           className="flex items-center gap-1.5 px-5 py-2.5 rounded-full
                      font-semibold text-[13px] whitespace-nowrap
                      transition-all duration-200 hover:-translate-y-px"
           style={{
             background: '#0b1f3a',
             color: '#ffffff',
             boxShadow: '0 2px 12px rgba(11,31,58,0.30)',
           }}
           onMouseEnter={e => (e.currentTarget.style.background = '#162d50')}
           onMouseLeave={e => (e.currentTarget.style.background = '#0b1f3a')}>
          Connect your application <span>→</span>
        </a>
      </nav>
    </div>
  );
}
