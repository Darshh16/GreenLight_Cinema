import { useState, useEffect } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ScatterChart, Scatter, ZAxis } from 'recharts';
import LiquidGlass from './LiquidGlass';
import WikiAvatar from './WikiAvatar';
import { fetchAnalytics } from '../hooks/useApi';

const ChartTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="liquid-glass px-3 py-2 text-xs">
      <p className="font-bold text-[var(--color-text-main)] mb-1">{label}</p>
      {payload.map((e, i) => (
        <p key={i} style={{ color: e.color }}>{e.name}: {typeof e.value === 'number' ? e.value.toFixed(2) : e.value}</p>
      ))}
    </div>
  );
};

const legendStyle = { fontSize: 12, color: 'var(--color-text-muted)' };

export default function AnalyticsTab() {
  const [genreData, setGenreData] = useState([]);
  const [dirData, setDirData] = useState([]);
  const [actData, setActData] = useState([]);

  useEffect(() => {
    fetchAnalytics('genre_roi').then(setGenreData);
    fetchAnalytics('directors').then(setDirData);
    fetchAnalytics('actors').then(setActData);
  }, []);

  return (
    <div className="space-y-8">
      <div className="text-center animate-fade-slide-in">
        <h2 className="text-4xl italic mb-2">Performance Analytics</h2>
        <p className="text-[var(--color-text-muted)]">DuckDB-powered market intelligence across 3,600+ titles</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Genre ROI Bar Chart */}
        <LiquidGlass className="p-6 animate-fade-slide-in" style={{ animationDelay: '50ms' }}>
          <h3 className="text-lg italic mb-4">Top Genres by Median ROI</h3>
          <div style={{ width: '100%', height: 400 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={genreData.slice(0, 15)} margin={{ top: 10, right: 20, left: 10, bottom: 60 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" vertical={false} />
                <XAxis dataKey="genre" stroke="var(--color-text-muted)" tick={{ fontSize: 11 }} angle={-35} textAnchor="end" interval={0} />
                <YAxis stroke="var(--color-text-muted)" tick={{ fontSize: 11 }} label={{ value: 'ROI (x)', angle: -90, position: 'insideLeft', style: { fill: '#D1C9BE', fontSize: 11 } }} />
                <Tooltip content={<ChartTooltip />} />
                <Legend wrapperStyle={legendStyle} />
                <Bar dataKey="median_roi" name="Median ROI (x)" fill="#D4A94E" radius={[4, 4, 0, 0]} />
                <Bar dataKey="avg_rating" name="Avg Rating" fill="#00E5A0" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </LiquidGlass>

        {/* Risk vs Reward Scatter */}
        <LiquidGlass className="p-6 animate-fade-slide-in" style={{ animationDelay: '100ms' }}>
          <h3 className="text-lg italic mb-4">Risk vs. Reward</h3>
          <div style={{ width: '100%', height: 400 }}>
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart margin={{ top: 10, right: 20, left: 10, bottom: 40 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                <XAxis dataKey="avg_budget" name="Avg Budget" stroke="var(--color-text-muted)" tick={{ fontSize: 11 }} scale="log" domain={['auto', 'auto']} tickFormatter={v => `$${(v / 1e6).toFixed(0)}M`} label={{ value: 'Average Budget', position: 'insideBottom', offset: -25, style: { fill: '#D1C9BE', fontSize: 11 } }} />
                <YAxis dataKey="median_roi" name="Median ROI" stroke="var(--color-text-muted)" tick={{ fontSize: 11 }} label={{ value: 'Median ROI (x)', angle: -90, position: 'insideLeft', style: { fill: '#D1C9BE', fontSize: 11 } }} />
                <ZAxis dataKey="movie_count" name="Movie Count" range={[60, 500]} />
                <Tooltip content={<ChartTooltip />} cursor={{ strokeDasharray: '3 3', stroke: 'rgba(255,255,255,0.2)' }} />
                <Legend wrapperStyle={legendStyle} />
                <Scatter name="Genres (size = movie count)" data={genreData} fill="#D4A94E" opacity={0.85} />
              </ScatterChart>
            </ResponsiveContainer>
          </div>
        </LiquidGlass>
      </div>

      {/* Directors + Actors tables */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <LiquidGlass className="p-6 animate-fade-slide-in" style={{ animationDelay: '150ms' }}>
          <h3 className="text-lg italic mb-4">Top ROI Directors</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead><tr className="border-b border-white/10">
                <th className="text-left py-2 px-3 text-xs text-[var(--color-text-muted)] font-bold uppercase">Name</th>
                <th className="text-left py-2 px-3 text-xs text-[var(--color-text-muted)] font-bold uppercase">Median ROI</th>
                <th className="text-left py-2 px-3 text-xs text-[var(--color-text-muted)] font-bold uppercase">Films</th>
              </tr></thead>
              <tbody>
                {dirData.slice(0, 10).map((r, i) => (
                  <tr key={i} className="border-b border-white/5 hover:bg-white/[0.02] animate-fade-row" style={{ animationDelay: `${i * 50}ms` }}>
                    <td className="py-2 px-3 flex items-center gap-3">
                      <WikiAvatar name={r.name} className="w-8 h-8 rounded-full border border-[var(--color-gold)]/20 shadow-[0_0_8px_rgba(212,169,78,0.2)]" />
                      {r.name}
                    </td>
                    <td className="py-2 px-3 font-mono text-[var(--color-gold)]">{Number(r.median_roi).toFixed(2)}x</td>
                    <td className="py-2 px-3 text-[var(--color-text-muted)]">{r.movie_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </LiquidGlass>

        <LiquidGlass className="p-6 animate-fade-slide-in" style={{ animationDelay: '200ms' }}>
          <h3 className="text-lg italic mb-4">Top ROI Actors</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead><tr className="border-b border-white/10">
                <th className="text-left py-2 px-3 text-xs text-[var(--color-text-muted)] font-bold uppercase">Name</th>
                <th className="text-left py-2 px-3 text-xs text-[var(--color-text-muted)] font-bold uppercase">Median ROI</th>
                <th className="text-left py-2 px-3 text-xs text-[var(--color-text-muted)] font-bold uppercase">Films</th>
              </tr></thead>
              <tbody>
                {actData.slice(0, 10).map((r, i) => (
                  <tr key={i} className="border-b border-white/5 hover:bg-white/[0.02] animate-fade-row" style={{ animationDelay: `${i * 50}ms` }}>
                    <td className="py-2 px-3 flex items-center gap-3">
                      <WikiAvatar name={r.name} className="w-8 h-8 rounded-full border border-[var(--color-gold)]/20 shadow-[0_0_8px_rgba(212,169,78,0.2)]" />
                      {r.name}
                    </td>
                    <td className="py-2 px-3 font-mono text-[var(--color-gold)]">{Number(r.median_roi).toFixed(2)}x</td>
                    <td className="py-2 px-3 text-[var(--color-text-muted)]">{r.movie_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </LiquidGlass>
      </div>
    </div>
  );
}
