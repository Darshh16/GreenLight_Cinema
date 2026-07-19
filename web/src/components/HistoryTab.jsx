import { useState, useEffect } from 'react';
import LiquidGlass from './LiquidGlass';

export default function HistoryTab() {
  const [history, setHistory] = useState([]);
  const [expanded, setExpanded] = useState(null);

  useEffect(() => {
    const stored = JSON.parse(sessionStorage.getItem('gl_history') || '[]');
    setHistory(stored);
  }, []);

  if (!history.length) {
    return (
      <div className="text-center py-20 animate-fade-slide-in">
        <h2 className="text-4xl italic mb-3">Generation History</h2>
        <p className="text-[var(--color-text-muted)]">No synopses generated yet in this session.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="text-center animate-fade-slide-in">
        <h2 className="text-4xl italic mb-2">Generation History</h2>
        <p className="text-[var(--color-text-muted)]">{history.length} generation{history.length !== 1 ? 's' : ''} this session</p>
      </div>

      {history.map((item, idx) => {
        const isOpen = expanded === idx;
        const score = item.result?.score || 0;
        return (
          <LiquidGlass key={idx} className="animate-fade-slide-in" style={{ animationDelay: `${idx * 60}ms` }}>
            <button
              onClick={() => setExpanded(isOpen ? null : idx)}
              className="w-full flex items-center justify-between p-5 text-left cursor-pointer"
            >
              <div className="flex items-center gap-4">
                <span className="text-sm text-[var(--color-text-muted)] font-mono">{item.timestamp}</span>
                <span className="text-[var(--color-text-main)] font-semibold">{item.genre}</span>
                <span className="text-xs text-[var(--color-text-muted)]">${(item.budget / 1e6).toFixed(0)}M</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="font-mono text-[var(--color-gold)]">{score.toFixed(2)}</span>
                <span className="text-[var(--color-text-muted)] transition-transform" style={{ transform: isOpen ? 'rotate(180deg)' : '' }}>▾</span>
              </div>
            </button>
            {isOpen && (
              <div className="px-5 pb-5 border-t border-white/5 pt-4 space-y-3">
                {item.prompt && (
                  <p className="text-sm text-[var(--color-text-muted)]"><span className="font-bold">Prompt:</span> {item.prompt}</p>
                )}
                <div className="liquid-glass p-5 font-mono text-sm text-[var(--color-text-muted)] leading-relaxed whitespace-pre-wrap">
                  {item.result?.synopsis || 'No synopsis.'}
                </div>
              </div>
            )}
          </LiquidGlass>
        );
      })}
    </div>
  );
}
