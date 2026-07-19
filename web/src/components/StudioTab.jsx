import { useState, useEffect } from 'react';
import { Sparkles } from 'lucide-react';
import LiquidGlass from './LiquidGlass';
import { apiFetch, fetchAnalytics } from '../hooks/useApi';

const GENRES = ['Action', 'Science Fiction', 'Horror', 'Comedy', 'Drama', 'Romance', 'Crime', 'Fantasy'];
const BUDGETS = [
  { value: 5000000, label: '$5M' },
  { value: 30000000, label: '$30M' },
  { value: 50000000, label: '$50M' },
  { value: 100000000, label: '$100M' },
  { value: 200000000, label: '$200M' },
];
const PRESETS = [
  { label: 'Sci-Fi Mystery $50M', genre: 'Science Fiction', budget: 50000000, prompt: 'A mysterious signal from deep space lures a crew into a reality-bending trap.' },
  { label: 'Horror Survival $15M', genre: 'Horror', budget: 5000000, prompt: 'A group of hikers discovers an abandoned research facility in the mountains.' },
  { label: 'Action Comedy $100M', genre: 'Action', budget: 100000000, prompt: 'Two rival stunt performers must team up to pull off an impossible heist during a live movie shoot.' },
];
const STATUS_MSGS = [
  { at: 0, text: 'Initializing multi-agent workflow...' },
  { at: 10, text: 'Querying DuckDB for constraints...' },
  { at: 30, text: 'Retrieving script chunks from ChromaDB...' },
  { at: 50, text: 'Writer Agent drafting synopsis...' },
  { at: 70, text: 'Critic Agent evaluating market fit...' },
  { at: 80, text: 'Refiner Agent polishing narrative...' },
  { at: 90, text: 'Producer Agent calculating risk...' },
];

function getWikiImage(name) {
  return fetch(`https://en.wikipedia.org/w/api.php?action=query&titles=${encodeURIComponent(name)}&prop=pageimages&format=json&pithumbsize=100&origin=*`)
    .then(r => r.json())
    .then(d => {
      const pages = d.query.pages;
      const p = Object.values(pages)[0];
      return p?.thumbnail?.source || null;
    })
    .catch(() => null);
}

// -- Sub-components ----------------------------------------------------------

function MetricCard({ label, value, color }) {
  return (
    <LiquidGlass className="flex-1 p-5 border-t-2" style={{ borderTopColor: 'var(--color-gold)' }}>
      <div className="text-sm text-[var(--color-text-muted)]">{label}</div>
      <div className="text-3xl font-bold font-mono mt-1" style={{ color: color || 'var(--color-gold)' }}>{value}</div>
    </LiquidGlass>
  );
}

function ConstraintChips({ constraints }) {
  if (!constraints) return null;
  const tags = [
    constraints.target_budget_tier && `Budget: ${constraints.target_budget_tier}`,
    constraints.best_release_quarters?.length && `Release: ${constraints.best_release_quarters.join(', ')}`,
    constraints.expected_roi_multiplier && `Target ROI: ${constraints.expected_roi_multiplier}x`,
  ].filter(Boolean);

  return (
    <div className="flex gap-3 flex-wrap">
      {tags.map((t, i) => (
        <span key={i} className="liquid-glass px-4 py-2 rounded-full text-sm text-[var(--color-text-muted)] hover:text-[var(--color-gold)] transition-colors cursor-default">
          {t}
        </span>
      ))}
    </div>
  );
}

function TalentColumn({ title, names }) {
  const [images, setImages] = useState({});
  useEffect(() => {
    if (!names?.length) return;
    names.slice(0, 3).forEach(n => {
      getWikiImage(n).then(url => {
        if (url) setImages(prev => ({ ...prev, [n]: url }));
      });
    });
  }, [names]);

  return (
    <div className="flex-1">
      <div className="text-xs text-[var(--color-text-muted)] font-bold mb-3 uppercase tracking-wider">{title}</div>
      {(names || []).slice(0, 3).map((n, i) => (
        <div key={i} className="flex items-center gap-3 mb-2 text-sm text-[var(--color-text-muted)]">
          {images[n]
            ? <img src={images[n]} alt={n} className="w-8 h-8 rounded-full object-cover ring-1 ring-white/10" />
            : <div className="w-8 h-8 rounded-full bg-white/10 flex items-center justify-center text-xs font-bold">{n?.[0]}</div>
          }
          <span>{n}</span>
        </div>
      ))}
    </div>
  );
}

function CriticDial({ score }) {
  return (
    <div className="relative w-36 h-36 flex items-center justify-center">
      <div className="absolute inset-0 rounded-full" style={{
        background: 'conic-gradient(#00E5A0 0%, #D4A94E 50%, #FF4D6D 100%)',
        maskImage: 'radial-gradient(transparent 60%, black 61%)',
        WebkitMaskImage: 'radial-gradient(transparent 60%, black 61%)',
      }} />
      <span className="relative z-10 text-3xl font-bold font-mono text-[var(--color-text-main)]">{score.toFixed(2)}</span>
    </div>
  );
}

function TableCard({ title, data, columns }) {
  return (
    <LiquidGlass className="p-5">
      <h3 className="text-lg mb-4 italic">{title}</h3>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-white/10">
              {columns.map(c => (
                <th key={c.key} className="text-left py-2 px-3 text-[var(--color-text-muted)] font-semibold uppercase tracking-wider text-xs">{c.label}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {(data || []).slice(0, 10).map((row, i) => (
              <tr key={i} className="border-b border-white/5 hover:bg-white/[0.02] animate-fade-row" style={{ animationDelay: `${i * 60}ms` }}>
                {columns.map(c => (
                  <td key={c.key} className="py-2 px-3 text-[var(--color-text-main)]">
                    {c.format ? c.format(row[c.key]) : row[c.key]}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </LiquidGlass>
  );
}

// -- Main StudioTab ----------------------------------------------------------

export default function StudioTab() {
  const [genre, setGenre] = useState('Action');
  const [budget, setBudget] = useState(100000000);
  const [userPrompt, setUserPrompt] = useState('');
  const [isGenerating, setIsGenerating] = useState(false);
  const [progress, setProgress] = useState(0);
  const [statusMsg, setStatusMsg] = useState('');
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [genreRoi, setGenreRoi] = useState([]);
  const [directors, setDirectors] = useState([]);

  // Load market intelligence on mount
  useEffect(() => {
    fetchAnalytics('genre_roi').then(d => setGenreRoi(d));
    fetchAnalytics('directors').then(d => setDirectors(d));
  }, []);

  const applyPreset = (p) => {
    setGenre(p.genre);
    setBudget(p.budget);
    setUserPrompt(p.prompt);
  };

  const handleGenerate = async () => {
    setIsGenerating(true);
    setResult(null);
    setError(null);
    setProgress(0);

    // Animated progress
    const interval = setInterval(() => {
      setProgress(prev => {
        if (prev >= 89) { clearInterval(interval); return 89; }
        const next = prev + 1;
        const msg = [...STATUS_MSGS].reverse().find(m => m.at <= next);
        if (msg) setStatusMsg(msg.text);
        return next;
      });
    }, 50);

    try {
      const data = await apiFetch('/generate', {
        method: 'POST',
        body: JSON.stringify({ genre, budget, user_prompt: userPrompt, max_iterations: 3 }),
      });
      setResult(data);
      // Save to session history
      const hist = JSON.parse(sessionStorage.getItem('gl_history') || '[]');
      hist.unshift({ timestamp: new Date().toLocaleTimeString(), genre, budget, prompt: userPrompt, result: data });
      sessionStorage.setItem('gl_history', JSON.stringify(hist));
    } catch (e) {
      setError(e.message);
    } finally {
      clearInterval(interval);
      setProgress(100);
      setStatusMsg('');
      setIsGenerating(false);
    }
  };

  const score = result?.score || 0;
  const wc = result?.synopsis ? result.synopsis.split(/\s+/).length : 0;
  const conf = score > 0 ? Math.min(Math.round((score / 0.8) * 100), 99) : 0;
  const riskVal = result?.risk_score || 0;
  const riskColor = riskVal < 0.4 ? 'var(--color-green)' : riskVal < 0.7 ? 'var(--color-gold)' : 'var(--color-red)';
  const riskLabel = riskVal < 0.4 ? 'Low Risk' : riskVal < 0.7 ? 'Medium Risk' : 'High Risk';

  return (
    <div className="space-y-8">
      {/* Production Parameters */}
      <LiquidGlass className="p-6 animate-fade-slide-in" style={{ animationDelay: '50ms' }}>
        <h3 className="text-xl mb-5 italic">Production Parameters</h3>
        <div className="grid grid-cols-1 md:grid-cols-[1fr_2fr_1fr] gap-5">
          <div>
            <label className="block text-xs text-[var(--color-text-muted)] font-bold uppercase tracking-wider mb-2">Genre</label>
            <select value={genre} onChange={e => setGenre(e.target.value)}
              className="liquid-glass w-full px-4 py-3 text-[var(--color-gold)] font-semibold bg-transparent focus:outline-none focus:ring-1 focus:ring-[var(--color-gold)]/30">
              {GENRES.map(g => <option key={g} value={g} className="bg-[#111] text-white">{g}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-xs text-[var(--color-text-muted)] font-bold uppercase tracking-wider mb-2">Creative Prompt (Optional)</label>
            <textarea value={userPrompt} onChange={e => setUserPrompt(e.target.value)}
              placeholder="e.g. A retired hitman whose dog gets kidnapped..."
              className="liquid-glass w-full px-4 py-3 bg-transparent text-[var(--color-text-main)] placeholder-white/20 focus:outline-none focus:ring-1 focus:ring-[var(--color-gold)]/30 resize-none h-[68px]"
            />
          </div>
          <div>
            <label className="block text-xs text-[var(--color-text-muted)] font-bold uppercase tracking-wider mb-2">Budget</label>
            <select value={budget} onChange={e => setBudget(Number(e.target.value))}
              className="liquid-glass w-full px-4 py-3 text-[var(--color-gold)] font-semibold bg-transparent focus:outline-none focus:ring-1 focus:ring-[var(--color-gold)]/30">
              {BUDGETS.map(b => <option key={b.value} value={b.value} className="bg-[#111] text-white">{b.label}</option>)}
            </select>
          </div>
        </div>
        <button onClick={handleGenerate} disabled={isGenerating}
          className={`mt-5 w-full py-4 rounded-xl font-bold text-sm uppercase tracking-wider transition-all cursor-pointer
            ${isGenerating
              ? 'bg-white/5 text-[var(--color-text-muted)] cursor-not-allowed'
              : 'bg-gradient-to-r from-[var(--color-gold)] to-[var(--color-gold-dark)] text-[#050508] hover:-translate-y-0.5 hover:shadow-lg hover:shadow-[var(--color-gold)]/30 animate-pulse-glow-off'
            } ${isGenerating ? '' : ''}`}
        >
          {isGenerating ? 'Processing Workflow...' : 'Generate'}
        </button>
      </LiquidGlass>

      {/* Progress indicator */}
      {isGenerating && (
        <div className="liquid-glass flex items-center gap-4 px-5 py-4 border-l-4 border-[var(--color-gold)] animate-fade-slide-in">
          <div className="w-3 h-3 rounded-full bg-[var(--color-gold)] animate-pulse-dot shrink-0" />
          <div className="flex-1">
            <div className="text-sm font-mono text-[var(--color-gold)]">{statusMsg}</div>
            <div className="mt-2 h-1.5 bg-white/5 rounded-full overflow-hidden">
              <div className="h-full bg-[var(--color-gold)] rounded-full transition-all duration-300" style={{ width: `${progress}%` }} />
            </div>
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <LiquidGlass className="p-5 border-l-4 border-[var(--color-red)]">
          <p className="text-[var(--color-red)] text-sm">{error}</p>
        </LiquidGlass>
      )}



      {/* Inspiration Presets */}
      {!result && !isGenerating && (
        <div className="animate-fade-slide-in" style={{ animationDelay: '150ms' }}>
          <div className="flex items-center gap-2 mb-4">
            <Sparkles size={16} className="text-[var(--color-gold)]" />
            <span className="text-sm text-[var(--color-text-muted)] font-bold uppercase tracking-wider">Need Inspiration?</span>
          </div>
          <div className="flex flex-wrap gap-3">
            {PRESETS.map((p, i) => (
              <button key={i} onClick={() => applyPreset(p)}
                className="liquid-glass px-5 py-3 rounded-full text-sm text-[var(--color-text-muted)] hover:text-[var(--color-gold)] hover:shadow-lg hover:shadow-[var(--color-gold)]/10 transition-all hover:-translate-y-0.5 cursor-pointer">
                {p.label}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Market Intelligence Snapshot */}
      {!result && !isGenerating && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 animate-fade-slide-in" style={{ animationDelay: '200ms' }}>
          <TableCard
            title="Top Genres by ROI"
            data={genreRoi}
            columns={[
              { key: 'genre', label: 'Genre' },
              { key: 'median_roi', label: 'Median ROI', format: v => `${Number(v).toFixed(2)}x` },
            ]}
          />
          <TableCard
            title="Top Directors by ROI"
            data={directors}
            columns={[
              { key: 'name', label: 'Name' },
              { key: 'median_roi', label: 'Median ROI', format: v => `${Number(v).toFixed(2)}x` },
            ]}
          />
        </div>
      )}

      {/* ── Results ─────────────────────────────────────────────────────── */}
      {result && (
        <>
          {/* Metrics row */}
          <div className="flex gap-4 animate-fade-slide-in">
            <MetricCard label="Market Score" value={score.toFixed(2)} />
            <MetricCard label="Cycles" value={result.iterations} />
            <MetricCard label="Words" value={wc} />
            <MetricCard label="Confidence" value={`${conf}%`} color={conf > 80 ? 'var(--color-green)' : 'var(--color-gold)'} />
          </div>

          {/* Constraints + Talent */}
          <LiquidGlass className="p-6 animate-fade-slide-in" style={{ animationDelay: '50ms' }}>
            <h3 className="text-lg italic mb-4">Market Constraints</h3>
            <ConstraintChips constraints={result.constraints} />
            <div className="flex gap-4 mt-5">
              <TalentColumn title="Directors" names={result.constraints?.suggested_directors} />
              <TalentColumn title="Cast" names={result.constraints?.suggested_cast} />
              <TalentColumn title="Emerging Talent" names={result.constraints?.emerging_talent} />
            </div>
          </LiquidGlass>

          {/* Synopsis */}
          <LiquidGlass className="p-8 animate-fade-slide-in" style={{ animationDelay: '100ms' }}>
            <div className="font-mono text-[var(--color-text-muted)] leading-relaxed text-[15px] whitespace-pre-wrap">
              {result.synopsis}
            </div>
          </LiquidGlass>

          {/* Critic Score + Passed/Failed */}
          <LiquidGlass className="p-6 flex flex-col md:flex-row gap-8 animate-fade-slide-in" style={{ animationDelay: '150ms' }}>
            <div className="flex flex-col items-center justify-center border-r border-white/10 pr-8">
              <h3 className="text-lg italic mb-4">Critic Score</h3>
              <CriticDial score={score} />
            </div>
            <div className="flex-1 flex gap-6">
              <div className="flex-1">
                <h4 className="text-[var(--color-green)] font-bold mb-3">Passed</h4>
                {(result.critique?.passed_constraints || []).length > 0
                  ? result.critique.passed_constraints.map((c, i) => (
                      <div key={i} className="liquid-glass px-4 py-2.5 mb-2 border-l-2 border-[var(--color-green)] text-sm animate-fade-row" style={{ animationDelay: `${i * 80}ms` }}>✓ {c}</div>
                    ))
                  : <p className="text-sm text-[var(--color-text-muted)] italic">{score >= 0.8 ? 'Perfect alignment. All constraints satisfied.' : 'No passed constraints listed.'}</p>
                }
              </div>
              {(result.critique?.failed_constraints || []).length > 0 && (
                <div className="flex-1">
                  <h4 className="text-[var(--color-red)] font-bold mb-3">Failed</h4>
                  {result.critique.failed_constraints.map((c, i) => (
                    <div key={i} className="liquid-glass px-4 py-2.5 mb-2 border-l-2 border-[var(--color-red)] text-sm animate-fade-row" style={{ animationDelay: `${i * 80}ms` }}>✗ {c}</div>
                  ))}
                </div>
              )}
            </div>
          </LiquidGlass>

          {/* Producer Report */}
          <LiquidGlass className="p-6 animate-fade-slide-in" style={{ animationDelay: '200ms' }}>
            <h3 className="text-lg italic mb-5">Producer Report</h3>
            <div className="flex flex-col md:flex-row gap-10">
              <div className="flex-1">
                <h4 className="text-sm text-[var(--color-text-muted)] font-bold mb-4 uppercase tracking-wider">Estimated Budget Breakdown</h4>
                {Object.entries(result.budget_breakdown || {}).map(([k, v], i) => (
                  <div key={k} className="mb-4 animate-fade-row" style={{ animationDelay: `${i * 60}ms` }}>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-[var(--color-text-muted)]">{k}</span>
                      <span className="font-mono">{v}%</span>
                    </div>
                    <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
                      <div className="h-full bg-[var(--color-gold)] rounded-full transition-all duration-700" style={{ width: `${v}%` }} />
                    </div>
                  </div>
                ))}
              </div>
              <div className="flex-1 flex flex-col items-center justify-center">
                <h4 className="text-sm text-[var(--color-text-muted)] font-bold mb-4 uppercase tracking-wider">Greenlight Risk Assessment</h4>
                <div className="text-6xl font-mono font-bold" style={{ color: riskColor }}>{(riskVal * 100).toFixed(0)}%</div>
                <div className="mt-3 px-5 py-2 rounded-full text-sm font-bold border" style={{ color: riskColor, borderColor: riskColor }}>
                  {riskLabel}
                </div>
              </div>
            </div>
          </LiquidGlass>
        </>
      )}
    </div>
  );
}
