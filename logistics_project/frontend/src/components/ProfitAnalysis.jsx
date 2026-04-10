import { useState, useEffect } from 'react';
import {
  fetchProfitSummary, fetchProfitLanes, fetchProfitTrends,
  fetchProfitAlerts, fetchProfitDrilldown, fetchProfitInsights,
} from '../api';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  LineChart, Line, PieChart, Pie, Cell, Legend,
} from 'recharts';

const CATEGORY_CONFIG = {
  good: { label: 'Good Lane', color: '#10b981', icon: '🟢', bg: 'rgba(16,185,129,0.08)', border: 'rgba(16,185,129,0.25)' },
  low_margin: { label: 'Low Margin', color: '#f59e0b', icon: '🟡', bg: 'rgba(245,158,11,0.08)', border: 'rgba(245,158,11,0.25)' },
  bad: { label: 'Bad Lane', color: '#f43f5e', icon: '🔴', bg: 'rgba(244,63,94,0.08)', border: 'rgba(244,63,94,0.25)' },
  abnormal_loss: { label: 'Abnormal Loss', color: '#1e293b', icon: '⚫', bg: 'rgba(30,41,59,0.08)', border: 'rgba(30,41,59,0.25)' },
  abnormal_profit: { label: 'Abnormal Profit', color: '#8b5cf6', icon: '🟣', bg: 'rgba(139,92,246,0.08)', border: 'rgba(139,92,246,0.25)' },
};

const ALERT_COLOR = {
  red: { bg: 'rgba(244,63,94,0.06)', border: 'rgba(244,63,94,0.2)', text: '#be123c' },
  yellow: { bg: 'rgba(245,158,11,0.06)', border: 'rgba(245,158,11,0.2)', text: '#92400e' },
  green: { bg: 'rgba(16,185,129,0.06)', border: 'rgba(16,185,129,0.2)', text: '#065f46' },
  purple: { bg: 'rgba(139,92,246,0.06)', border: 'rgba(139,92,246,0.2)', text: '#5b21b6' },
};

const fmt = (val) => {
  if (val === undefined || val === null || isNaN(val)) return '₹0';
  const num = Number(val);
  if (num >= 10000000) return `₹${(num / 10000000).toFixed(2)} Cr`;
  if (num >= 100000) return `₹${(num / 100000).toFixed(2)} L`;
  return `₹${num.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;
};

export default function ProfitAnalysis() {
  const [summary, setSummary] = useState(null);
  const [lanes, setLanes] = useState(null);
  const [trends, setTrends] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [insights, setInsights] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [drilldown, setDrilldown] = useState(null);
  const [drillLoading, setDrillLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('overview');
  const [categoryFilter, setCategoryFilter] = useState('all');

  useEffect(() => {
    loadAll();
  }, []);

  const loadAll = async () => {
    setLoading(true); setError(null);
    try {
      const [s, l, t, a, ins] = await Promise.all([
        fetchProfitSummary(), fetchProfitLanes(), fetchProfitTrends(),
        fetchProfitAlerts(), fetchProfitInsights(),
      ]);
      setSummary(s); setLanes(l); setTrends(t); setAlerts(a); setInsights(ins);
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  };

  const openDrilldown = async (loadingCity, deliveryCity) => {
    setDrillLoading(true);
    try {
      const d = await fetchProfitDrilldown(loadingCity, deliveryCity);
      setDrilldown(d);
    } catch (e) { alert(`Error: ${e.message}`); }
    finally { setDrillLoading(false); }
  };

  if (loading) return <div style={{ padding: '3rem', textAlign: 'center', color: '#94a3b8' }}>⏳ Loading Profit Intelligence...</div>;
  if (error) return <div style={{ padding: '2rem', color: '#f43f5e' }}>Error: {error}</div>;
  if (summary?.error) return <div style={{ padding: '3rem', textAlign: 'center', color: '#94a3b8' }}><div style={{ fontSize: '3rem', marginBottom: '1rem' }}>📊</div><p>No profit data available. Upload a Gross Margin MIS file to get started.</p></div>;

  const filteredLanes = lanes?.lanes?.filter(l => categoryFilter === 'all' || l.category === categoryFilter) || [];

  // Pie data for lane distribution
  const pieData = lanes?.summary ? Object.entries(lanes.summary).filter(([,v]) => v > 0).map(([k, v]) => ({
    name: CATEGORY_CONFIG[k]?.label || k, value: v, color: CATEGORY_CONFIG[k]?.color || '#94a3b8'
  })) : [];

  const tabs = [
    { key: 'overview', label: '📊 Overview' },
    { key: 'lanes', label: '🛤️ Lanes' },
    { key: 'trends', label: '📈 Trends' },
    { key: 'alerts', label: `🚨 Alerts (${alerts.length})` },
    { key: 'insights', label: '💡 Insights' },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Tab Navigation */}
      <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
        {tabs.map(t => (
          <button key={t.key} onClick={() => setActiveTab(t.key)} style={{
            padding: '0.5rem 1.25rem', borderRadius: '999px', border: activeTab === t.key ? '2px solid #3b82f6' : '1px solid #e2e8f0',
            background: activeTab === t.key ? 'rgba(59,130,246,0.08)' : '#fff', color: activeTab === t.key ? '#3b82f6' : '#64748b',
            fontWeight: 600, fontSize: '0.85rem', cursor: 'pointer', transition: 'all 0.2s', fontFamily: 'inherit',
          }}>{t.label}</button>
        ))}
      </div>

      {/* ──── OVERVIEW TAB ──── */}
      {activeTab === 'overview' && (
        <>
          {/* KPI Cards */}
          <div className="kpi-grid">
            {[
              { label: 'Total Freight', value: fmt(summary.total_freight), icon: '💰', color: 'blue', sub: `${summary.total_records} records` },
              { label: 'Total Cost', value: fmt(summary.total_cost), icon: '📦', color: 'amber', sub: 'Transport + Operations' },
              { label: 'Gross Profit (GM1)', value: fmt(summary.total_profit), icon: summary.total_profit >= 0 ? '📈' : '📉', color: summary.total_profit >= 0 ? 'emerald' : 'rose', sub: `Final GM7: ${fmt(summary.final_profit_gm7)}` },
              { label: 'Avg Profit/Tonne', value: `₹${summary.avg_profit_per_tonne?.toLocaleString('en-IN') || 0}`, icon: '⚖️', color: 'violet', sub: `${summary.total_weight?.toFixed(0)} MT total` },
              { label: 'Overall Margin', value: `${summary.overall_margin_pct}%`, icon: '🎯', color: summary.overall_margin_pct >= 3 ? 'emerald' : 'rose', sub: summary.overall_margin_pct >= 3 ? 'Healthy' : 'Needs Attention' },
            ].map((kpi, i) => (
              <div key={i} className={`kpi-card ${kpi.color}`}>
                <div className="kpi-header">
                  <div className={`kpi-icon ${kpi.color}`}>{kpi.icon}</div>
                </div>
                <div className="kpi-label">{kpi.label}</div>
                <div className="kpi-value">{kpi.value}</div>
                <div className="kpi-sub">{kpi.sub}</div>
              </div>
            ))}
          </div>

          {/* Lane Distribution + Top Alerts */}
          <div className="charts-grid">
            <div className="chart-card">
              <div className="chart-header"><div><div className="chart-title">Lane Health Distribution</div><div className="chart-subtitle">Classification of all routes</div></div></div>
              {pieData.length > 0 ? (
                <ResponsiveContainer width="100%" height={280}>
                  <PieChart>
                    <Pie data={pieData} cx="50%" cy="50%" innerRadius={60} outerRadius={100} dataKey="value" labelLine={false}
                      label={({ name, value }) => `${name}: ${value}`}>
                      {pieData.map((e, i) => <Cell key={i} fill={e.color} />)}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              ) : <p style={{ color: '#94a3b8', textAlign: 'center', padding: '3rem' }}>No lane data</p>}
            </div>

            <div className="chart-card">
              <div className="chart-header"><div><div className="chart-title">Priority Alerts</div><div className="chart-subtitle">Top issues requiring attention</div></div></div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', maxHeight: '260px', overflowY: 'auto' }}>
                {alerts.slice(0, 5).map((a, i) => {
                  const c = ALERT_COLOR[a.level] || ALERT_COLOR.yellow;
                  return (
                    <div key={i} style={{ padding: '0.75rem', background: c.bg, border: `1px solid ${c.border}`, borderRadius: '10px', fontSize: '0.82rem' }}>
                      <div style={{ fontWeight: 700, color: c.text, marginBottom: '0.25rem' }}>{a.title}</div>
                      <div style={{ color: '#475569', lineHeight: 1.4 }}>{a.insight}</div>
                    </div>
                  );
                })}
                {alerts.length === 0 && <p style={{ color: '#94a3b8', textAlign: 'center', padding: '2rem' }}>No alerts — all lanes operating normally.</p>}
              </div>
            </div>
          </div>

          {/* Quick Insights */}
          {insights.length > 0 && (
            <div className="chart-card">
              <div className="chart-header"><div><div className="chart-title">💡 Decision Intelligence</div><div className="chart-subtitle">Auto-generated insights from your data</div></div></div>
              <ul className="insights-list">
                {insights.map((ins, i) => (
                  <li key={i} className="insight-item">
                    <span className="insight-icon">{ins.type === 'success' ? '✅' : ins.type === 'danger' ? '🚨' : '⚠️'}</span>
                    <div>
                      <div style={{ fontWeight: 600, color: '#0f172a', marginBottom: '0.25rem' }}>{ins.text}</div>
                      <div style={{ fontSize: '0.8rem', color: '#64748b', fontStyle: 'italic' }}>→ {ins.suggestion}</div>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </>
      )}

      {/* ──── LANES TAB ──── */}
      {activeTab === 'lanes' && (
        <>
          {/* Category Filter Chips */}
          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
            {[{ key: 'all', label: 'All Lanes' }, ...Object.entries(CATEGORY_CONFIG).map(([k, v]) => ({ key: k, label: `${v.icon} ${v.label}` }))].map(f => (
              <button key={f.key} onClick={() => setCategoryFilter(f.key)} style={{
                padding: '0.4rem 1rem', borderRadius: '999px', fontSize: '0.8rem', fontWeight: 600, cursor: 'pointer',
                background: categoryFilter === f.key ? '#1e293b' : '#fff', color: categoryFilter === f.key ? '#fff' : '#475569',
                border: `1px solid ${categoryFilter === f.key ? '#1e293b' : '#e2e8f0'}`, transition: 'all 0.2s', fontFamily: 'inherit',
              }}>{f.label} {f.key !== 'all' && lanes?.summary?.[f.key] ? `(${lanes.summary[f.key]})` : ''}</button>
            ))}
          </div>

          {/* Lane Cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))', gap: '1rem' }}>
            {filteredLanes.map((lane, i) => {
              const cat = CATEGORY_CONFIG[lane.category] || CATEGORY_CONFIG.good;
              return (
                <div key={i} onClick={() => openDrilldown(lane.loading_city, lane.delivery_city)}
                  style={{
                    background: '#fff', border: `1px solid ${cat.border}`, borderRadius: '14px', padding: '1.25rem',
                    cursor: 'pointer', transition: 'all 0.2s', borderLeft: `4px solid ${cat.color}`,
                  }}
                  onMouseEnter={e => { e.currentTarget.style.transform = 'translateY(-2px)'; e.currentTarget.style.boxShadow = '0 8px 20px rgba(0,0,0,0.06)'; }}
                  onMouseLeave={e => { e.currentTarget.style.transform = ''; e.currentTarget.style.boxShadow = ''; }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                    <div style={{ fontSize: '0.95rem', fontWeight: 700, color: '#0f172a' }}>{lane.lane_name}</div>
                    <span style={{ fontSize: '0.7rem', fontWeight: 700, color: cat.color, background: cat.bg, padding: '2px 10px', borderRadius: '999px', border: `1px solid ${cat.border}` }}>{cat.label}</span>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0.6rem' }}>
                    {[
                      { label: 'Freight', value: fmt(lane.total_freight) },
                      { label: 'Cost', value: fmt(lane.total_cost) },
                      { label: 'Profit', value: fmt(lane.total_profit) },
                      { label: 'Margin', value: `${lane.margin_pct}%` },
                      { label: 'Shipments', value: lane.total_shipments },
                      { label: 'Cost/T', value: `₹${lane.cost_per_tonne?.toLocaleString('en-IN') || 0}` },
                    ].map((m, j) => (
                      <div key={j}>
                        <div style={{ fontSize: '0.6rem', color: '#94a3b8', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>{m.label}</div>
                        <div style={{ fontSize: '0.82rem', fontWeight: 700, color: '#0f172a' }}>{m.value}</div>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </>
      )}

      {/* ──── TRENDS TAB ──── */}
      {activeTab === 'trends' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          {trends.filter(t => t.data.length >= 2).slice(0, 10).map((t, i) => (
            <div key={i} className="chart-card">
              <div className="chart-header">
                <div>
                  <div className="chart-title">{t.lane_name}</div>
                  <div className="chart-subtitle">
                    {t.trend === 'increasing' ? `📈 Cost increased by ${t.pct_change}%` :
                     t.trend === 'decreasing' ? `📉 Cost decreased by ${Math.abs(t.pct_change)}%` :
                     '➡️ Stable cost trend'}
                  </div>
                </div>
                <span style={{
                  padding: '0.3rem 0.8rem', borderRadius: '999px', fontSize: '0.7rem', fontWeight: 700,
                  background: t.trend === 'increasing' ? 'rgba(244,63,94,0.1)' : t.trend === 'decreasing' ? 'rgba(16,185,129,0.1)' : 'rgba(148,163,184,0.1)',
                  color: t.trend === 'increasing' ? '#f43f5e' : t.trend === 'decreasing' ? '#10b981' : '#94a3b8',
                }}>{t.pct_change > 0 ? '+' : ''}{t.pct_change}%</span>
              </div>
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={t.data}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(0,0,0,0.05)" />
                  <XAxis dataKey="month" tick={{ fontSize: 11, fill: '#94a3b8' }} />
                  <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} />
                  <Tooltip contentStyle={{ background: 'rgba(255,255,255,0.95)', border: '1px solid rgba(0,0,0,0.08)', borderRadius: '8px', fontSize: '0.82rem' }} />
                  <Line type="monotone" dataKey="cost_per_tonne" name="Cost/Tonne" stroke="#3b82f6" strokeWidth={2.5} dot={{ r: 4 }} />
                  <Line type="monotone" dataKey="profit" name="Profit" stroke="#10b981" strokeWidth={2} dot={{ r: 3 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          ))}
          {trends.filter(t => t.data.length >= 2).length === 0 && (
            <div style={{ padding: '3rem', textAlign: 'center', color: '#94a3b8' }}>Need 2+ months of data for trend analysis.</div>
          )}
        </div>
      )}

      {/* ──── ALERTS TAB ──── */}
      {activeTab === 'alerts' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(400px, 1fr))', gap: '1rem' }}>
          {alerts.map((a, i) => {
            const c = ALERT_COLOR[a.level] || ALERT_COLOR.yellow;
            return (
              <div key={i} style={{ background: c.bg, border: `1px solid ${c.border}`, borderRadius: '14px', padding: '1.25rem', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                <div style={{ fontWeight: 700, color: c.text, fontSize: '1rem' }}>{a.title}</div>
                <p style={{ fontSize: '0.9rem', color: '#1e293b', lineHeight: 1.5, margin: 0 }}>{a.insight}</p>
                <div style={{ marginTop: 'auto', fontSize: '0.82rem', color: '#475569', background: 'rgba(255,255,255,0.7)', padding: '0.75rem', borderRadius: '8px', borderLeft: `3px solid ${c.border}` }}>
                  {a.recommendation}
                </div>
              </div>
            );
          })}
          {alerts.length === 0 && <div style={{ padding: '3rem', textAlign: 'center', color: '#94a3b8', gridColumn: '1/-1' }}>✅ No alerts — all lanes operating within expected parameters.</div>}
        </div>
      )}

      {/* ──── INSIGHTS TAB ──── */}
      {activeTab === 'insights' && (
        <div className="chart-card">
          <div className="chart-header"><div><div className="chart-title">🧠 AI-Powered Profit Insights</div><div className="chart-subtitle">What's happening and why — with actionable recommendations</div></div></div>
          {insights.length > 0 ? (
            <ul className="insights-list">
              {insights.map((ins, i) => (
                <li key={i} className="insight-item" style={{ flexDirection: 'column', gap: '0.5rem' }}>
                  <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'flex-start' }}>
                    <span className="insight-icon" style={{ fontSize: '1.1rem' }}>{ins.type === 'success' ? '✅' : ins.type === 'danger' ? '🚨' : '⚠️'}</span>
                    <div style={{ fontWeight: 600, color: '#0f172a', lineHeight: 1.5 }}>{ins.text}</div>
                  </div>
                  <div style={{ marginLeft: '2rem', padding: '0.6rem 1rem', background: 'rgba(59,130,246,0.04)', border: '1px solid rgba(59,130,246,0.1)', borderRadius: '8px', fontSize: '0.82rem', color: '#1e40af' }}>
                    💡 <strong>Recommendation:</strong> {ins.suggestion}
                  </div>
                </li>
              ))}
            </ul>
          ) : <p style={{ padding: '3rem', textAlign: 'center', color: '#94a3b8' }}>Upload profit data to see AI-generated insights.</p>}
        </div>
      )}

      {/* ──── DRILLDOWN MODAL ──── */}
      {drilldown && !drilldown.error && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '2rem' }}
          onClick={() => setDrilldown(null)}>
          <div onClick={e => e.stopPropagation()} style={{ background: '#fff', borderRadius: '16px', padding: '2rem', maxWidth: '700px', width: '100%', maxHeight: '85vh', overflowY: 'auto', boxShadow: '0 20px 60px rgba(0,0,0,0.15)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
              <div>
                <h2 style={{ margin: 0, fontSize: '1.15rem', fontWeight: 700 }}>{drilldown.lane_name}</h2>
                <p style={{ margin: '0.25rem 0 0', color: '#64748b', fontSize: '0.82rem' }}>{drilldown.total_shipments} shipments · {drilldown.total_weight} MT · Margin: {drilldown.margin_pct}%</p>
              </div>
              <button onClick={() => setDrilldown(null)} style={{ background: 'transparent', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '0.4rem 1rem', cursor: 'pointer', fontFamily: 'inherit', fontWeight: 600, color: '#64748b' }}>✕ Close</button>
            </div>

            <h3 style={{ fontSize: '0.9rem', fontWeight: 700, color: '#475569', marginBottom: '0.75rem' }}>Margin Waterfall (Freight → GM7)</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
              {drilldown.waterfall?.map((w, i) => {
                const isPositive = w.value >= 0;
                const maxVal = Math.max(...drilldown.waterfall.map(x => Math.abs(x.value)), 1);
                const barWidth = Math.min(Math.abs(w.value) / maxVal * 100, 100);
                const barColor = w.type === 'revenue' ? '#3b82f6' : w.type === 'margin' ? '#10b981' : w.type === 'final' ? '#8b5cf6' : w.type === 'deduction' ? '#f59e0b' : '#f43f5e';
                return (
                  <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', padding: '0.4rem 0' }}>
                    <div style={{ width: '140px', fontSize: '0.75rem', color: '#475569', fontWeight: 500, flexShrink: 0 }}>{w.label}</div>
                    <div style={{ flex: 1, height: '18px', background: '#f1f5f9', borderRadius: '4px', overflow: 'hidden', position: 'relative' }}>
                      <div style={{ width: `${barWidth}%`, height: '100%', background: barColor, borderRadius: '4px', transition: 'width 0.5s ease' }} />
                    </div>
                    <div style={{ width: '90px', textAlign: 'right', fontSize: '0.78rem', fontWeight: 700, color: isPositive ? '#10b981' : '#f43f5e' }}>
                      {isPositive ? '+' : ''}{fmt(w.value)}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
