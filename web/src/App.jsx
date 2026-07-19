import { useState, useRef } from 'react';
import { Film, BarChart3, Clock, Menu, X } from 'lucide-react';
import VideoBackground, { SCENES } from './components/VideoBackground';
import LiquidGlass from './components/LiquidGlass';
import StudioTab from './components/StudioTab';
import AnalyticsTab from './components/AnalyticsTab';
import HistoryTab from './components/HistoryTab';
import './index.css';

const TABS = [
  { key: 'Studio', icon: Film },
  { key: 'Analytics', icon: BarChart3 },
  { key: 'History', icon: Clock },
];

export default function App() {
  const [currentTab, setCurrentTab] = useState('Studio');
  const [activeScene, setActiveScene] = useState(0);
  const [transitioning, setTransitioning] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const cooldownRef = useRef(false);

  const handleSceneChange = (idx) => {
    if (cooldownRef.current || idx === activeScene) return;
    cooldownRef.current = true;
    setTransitioning(true);
    setActiveScene(idx);
    setTimeout(() => {
      setTransitioning(false);
      cooldownRef.current = false;
    }, 1000);
  };

  return (
    <>
      <VideoBackground activeScene={activeScene} />

      {/* Main content (above video, inset exactly inside the TV screen hole) */}
      <div className="fixed z-10 overflow-y-auto overflow-x-hidden tv-screen-content"
           style={{
             top: 'clamp(40px, 5vw, 75px)',
             bottom: 'clamp(45px, 5.5vw, 90px)',
             left: 'clamp(30px, 4vw, 60px)',
             right: 'clamp(30px, 4vw, 60px)',
             borderRadius: '40px',
             paddingTop: '24px',
           }}>
        {/* ── Top Nav ───────────────────────────────────────────────── */}
        <header className="px-4 md:px-6 pt-4">
          <LiquidGlass className="flex items-center justify-between px-4 md:px-6 py-3 animate-fade-slide-in">
            {/* Logo */}
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[var(--color-gold)] to-[var(--color-gold-dark)] flex items-center justify-center text-[#0a0a0f] font-bold text-sm">G</div>
              <div className="hidden sm:block">
                <div className="text-sm font-bold tracking-wide text-[var(--color-text-main)]">Greenlight Cinema</div>
                <div className="text-[10px] text-[var(--color-text-muted)] uppercase tracking-widest">AI Validation</div>
              </div>
            </div>

            {/* Desktop Nav */}
            <div className="hidden md:flex items-center gap-2">
              <span className="text-[11px] text-[var(--color-text-muted)] mr-2 font-mono">Zach1209/Greenlight-Cinema</span>
              <span className="text-[10px] text-[var(--color-green)] flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-green)] animate-pulse-dot inline-block" />
                Running
              </span>
            </div>

            {/* Mobile hamburger */}
            <button onClick={() => setMobileMenuOpen(!mobileMenuOpen)} className="md:hidden text-[var(--color-text-muted)] cursor-pointer">
              {mobileMenuOpen ? <X size={20} /> : <Menu size={20} />}
            </button>
          </LiquidGlass>

          {/* Mobile menu dropdown */}
          {mobileMenuOpen && (
            <LiquidGlass className="md:hidden mt-2 p-3 space-y-2 animate-fade-slide-in">
              {TABS.map(t => (
                <button key={t.key}
                  onClick={() => { setCurrentTab(t.key); setMobileMenuOpen(false); }}
                  className={`w-full text-left px-4 py-2.5 rounded-lg text-sm font-semibold flex items-center gap-2 cursor-pointer transition-colors
                    ${currentTab === t.key ? 'bg-gradient-to-r from-[var(--color-gold)] to-[var(--color-gold-dark)] text-[#050508]' : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-main)]'}`}>
                  <t.icon size={14} />{t.key}
                </button>
              ))}
            </LiquidGlass>
          )}
        </header>

        {/* ── Hero ──────────────────────────────────────────────────── */}
        <div className="px-4 md:px-6 mt-6">
          <div className="relative border-b border-[var(--color-gold)]/30 pb-8 mb-6 animate-fade-slide-in" style={{ animationDelay: '50ms' }}>
            {/* Studio Mode badge */}
            <div className="absolute right-0 top-0">
              <LiquidGlass className="flex items-center gap-2 px-3 py-1.5 rounded-full">
                <span className="w-2 h-2 rounded-full bg-[var(--color-green)] animate-pulse-dot" />
                <span className="text-[11px] font-mono text-[var(--color-green)] uppercase tracking-wider">Studio Mode Active</span>
              </LiquidGlass>
            </div>
            <h1 className="text-5xl md:text-6xl italic text-[var(--color-gold)]">Welcome to Greenlight Cinema</h1>
            <p className="text-lg text-[var(--color-text-muted)] mt-3 max-w-3xl leading-relaxed">
              Our multi-agent AI pipeline drafts, critiques, refines, and validates movie synopses against real box-office data. Choose your genre, set a budget, and let the agents work.
            </p>
          </div>
        </div>

        {/* ── Tab Row + Scene Switcher ──────────────────────────────── */}
        <div className="px-4 md:px-6 mb-8 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 animate-fade-slide-in" style={{ animationDelay: '100ms' }}>
          {/* Tab pills */}
          <LiquidGlass className="hidden md:inline-flex items-center gap-1 p-1.5 rounded-full">
            {TABS.map(t => (
              <button key={t.key} onClick={() => setCurrentTab(t.key)}
                className={`flex items-center gap-2 px-5 py-2.5 rounded-full text-sm font-semibold transition-all cursor-pointer
                  ${currentTab === t.key
                    ? 'bg-gradient-to-r from-[var(--color-gold)] to-[var(--color-gold-dark)] text-[#050508] shadow-lg shadow-[var(--color-gold)]/30'
                    : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-main)]'}`}>
                <t.icon size={14} />{t.key}
              </button>
            ))}
          </LiquidGlass>

          {/* Scene switcher */}
          <LiquidGlass className="inline-flex items-center px-4 py-2 rounded-full">
            <select
              value={activeScene}
              onChange={e => handleSceneChange(Number(e.target.value))}
              disabled={transitioning}
              className="bg-transparent text-sm text-[var(--color-text-muted)] focus:outline-none cursor-pointer disabled:opacity-50 pr-6"
            >
              {SCENES.map((s, i) => (
                <option key={i} value={i} className="bg-[#111] text-white">{s.label}</option>
              ))}
            </select>
          </LiquidGlass>
        </div>

        {/* ── Tab Content ──────────────────────────────────────────── */}
        <main className="px-4 md:px-6 pb-20 max-w-[1200px] mx-auto">
          {currentTab === 'Studio' && <StudioTab />}
          {currentTab === 'Analytics' && <AnalyticsTab />}
          {currentTab === 'History' && <HistoryTab />}
        </main>
      </div>
    </>
  );
}
