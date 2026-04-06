import { useState, useEffect, useCallback, useRef } from 'react';
import './index.css';
import {
  fetchSummary, fetchRevenueTrends, fetchTopRoutes, fetchSmartInsights,
  fetchUploadHistory, fetchRootCause, fetchRisk,
  fetchQuality, fetchDrilldown, uploadFile, fetchAIAnalysis, deleteUpload, fetchShipments
} from './api';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  LineChart, Line, AreaChart, Area, PieChart, Pie, Cell, Legend,
} from 'recharts';
import { useAuth } from './context/AuthContext';
import LoginPage from './components/LoginPage';
import DriverPanel from './components/DriverPanel';
import CustomerPanel from './components/CustomerPanel';
import NotificationBell from './components/NotificationBell';

// ─── Constants ─────────────────────────────────────────
const COLORS = {
  blue: '#3b82f6', emerald: '#10b981', rose: '#f43f5e',
  amber: '#f59e0b', violet: '#8b5cf6', cyan: '#06b6d4',
};

const TOOLTIP_STYLE = {
  contentStyle: {
    background: 'rgba(255, 255, 255, 0.95)', border: '1px solid rgba(0,0,0,0.08)',
    borderRadius: '8px', color: '#0f172a', fontSize: '0.82rem', padding: '0.75rem 1rem',
    boxShadow: '0 4px 10px rgba(0,0,0,0.05)'
  },
};

const RISK_COLORS = { high: '#f43f5e', medium: '#f59e0b', low: '#10b981' };
const INSIGHT_ICONS = { success: '✅', warning: '⚠️', danger: '🚨', info: '💡' };

const NAV_ITEMS = [
  { key: 'dashboard', icon: '📊', label: 'Dashboard' },
  { key: 'analytics', icon: '🔍', label: 'Analytics' },
  { key: 'ai', icon: '🤖', label: 'AI Copilot' },
  { key: 'upload', icon: '📁', label: 'Upload Data' },
  { key: 'history', icon: '📋', label: 'History' },
];

const PAGE_META = {
  dashboard: { title: 'Command Center', sub: 'Real-time logistics overview and key metrics' },
  analytics: { title: 'Deep Analytics', sub: 'Root cause analysis and risk prediction' },
  ai: { title: 'AI Copilot', sub: 'Gemini-powered logistics intelligence' },
  upload: { title: 'Upload Data', sub: 'Import your shipment files' },
  history: { title: 'Upload History', sub: 'Track all your data imports' },
};

// ═══════════════════════════════════════════════════════════
// APP — Auth-aware router
// ═══════════════════════════════════════════════════════════
export default function App() {
  const { user, loading: authLoading, logout } = useAuth();

  // While verifying stored JWT, show a minimal splash
  if (authLoading) {
    return (
      <div style={{
        minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
        background: '#0F172A', color: '#64748B', fontFamily: 'Inter, sans-serif', fontSize: '1rem',
      }}>
        ⏳ Authenticating…
      </div>
    );
  }

  // Not logged in → show login page
  if (!user) {
    return <LoginPage onLoginSuccess={() => {}} />;
  }

  // Logged in as driver → Driver Panel
  if (user.role === 'driver') return <DriverPanel />;

  // Logged in as customer → Customer Panel
  if (user.role === 'customer') return <CustomerPanel />;

  // Logged in as manager → Full Intelligence Dashboard
  return <ManagerDashboard user={user} onLogout={logout} />;
}


// ═══════════════════════════════════════════════════════════
// MANAGER DASHBOARD (the original full analytics app)
// ═══════════════════════════════════════════════════════════
function ManagerDashboard({ user, onLogout }) {
  const [tab, setTab] = useState('dashboard');
  const [summary, setSummary] = useState(null);
  const [revenueTrends, setRevenueTrends] = useState([]);
  const [topRoutes, setTopRoutes] = useState([]);
  const [insights, setInsights] = useState([]);
  const [uploads, setUploads] = useState([]);
  const [rootCause, setRootCause] = useState(null);
  const [risk, setRisk] = useState(null);
  const [quality, setQuality] = useState(null);
  const [cnMatches, setCnMatches] = useState([]);
  const [drilldown, setDrilldown] = useState(null);
  const [drilldownType, setDrilldownType] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [logoError, setLogoError] = useState(false);
  const [filters, setFilters] = useState({ date_from: '', date_to: '', origin: '', destination: '', vehicle_type: '', transporter_name: '', booking_region: '', material: '', cnno: '' });
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const loadDashboard = useCallback(async (f) => {
    setLoading(true); setError(null);
    try {
      const cnno = (f?.cnno || '').trim();
      const [s, t, r, i, u, q] = await Promise.all([
        fetchSummary(f), fetchRevenueTrends({ ...f, group_by: 'day' }),
        fetchTopRoutes(f), fetchSmartInsights(f), fetchUploadHistory(),
        fetchQuality(),
      ]);
      setSummary(s); setRevenueTrends(t); setTopRoutes(r);
      setInsights(i.insights || []); setUploads(u.results || []);
      setQuality(q);
      if (cnno) {
        const shipmentRes = await fetchShipments({ ...f, page_size: 25 });
        setCnMatches(shipmentRes.results || []);
      } else {
        setCnMatches([]);
      }
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  }, []);

  const loadAnalytics = useCallback(async (f) => {
    setLoading(true); setError(null);
    try {
      const [rc, rk] = await Promise.all([fetchRootCause(f), fetchRisk(f)]);
      setRootCause(rc); setRisk(rk);
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { loadDashboard(filters); }, []);
  useEffect(() => {
    if (tab === 'analytics' && !rootCause) loadAnalytics(filters);
  }, [tab]);

  const handleFilter = () => { loadDashboard(filters); if (rootCause) loadAnalytics(filters); };
  const handleClear = useCallback(() => {
    const e = { date_from: '', date_to: '', origin: '', destination: '', vehicle_type: '', transporter_name: '', booking_region: '', material: '', cnno: '' };
    setFilters(e); loadDashboard(e);
  }, []);

  const openDrilldown = async (type) => {
    setDrilldownType(type);
    try {
      const res = await fetchDrilldown({ ...filters, filter: type, page_size: 5000 });
      setDrilldown(res.results || []);
    } catch { setDrilldown([]); }
  };

  const switchTab = (t) => { setTab(t); setSidebarOpen(false); };
  const meta = PAGE_META[tab] || PAGE_META.dashboard;

  return (
    <div className="app">
      <div className={`sidebar-overlay ${sidebarOpen ? 'visible' : ''}`} onClick={() => setSidebarOpen(false)} />

      <aside className={`sidebar ${sidebarOpen ? 'open' : ''}`}>
        <div className="sidebar-brand">
          <div className="sidebar-logo">
            {logoError ? (
              <span className="sidebar-logo-fallback">📦</span>
            ) : (
              <img src="/manncj.png" alt="CJ DARCL" className="sidebar-logo-image" onError={() => setLogoError(true)} />
            )}
          </div>
        </div>
        <nav className="sidebar-nav">
          <div className="sidebar-label">Navigation</div>
          {NAV_ITEMS.map(item => (
            <button key={item.key} className={`nav-item ${tab === item.key ? 'active' : ''}`} onClick={() => switchTab(item.key)}>
              <span className="nav-icon">{item.icon}</span>
              {item.label}
            </button>
          ))}
        </nav>
        {quality && (
          <div className="sidebar-footer">
            <div className="sidebar-quality">
              <QualityBadge score={quality.data_quality_score} />
              <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Data Quality</span>
            </div>
          </div>
        )}
      </aside>

      <div className="main-wrapper">
        <header className="header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <button className="mobile-menu-btn" onClick={() => setSidebarOpen(true)}>☰</button>
            <div className="header-left">
              <div className="header-page-title">{meta.title}</div>
              <div className="header-page-sub">{meta.sub}</div>
            </div>
          </div>
          <div className="header-actions">
            {quality && <QualityBadge score={quality.data_quality_score} />}
            <NotificationBell />
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.3rem 0.7rem', background: 'rgba(13,148,136,0.1)', border: '1px solid rgba(13,148,136,0.3)', borderRadius: '8px' }}>
              <span style={{ fontSize: '0.75rem', color: '#0D9488' }}>👤</span>
              <span style={{ fontSize: '0.78rem', fontWeight: 600, color: '#1e293b' }}>{user?.full_name || user?.username}</span>
              <span style={{ fontSize: '0.65rem', color: '#0D9488', fontWeight: 700, background: 'rgba(13,148,136,0.15)', padding: '1px 6px', borderRadius: '4px' }}>MANAGER</span>
            </div>
            <button className="btn btn-ghost" onClick={() => loadDashboard(filters)}>↻ Refresh</button>
            <button onClick={onLogout} style={{ padding: '0.35rem 0.85rem', background: 'transparent', border: '1px solid #334155', borderRadius: '6px', color: '#64748b', cursor: 'pointer', fontSize: '0.78rem', fontWeight: 600 }}>Sign Out</button>
          </div>
        </header>

        <main className="main-content">
          {tab === 'dashboard' && <DashboardView {...{ summary, revenueTrends, topRoutes, insights, loading, error, filters, setFilters, cnMatches }} onFilter={handleFilter} onClear={handleClear} onDrilldown={openDrilldown} />}
          {tab === 'analytics' && <AnalyticsView rootCause={rootCause} risk={risk} loading={loading} error={error} summary={summary} onDrilldown={openDrilldown} />}
          {tab === 'ai' && <AICopilotView />}
          {tab === 'upload' && <UploadView onUploadDone={() => { setRootCause(null); setRisk(null); loadDashboard(filters); setTab('dashboard'); }} />}
          {tab === 'history' && <HistoryView uploads={uploads} loading={loading} onRefresh={() => { setRootCause(null); setRisk(null); loadDashboard(filters); }} />}
        </main>
      </div>

      {drilldown && <DrilldownModal data={drilldown} type={drilldownType} onClose={() => { setDrilldown(null); setDrilldownType(null); }} />}
    </div>
  );
}


// ═══════════════════════════════════════════════════════════
// Quality Badge
// ═══════════════════════════════════════════════════════════
function QualityBadge({ score }) {
  const color = score >= 80 ? '#10b981' : score >= 50 ? '#f59e0b' : '#f43f5e';
  const label = score >= 80 ? 'Good' : score >= 50 ? 'Moderate' : 'Critical';
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: '0.4rem', padding: '0.3rem 0.7rem',
      background: `${color}18`, border: `1px solid ${color}35`, borderRadius: '999px'
    }}>
      <span style={{ fontSize: '0.82rem', fontWeight: 800, color }}>{score}%</span>
      <span style={{ fontSize: '0.65rem', fontWeight: 600, color, textTransform: 'uppercase', letterSpacing: '0.04em' }}>{label}</span>
    </div>
  );
}


// ═══════════════════════════════════════════════════════════
// Dashboard View
// ═══════════════════════════════════════════════════════════

// ═══════════════════════════════════════════════════════════
function DashboardView({ summary, revenueTrends, topRoutes, insights, loading, error, filters, setFilters, cnMatches, onFilter, onClear, onDrilldown }) {
  if (error) return <ErrorState msg={error} onRetry={onFilter} />;
  if (loading) return <Spinner text="Loading command center..." />;

  const hasFilters = Object.values(filters).some(v => v !== '');

  if (!summary || summary.total_shipments === 0) {
    if (hasFilters) {
      return (
        <>
          <Filters filters={filters} setFilters={setFilters} onFilter={onFilter} onClear={onClear} />
          <div className="empty-state" style={{ marginTop: '2rem' }}>
            <div className="empty-icon">🔍</div>
            <h2>No Matches Found</h2>
            <p style={{ color: 'var(--text-muted)' }}>No shipments match your current search criteria.</p>
            <button className="btn btn-primary" style={{ marginTop: '1rem' }} onClick={onClear}>Clear Filters</button>
          </div>
        </>
      );
    }
    return <EmptyState />;
  }

  const trendData = revenueTrends.map(i => ({
    date: i.period ? new Date(i.period).toLocaleDateString('en-IN', { month: 'short', day: 'numeric' }) : '',
    revenue: Number(i.total_revenue) || 0, shipments: i.shipment_count || 0,
  }));
  const routeData = topRoutes.map(r => ({
    name: `${r.route__origin} → ${r.route__destination}`, shipments: r.shipment_count,
    onTime: r.on_time_count, delayed: r.delayed_count, revenue: Number(r.total_revenue),
    delayPct: r.shipment_count > 0 ? Math.round((r.delayed_count / r.shipment_count) * 100) : 0,
  }));
  const pieData = [
    { name: 'On Time', value: summary.on_time_count, color: COLORS.emerald },
    { name: 'Delayed', value: summary.delayed_count, color: COLORS.rose },
  ];

  const onTimePct = summary.on_time_percentage;
  const perfStatus = onTimePct >= 90 ? 'good' : onTimePct >= 70 ? 'moderate' : 'critical';
  const perfLabel = onTimePct >= 90 ? '↗ good' : onTimePct >= 70 ? '→ moderate' : '↘ critical';

  return (
    <>
      <Filters filters={filters} setFilters={setFilters} onFilter={onFilter} onClear={onClear} />
      {filters.cnno && (
        <div className="chart-card" style={{ marginBottom: '1rem' }}>
          <div className="chart-header">
            <div>
              <div className="chart-title">🔎 CN Search Details</div>
              <div className="chart-subtitle">Showing matched shipment records for CN: {filters.cnno}</div>
            </div>
          </div>
          {cnMatches.length > 0 ? (
            <div className="history-table-wrap">
              <table className="history-table">
                <thead>
                  <tr>
                    <th>CN No.</th>
                    <th>Dispatch Date</th>
                    <th>Delivery Date</th>
                    <th>Route</th>
                    <th>Vehicle</th>
                    <th>Transporter</th>
                    <th>Status</th>
                    <th>Freight</th>
                  </tr>
                </thead>
                <tbody>
                  {cnMatches.map((s) => (
                    <tr key={s.id}>
                      <td style={{ fontWeight: 700, color: 'var(--text-primary)' }}>{s.shipment_id}</td>
                      <td>{s.dispatch_date || '-'}</td>
                      <td>{s.delivery_date || '-'}</td>
                      <td>{s.origin} → {s.destination}</td>
                      <td>{s.vehicle_no || s.vehicle_type || '-'}</td>
                      <td>{s.transporter_name || '-'}</td>
                      <td style={{ color: s.is_on_time ? COLORS.emerald : COLORS.rose, fontWeight: 600 }}>
                        {s.is_on_time ? 'On Time' : `Delayed ${s.delay_days || 0}d`}
                      </td>
                      <td>₹{Number(s.revenue || 0).toLocaleString('en-IN')}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>No shipment details found for this CN number.</div>
          )}
        </div>
      )}

      {/* KPI Cards */}
      <div className="kpi-grid">
        <div onClick={() => onDrilldown('all')} style={{ cursor: 'pointer' }}>
          <KpiCard icon="📦" label="Total Shipments" value={summary.total_shipments.toLocaleString()} color="blue"
            status={`${summary.total_shipments} records loaded`} statusType="neutral" />
        </div>
        <div onClick={() => onDrilldown('on_time')} style={{ cursor: 'pointer' }}>
          <KpiCard icon="✅" label="On-Time Rate" value={`${summary.on_time_percentage}%`}
            sub={`${summary.on_time_count} shipments`} color="emerald"
            status={perfLabel} statusType={perfStatus} />
        </div>
        <div onClick={() => onDrilldown('delayed')} style={{ cursor: 'pointer' }}>
          <KpiCard icon="⏱️" label="Delayed" value={summary.delayed_count.toLocaleString()}
            sub={`Avg ${summary.average_delay_days}d late`} color="rose"
            status={summary.delayed_count > 0 ? '↘ needs attention' : '✓ all clear'} statusType={summary.delayed_count > 0 ? 'critical' : 'good'} />
        </div>
        <div onClick={() => onDrilldown('penalty')} style={{ cursor: 'pointer' }}>
          <KpiCard icon="💰" label="Total Billed Freight" value={`₹${Number(summary.total_revenue).toLocaleString('en-IN', {maximumFractionDigits: 0})}`}
            sub={`Rev (2.5%): ₹${(Number(summary.total_revenue) * 0.025).toLocaleString('en-IN', {maximumFractionDigits: 0})}`} color="violet" />
        </div>
        {summary.total_distance > 0 && (
          <div style={{ cursor: 'default' }}>
            <KpiCard icon="📍" label="Distance Analyzed" value={`${summary.total_distance.toLocaleString('en-IN')} km`}
              sub="Total fleet transit scope" color="amber" />
          </div>
        )}
        {summary.pod_compliance > 0 && (
          <div style={{ cursor: 'default' }}>
            <KpiCard icon="📄" label="POD Compliance" value={`${summary.pod_compliance}%`}
              sub="Proof of Delivery completed" color="blue" />
          </div>
        )}
      </div>

      {/* Charts */}
      <div className="charts-grid">
        {/* Revenue Trend — Area Chart */}
        <div className="chart-card full-width">
          <div className="chart-header">
            <div>
              <div className="chart-title">📈 Billed Freight Trends</div>
              <div className="chart-subtitle">Daily freight billed & shipment volume over time</div>
            </div>
            <div className="chart-legend">
              <div className="legend-item"><div className="legend-dot" style={{ background: COLORS.blue }} />Freight Value</div>
              <div className="legend-item"><div className="legend-dot" style={{ background: COLORS.violet }} />Shipments</div>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={trendData}>
              <defs>
                <linearGradient id="gradRevenue" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={COLORS.blue} stopOpacity={0.3} />
                  <stop offset="95%" stopColor={COLORS.blue} stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="date" stroke="#6b7280" fontSize={11} tickLine={false} axisLine={false} />
              <YAxis stroke="#6b7280" fontSize={11} tickLine={false} axisLine={false}
                tickFormatter={v => `₹${(v / 1000).toFixed(0)}k`} />
              <Tooltip {...TOOLTIP_STYLE}
                formatter={(v, name) => [name === 'revenue' ? `₹${Number(v).toLocaleString('en-IN')}` : v, name === 'revenue' ? 'Freight' : 'Shipments']}
                labelStyle={{ color: '#9ca3af', fontSize: '0.75rem' }} />
              <Area type="monotone" dataKey="revenue" stroke={COLORS.blue} strokeWidth={2.5}
                fill="url(#gradRevenue)" dot={false} activeDot={{ r: 5, stroke: COLORS.blue, strokeWidth: 2, fill: '#0f1117' }} />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Top Routes — Horizontal Bar */}
        <div className="chart-card">
          <div className="chart-header">
            <div>
              <div className="chart-title">🛣️ Top Routes</div>
              <div className="chart-subtitle">By shipment volume (on-time vs delayed)</div>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={routeData.slice(0, 6)} layout="vertical" barCategoryGap="20%">
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis type="number" stroke="#6b7280" fontSize={11} tickLine={false} axisLine={false} />
              <YAxis type="category" dataKey="name" stroke="#6b7280" fontSize={10} width={120} tickLine={false} axisLine={false} />
              <Tooltip {...TOOLTIP_STYLE} />
              <Bar dataKey="onTime" stackId="a" fill={COLORS.emerald} name="On Time" radius={[0, 0, 0, 0]} />
              <Bar dataKey="delayed" stackId="a" fill={COLORS.rose} name="Delayed" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Delivery Performance — Donut */}
        <div className="chart-card">
          <div className="chart-header">
            <div>
              <div className="chart-title">🎯 Delivery Performance</div>
              <div className="chart-subtitle">On-time vs delayed ratio</div>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie data={pieData} cx="50%" cy="50%" innerRadius={70} outerRadius={100}
                dataKey="value" paddingAngle={4} stroke="none"
                label={({ name, value, percent }) => `${name}: ${value} (${(percent * 100).toFixed(0)}%)`}
                labelLine={{ stroke: '#6b7280', strokeWidth: 1 }}>
                {pieData.map((e, i) => <Cell key={i} fill={e.color} />)}
              </Pie>
              <Tooltip {...TOOLTIP_STYLE} />
              <Legend iconType="circle" wrapperStyle={{ fontSize: '0.82rem', color: '#9ca3af' }} />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Smart Insights */}
      {insights.length > 0 && (
        <div className="chart-card" style={{ marginBottom: '2rem' }}>
          <div className="chart-header">
            <div>
              <div className="chart-title">🧠 Smart Insights</div>
              <div className="chart-subtitle">Data-driven observations from your shipments</div>
            </div>
          </div>
          <ul className="insights-list">
            {insights.map((item, i) => (
              <li key={i} className="insight-item">
                <span className="insight-icon">{INSIGHT_ICONS[item.type] || '💡'}</span>
                <span>{typeof item === 'string' ? item : item.text}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </>
  );
}
// Analytics View
// ═══════════════════════════════════════════════════════════
function AnalyticsView({ rootCause, risk, loading, error, summary, onDrilldown }) {
  if (error) return <ErrorState msg={error} />;
  if (loading || !rootCause) return <Spinner text="Loading deep analytics..." />;

  const routeAnalysis = rootCause.by_route || [];
  const monthAnalysis = rootCause.by_month || [];
  const routeRisks = risk?.route_risks || [];

  const MONTH_NAMES = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const routeDelayData = routeAnalysis.slice(0, 8).map((r) => ({
    name: `${r.route__origin}→${r.route__destination}`.slice(0, 20),
    delayed: r.delayed,
    onTime: r.on_time,
    total: (r.delayed || 0) + (r.on_time || 0),
  }));
  const monthlyDelayData = monthAnalysis.map((m) => ({
    month: MONTH_NAMES[m.month] || m.month,
    total: m.total,
    delayed: m.delayed,
    delayPct: m.total > 0 ? Math.round((m.delayed / m.total) * 100) : 0,
  }));
  const isSmallRouteData = routeDelayData.length <= 2;
  const isSmallMonthData = monthlyDelayData.length <= 2;

  return (
    <div className="analytics-view fade-in">

      {/* 🧠 Predictive Logistics Intelligence Block */}
      {summary && (
        <div className="card" style={{ padding: '1.5rem', marginBottom: '1.5rem', background: 'linear-gradient(135deg, rgba(30,58,138,0.1), rgba(139,92,246,0.1))', border: '1px solid var(--border-glass)' }}>
          <h3 style={{ marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '1.1rem' }}>
            <span style={{ fontSize: '1.3rem' }}>🧠</span> Advanced Data Science Intel
          </h3>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '1.25rem' }}>Analyst-level macro overview measuring supply chain volatility, SLA leakage, and reliability probability.</p>
          <div className="kpi-grid">
            <KpiCard icon="📉" label="System Delay Volatility" value={`±${summary.delay_volatility} Days`} sub="Standard Deviation of Delivery Delays" color="violet" />
            <KpiCard icon="⚠️" label="Revenue at Risk" value={`₹${Number(summary.revenue_at_risk).toLocaleString('en-IN')}`} sub="Freight Value tied up in active SLA failures" color="rose" />
            <KpiCard icon="🎯" label="Transit Reliability Index" value={`${summary.on_time_percentage}%`} sub="Current Probability of On-Time SLA Adherence" color="emerald" />
          </div>
        </div>
      )}

      {/* Risk Summary */}
      {risk && (
        <div className="kpi-grid" style={{ marginBottom: '1.5rem' }}>
          <KpiCard icon="🔴" label="High Risk Routes" value={risk.high_risk_route_count} sub=">40% delay rate" color="rose"
            status="requires action" statusType="critical" />
          <KpiCard icon="🟡" label="Medium Risk" value={risk.medium_risk_route_count} sub=">20% delay rate" color="amber"
            status="monitor closely" statusType="moderate" />
          <KpiCard icon="🟢" label="Low Risk" value={risk.low_risk_route_count} sub="≤20% delay rate" color="emerald"
            status="performing well" statusType="good" />
        </div>
      )}

      <div className="charts-grid">
        {/* Route Risk Matrix */}
        <div className="chart-card full-width">
          <div className="chart-header">
            <div>
              <div className="chart-title">🎯 Route Risk Matrix</div>
              <div className="chart-subtitle">Delay rate, penalty impact, and shortage per route</div>
            </div>
            <div className="chart-legend">
              <div className="legend-item"><div className="legend-dot" style={{ background: RISK_COLORS.high }} />High Risk</div>
              <div className="legend-item"><div className="legend-dot" style={{ background: RISK_COLORS.medium }} />Medium</div>
              <div className="legend-item"><div className="legend-dot" style={{ background: RISK_COLORS.low }} />Low</div>
            </div>
          </div>
          <div className="history-table-wrap" style={{ maxHeight: '350px', overflowY: 'auto' }}>
            <table className="history-table">
              <thead>
                <tr>
                  <th>Route</th>
                  <th>Total</th>
                  <th>Delayed</th>
                  <th>Delay Rate</th>
                  {routeRisks.some(r => Number(r.total_penalty) > 0) && <th>Penalty</th>}
                  <th>Shortage</th>
                  <th>Risk</th>
                </tr>
              </thead>
              <tbody>
                {routeRisks.map((r, i) => (
                  <tr key={i}>
                    <td style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{r.route__origin} → {r.route__destination}</td>
                    <td>{r.total}</td>
                    <td style={{ color: r.delayed > 0 ? COLORS.rose : 'inherit', fontWeight: r.delayed > 0 ? 600 : 400 }}>{r.delayed}</td>
                    <td style={{ fontWeight: 600, color: RISK_COLORS[r.risk_level] }}>{r.delay_rate}%</td>
                    {routeRisks.some(rt => Number(rt.total_penalty) > 0) && (
                      <td>₹{Number(r.total_penalty).toLocaleString('en-IN')}</td>
                    )}
                    <td>{Number(r.total_shortage).toFixed(3)} MT</td>
                    <td><span className={`status-badge ${r.risk_level === 'high' ? 'failed' : r.risk_level === 'medium' ? 'partial' : 'completed'}`}>{r.risk_level}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Route Delay Breakdown */}
        <div className="chart-card">
          <div className="chart-header">
            <div>
              <div className="chart-title">📊 Route Delay Breakdown</div>
              <div className="chart-subtitle">
                {isSmallRouteData ? 'Compact view for low-volume filtered results' : 'On-time vs delayed per route'}
              </div>
            </div>
          </div>
          {isSmallRouteData ? (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={routeDelayData} barCategoryGap="35%">
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="name" stroke="#6b7280" fontSize={11} tickLine={false} axisLine={false} />
                <YAxis stroke="#6b7280" fontSize={11} allowDecimals={false} tickLine={false} axisLine={false} />
                <Tooltip {...TOOLTIP_STYLE} />
                <Legend iconType="circle" wrapperStyle={{ fontSize: '0.8rem', color: '#9ca3af' }} />
                <Bar dataKey="onTime" fill={COLORS.emerald} name="On Time" radius={[6, 6, 0, 0]} />
                <Bar dataKey="delayed" fill={COLORS.rose} name="Delayed" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={routeDelayData} layout="vertical" barCategoryGap="18%">
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis type="number" stroke="#6b7280" fontSize={11} tickLine={false} axisLine={false} />
                <YAxis type="category" dataKey="name" stroke="#6b7280" fontSize={9} width={120} tickLine={false} axisLine={false} />
                <Tooltip {...TOOLTIP_STYLE} />
                <Bar dataKey="onTime" stackId="a" fill={COLORS.emerald} name="On Time" />
                <Bar dataKey="delayed" stackId="a" fill={COLORS.rose} name="Delayed" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Monthly Pattern */}
        <div className="chart-card">
          <div className="chart-header">
            <div>
              <div className="chart-title">📅 Monthly Delay Pattern</div>
              <div className="chart-subtitle">
                {isSmallMonthData ? 'Smoothed trend view for low-volume filtered results' : 'Seasonal trends in delivery delays'}
              </div>
            </div>
          </div>
          {isSmallMonthData ? (
            <ResponsiveContainer width="100%" height={300}>
              <AreaChart data={monthlyDelayData}>
                <defs>
                  <linearGradient id="gradMonthlyDelayed" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={COLORS.rose} stopOpacity={0.3} />
                    <stop offset="95%" stopColor={COLORS.rose} stopOpacity={0.04} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="month" stroke="#6b7280" fontSize={12} tickLine={false} axisLine={false} />
                <YAxis stroke="#6b7280" fontSize={11} allowDecimals={false} tickLine={false} axisLine={false} />
                <Tooltip {...TOOLTIP_STYLE}
                  formatter={(v, name) => [v, name === 'delayed' ? 'Delayed' : 'Total Shipments']}
                  labelFormatter={(l) => `Month: ${l}`} />
                <Legend iconType="circle" wrapperStyle={{ fontSize: '0.8rem', color: '#9ca3af' }} />
                <Area type="monotone" dataKey="total" stroke={COLORS.blue} fill="transparent" strokeWidth={2} name="Total Shipments" />
                <Area type="monotone" dataKey="delayed" stroke={COLORS.rose} fill="url(#gradMonthlyDelayed)" strokeWidth={2} name="Delayed" />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={monthlyDelayData} barCategoryGap="25%">
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="month" stroke="#6b7280" fontSize={12} tickLine={false} axisLine={false} />
                <YAxis stroke="#6b7280" fontSize={11} tickLine={false} axisLine={false} />
                <Tooltip {...TOOLTIP_STYLE}
                  formatter={(v, name) => [v, name === 'Total' ? 'Total Shipments' : 'Delayed']}
                  labelFormatter={l => `Month: ${l}`} />
                <Bar dataKey="total" fill={COLORS.blue} name="Total" radius={[4, 4, 0, 0]}
                  label={{ position: 'top', fill: '#6b7280', fontSize: 10 }} />
                <Bar dataKey="delayed" fill={COLORS.rose} name="Delayed" radius={[4, 4, 0, 0]}
                  label={{ position: 'top', fill: '#f43f5e', fontSize: 10 }} />
                <Legend iconType="circle" wrapperStyle={{ fontSize: '0.8rem', color: '#9ca3af' }} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* Contractor Reliability Matrix */}
      {rootCause.by_contractor && rootCause.by_contractor.length > 0 && (
        <div className="chart-card" style={{ marginTop: '1.5rem' }}>
          <div className="chart-header">
            <div>
              <div className="chart-title">🚚 Contractor Reliability Matrix</div>
              <div className="chart-subtitle">Top High-Risk Transporters & Vendors</div>
            </div>
          </div>
          <div className="history-table-wrap">
            <table className="history-table">
              <thead>
                <tr>
                  <th>Contractor / Transporter</th>
                  <th>Total Shipments</th>
                  <th>Delayed</th>
                  <th>Avg Delay</th>
                  <th>Reliability</th>
                </tr>
              </thead>
              <tbody>
                {rootCause.by_contractor.map((c, i) => {
                  const onTime = c.total_shipments - c.delayed_count;
                  const reliability = c.total_shipments > 0 ? ((onTime / c.total_shipments) * 100).toFixed(1) : 0;
                  return (
                    <tr key={i}>
                      <td style={{ fontWeight: 600 }}>{c.transporter_name}</td>
                      <td>{c.total_shipments}</td>
                      <td style={{ color: c.delayed_count > 0 ? COLORS.rose : COLORS.emerald }}>{c.delayed_count}</td>
                      <td>{c.delayed_count > 0 && c.avg_delay ? `+${c.avg_delay.toFixed(1)}d` : '-'}</td>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          <div style={{ width: '60px', height: '6px', background: 'rgba(255,255,255,0.1)', borderRadius: '3px' }}>
                            <div style={{ height: '100%', width: `${reliability}%`, background: reliability > 85 ? COLORS.emerald : reliability > 60 ? COLORS.amber : COLORS.rose, borderRadius: '3px' }} />
                          </div>
                          <span style={{ fontSize: '0.8rem', color: reliability > 85 ? COLORS.emerald : reliability > 60 ? COLORS.amber : COLORS.rose }}>{reliability}%</span>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Shortage Summary */}
      {rootCause.shortages && rootCause.shortages.total_shortage_shipments > 0 && (
        <div className="chart-card">
          <div className="chart-header"><div><div className="chart-title">📉 Shortage Analysis</div><div className="chart-subtitle">Material shortage impact summary</div></div></div>
          <div style={{ display: 'flex', gap: '3rem', padding: '0.5rem 0', cursor: 'pointer' }} onClick={() => onDrilldown('shortage')}>
            <div>
              <span style={{ fontSize: '2rem', fontWeight: 800, color: COLORS.amber }}>{rootCause.shortages.total_shortage_shipments}</span>
              <div className="kpi-sub">Affected Shipments</div>
            </div>
            <div>
              <span style={{ fontSize: '2rem', fontWeight: 800, color: COLORS.amber }}>{rootCause.shortages.total_shortage_mt.toFixed(3)}</span>
              <div className="kpi-sub">Total Shortage (MT)</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}


// ═══════════════════════════════════════════════════════════
// AI Copilot View
// ═══════════════════════════════════════════════════════════
function AICopilotView() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  useEffect(scrollToBottom, [messages]);

  const SUGGESTIONS = [
    "What are the top issues in my logistics?",
    "Which routes need immediate attention?",
    "How can I reduce penalties?",
    "Analyze delivery performance trends",
    "What's causing the most delays?",
    "Give me optimization recommendations",
  ];

  const sendMessage = async (text) => {
    const q = text || input.trim();
    if (!q || loading) return;
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: q }]);
    setLoading(true);
    try {
      const res = await fetchAIAnalysis(q);
      setMessages(prev => [...prev, { role: 'assistant', content: res.analysis, model: res.model }]);
    } catch (e) {
      setMessages(prev => [...prev, { role: 'assistant', content: `⚠️ Error: ${e.message}` }]);
    }
    setLoading(false);
  };

  const handleKeyDown = (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); } };

  return (
    <div className="ai-container">
      <div className="ai-chat-box">
        <div className="ai-messages">
          {messages.length === 0 && (
            <div className="ai-welcome">
              <div className="ai-welcome-icon">🤖</div>
              <div className="ai-welcome-title">AI Logistics Copilot</div>
              <p style={{ color: 'var(--text-muted)', maxWidth: '500px', margin: '0 auto' }}>
                Ask me anything about your logistics data. I'm powered by Google Gemini and trained to analyze shipment patterns, identify risks, and suggest optimizations.
              </p>
              <div className="ai-suggestions">
                {SUGGESTIONS.map((s, i) => (
                  <button key={i} className="ai-suggestion-btn" onClick={() => sendMessage(s)}>{s}</button>
                ))}
              </div>
            </div>
          )}
          {messages.map((msg, i) => (
            <div key={i} className={`ai-message ${msg.role}`}>
              {msg.role === 'assistant' ? <FormattedAI text={msg.content} /> : msg.content}
            </div>
          ))}
          {loading && (
            <div className="ai-typing">
              <div className="ai-typing-dots"><span /><span /><span /></div>
              Gemini is analyzing your data...
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
        <div className="ai-input-bar">
          {messages.length > 0 && (
            <button className="btn btn-ghost" title="Start over / view suggestions" onClick={() => setMessages([])} disabled={loading} style={{ padding: '0.7rem 1rem' }}>
              🔄 New
            </button>
          )}
          <input className="ai-input" placeholder="Ask about your logistics data..." value={input}
            onChange={e => setInput(e.target.value)} onKeyDown={handleKeyDown} disabled={loading} />
          <button className="ai-send-btn" onClick={() => sendMessage()} disabled={loading || !input.trim()}>
            {loading ? '⏳' : '➤'} Send
          </button>
        </div>
      </div>
    </div>
  );
}

// Simple markdown-ish formatter for AI response
function FormattedAI({ text }) {
  if (!text) return null;
  const parseInline = (str) => {
    const parts = str.split(/(\*\*.*?\*\*)/g);
    return parts.map((part, idx) =>
      part.startsWith('**') && part.endsWith('**') ? <strong key={idx}>{part.slice(2, -2)}</strong> : part
    );
  };
  const lines = text.split('\n');
  return (
    <div style={{ lineHeight: '1.5' }}>
      {lines.map((line, i) => {
        if (line.startsWith('### ')) return <h3 key={i} style={{ marginTop: '1rem', marginBottom: '0.4rem', fontSize: '1.05rem', color: 'var(--text-primary)' }}>{parseInline(line.replace('### ', ''))}</h3>;
        if (line.startsWith('## ')) return <h2 key={i} style={{ marginTop: '1.2rem', marginBottom: '0.5rem', fontSize: '1.15rem', color: 'var(--text-primary)' }}>{parseInline(line.replace('## ', ''))}</h2>;
        if (line.startsWith('- ') || line.startsWith('* ')) return <div key={i} style={{ paddingLeft: '0.5rem', marginBottom: '0.3rem', display: 'flex' }}><span style={{ marginRight: '0.5rem', color: 'var(--accent-blue)' }}>•</span><span>{parseInline(line.replace(/^[-*]\s/, ''))}</span></div>;
        if (line.trim() === '') return <div key={i} style={{ height: '0.5rem' }} />;
        return <p key={i} style={{ marginBottom: '0.4rem' }}>{parseInline(line)}</p>;
      })}
    </div>
  );
}


// ═══════════════════════════════════════════════════════════
// Drilldown Modal
// ═══════════════════════════════════════════════════════════
function DrilldownModal({ data, type, onClose }) {
  const titles = { all: 'All Shipments', delayed: 'Delayed Shipments', on_time: 'On-Time Shipments', shortage: 'Shortage Shipments', penalty: 'Penalized Shipments' };
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()} style={{ maxWidth: '1400px', width: '95%' }}>
        <div className="modal-header">
          <h3 className="modal-title">{titles[type] || 'Shipments'} ({data.length})</h3>
          <button className="btn btn-ghost" onClick={onClose}>✕ Close</button>
        </div>
        <div className="history-table-wrap" style={{ maxHeight: '70vh', overflow: 'auto' }}>
          <table className="history-table">
            <thead>
              <tr>
                <th>CN No.</th>
                <th>Consignor</th>
                <th>Consignee</th>
                <th>Route</th>
                <th>Transporter</th>
                <th>Dispatch</th>
                <th>Expected</th>
                <th>Delivered</th>
                <th>Vehicle</th>
                {type === 'shortage' ? <th>Shortage</th> : <th>Delay</th>}
                <th>Freight Value</th>
              </tr>
            </thead>
            <tbody>
              {data.map((s, i) => (
                <tr key={i}>
                  <td style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{s.shipment_id}</td>
                  <td style={{ maxWidth: '150px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={s.consignor_name}>{s.consignor_name || '-'}</td>
                  <td style={{ maxWidth: '150px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={s.consignee_name}>{s.consignee_name || '-'}</td>
                  <td>{s.origin} → {s.destination}</td>
                  <td style={{ maxWidth: '150px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={s.transporter_name}>{s.transporter_name || '-'}</td>
                  <td>{s.dispatch_date}</td>
                  <td>{s.expected_delivery_date || '-'}</td>
                  <td>{s.delivery_date || '-'}</td>
                  <td>{s.vehicle_no || s.vehicle_type}</td>
                  {type === 'shortage' ? (
                    <td style={{ color: COLORS.amber, fontWeight: 600 }}>{s.shortage ? `${Number(s.shortage).toFixed(3)} MT` : '-'}</td>
                  ) : (
                    <td style={{ color: s.delay_days > 0 ? COLORS.rose : COLORS.emerald, fontWeight: 600 }}>{s.delay_days > 0 ? `+${s.delay_days}d` : 'On time'}</td>
                  )}
                  <td>₹{Number(s.revenue).toLocaleString('en-IN')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {data.length === 0 && <div className="empty-state" style={{ padding: '2rem' }}><p>No records found.</p></div>}
      </div>
    </div>
  );
}


// ═══════════════════════════════════════════════════════════
// Shared Components
// ═══════════════════════════════════════════════════════════

function KpiCard({ icon, label, value, sub, color, status, statusType }) {
  return (
    <div className={`kpi-card ${color}`}>
      <div className="kpi-header">
        <div className={`kpi-icon ${color}`}>{icon}</div>
        {status && <span className={`kpi-status ${statusType || ''}`}>{status}</span>}
      </div>
      <div className="kpi-label">{label}</div>
      <div className="kpi-value">{value}</div>
      {sub && <div className="kpi-sub">{sub}</div>}
    </div>
  );
}

function Filters({ filters, setFilters, onFilter, onClear }) {
  return (
    <div className="filters-bar">
      <div className="filter-group"><label className="filter-label">From</label><input type="date" className="filter-input" value={filters.date_from} onChange={e => setFilters({ ...filters, date_from: e.target.value })} /></div>
      <div className="filter-group"><label className="filter-label">To</label><input type="date" className="filter-input" value={filters.date_to} onChange={e => setFilters({ ...filters, date_to: e.target.value })} /></div>
      <div className="filter-group"><label className="filter-label">Origin</label><input type="text" className="filter-input" placeholder="e.g. Base" value={filters.origin} onChange={e => setFilters({ ...filters, origin: e.target.value })} /></div>
      <div className="filter-group"><label className="filter-label">Destination</label><input type="text" className="filter-input" placeholder="e.g. Jamshedpur" value={filters.destination} onChange={e => setFilters({ ...filters, destination: e.target.value })} /></div>
      <div className="filter-group"><label className="filter-label">CN No.</label><input type="text" className="filter-input" placeholder="e.g. JMS123..." value={filters.cnno} onChange={e => setFilters({ ...filters, cnno: e.target.value })} /></div>
      <div className="filter-group"><label className="filter-label">Material</label><input type="text" className="filter-input" placeholder="e.g. sheet" value={filters.material} onChange={e => setFilters({ ...filters, material: e.target.value })} /></div>
      <div className="filter-group"><label className="filter-label">Transporter</label><input type="text" className="filter-input" placeholder="e.g. Transport Co" value={filters.transporter_name} onChange={e => setFilters({ ...filters, transporter_name: e.target.value })} /></div>
      <div className="filter-group"><label className="filter-label">Region</label><input type="text" className="filter-input" placeholder="e.g. North" value={filters.booking_region} onChange={e => setFilters({ ...filters, booking_region: e.target.value })} /></div>
      <button className="btn btn-primary" onClick={onFilter}>Apply</button>
      <button className="btn btn-ghost" onClick={onClear}>Clear</button>
    </div>
  );
}

function ErrorState({ msg, onRetry }) {
  return <div className="empty-state"><div className="empty-state-icon">⚠️</div><div className="empty-state-title">Error</div><p>{msg}</p>{onRetry && <button className="btn btn-primary" style={{ marginTop: '1rem' }} onClick={onRetry}>Retry</button>}</div>;
}

function EmptyState() {
  return <div className="empty-state"><div className="empty-state-icon">📦</div><div className="empty-state-title">No Data Yet</div><p>Upload an Excel or CSV file to get started with your logistics intelligence.</p></div>;
}

function Spinner({ text }) {
  return <div className="loading-container"><div className="spinner" /><div className="loading-text">{text}</div></div>;
}


// ═══════════════════════════════════════════════════════════
// Upload View
// ═══════════════════════════════════════════════════════════
function UploadView({ onUploadDone }) {
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const handleFile = async (file) => {
    if (!file) return; setUploading(true); setResult(null); setError(null);
    try { const res = await uploadFile(file); setResult(res); setTimeout(() => onUploadDone(), 2500); }
    catch (e) { setError(e.message); }
    finally { setUploading(false); }
  };

  return (
    <div className="upload-container">
      <div className={`upload-zone ${dragOver ? 'drag-over' : ''} ${uploading ? 'uploading' : ''}`}
        onDragOver={e => { e.preventDefault(); setDragOver(true); }} onDragLeave={() => setDragOver(false)}
        onDrop={e => { e.preventDefault(); setDragOver(false); handleFile(e.dataTransfer.files[0]); }}
        onClick={() => document.getElementById('file-input').click()}>
        <div className="upload-icon">{uploading ? '⏳' : '📁'}</div>
        <div className="upload-title">{uploading ? 'Processing your data...' : 'Drop your Excel/CSV file here'}</div>
        <div className="upload-subtitle">Supports .xlsx, .xls, .csv (max 10MB)</div>
        {uploading && <div className="progress-bar-container"><div className="progress-bar-fill" style={{ width: '80%' }} /></div>}
        <input id="file-input" className="upload-input" type="file" accept=".xlsx,.xls,.csv" onChange={e => handleFile(e.target.files[0])} />
      </div>

      {result && (
        <div className="upload-result success">
          <div className="upload-result-title">✅ {result.message}</div>
          <div className="upload-stats">
            <div className="upload-stat"><div className="upload-stat-value">{result.processed_rows}</div><div className="upload-stat-label">Processed</div></div>
            <div className="upload-stat"><div className="upload-stat-value" style={{ color: result.error_rows > 0 ? '#f59e0b' : '#10b981' }}>{result.error_rows}</div><div className="upload-stat-label">Errors</div></div>
            <div className="upload-stat"><div className="upload-stat-value">{result.duplicates_removed || 0}</div><div className="upload-stat-label">Duplicates</div></div>
            <div className="upload-stat"><div className="upload-stat-value">{result.processing_time}</div><div className="upload-stat-label">Time</div></div>
          </div>
          {result.data_quality_score != null && (
            <div style={{ marginTop: '1rem', padding: '1rem', background: 'var(--bg-glass)', borderRadius: 'var(--radius-sm)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem' }}>
                <span style={{ fontWeight: 600 }}>Data Quality Score:</span>
                <QualityBadge score={result.data_quality_score} />
              </div>
              {result.quality_issues?.length > 0 && (
                <ul style={{ paddingLeft: '1.25rem', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                  {result.quality_issues.map((issue, i) => <li key={i} style={{ marginBottom: '0.3rem' }}>{issue}</li>)}
                </ul>
              )}
            </div>
          )}
        </div>
      )}
      {error && <div className="upload-result error"><div className="upload-result-title">❌ Upload Failed</div><p style={{ color: '#f87171' }}>{error}</p></div>}
    </div>
  );
}


// ═══════════════════════════════════════════════════════════
// History View
// ═══════════════════════════════════════════════════════════
function HistoryView({ uploads, loading, onRefresh }) {
  const [deleting, setDeleting] = useState(null);

  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to delete this upload? This will also remove all associated shipment records and cannot be undone.')) return;
    setDeleting(id);
    try {
      await deleteUpload(id);
      onRefresh();
    } catch (e) {
      alert(`Failed to delete: ${e.message}`);
    } finally {
      setDeleting(null);
    }
  };

  if (loading && !deleting) return <Spinner text="Loading upload history..." />;
  if (!uploads?.length) return <div className="empty-state"><div className="empty-state-icon">📋</div><div className="empty-state-title">No Uploads Yet</div><p>Upload your first shipment file to see history here.</p></div>;

  return (
    <div className="history-table-wrap">
      <table className="history-table">
        <thead><tr><th>File</th><th>Status</th><th>Rows</th><th>Processed</th><th>Errors</th><th>Dups</th><th>Quality</th><th>Date</th><th>Action</th></tr></thead>
        <tbody>
          {uploads.map(u => (
            <tr key={u.id}>
              <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{u.file_name}</td>
              <td><span className={`status-badge ${u.status}`}>{u.status}</span></td>
              <td>{u.total_rows}</td><td>{u.processed_rows}</td>
              <td style={{ color: u.error_rows > 0 ? '#f59e0b' : 'inherit', fontWeight: u.error_rows > 0 ? 600 : 400 }}>{u.error_rows}</td>
              <td>{u.duplicate_rows || 0}</td>
              <td>{u.data_quality_score != null ? <QualityBadge score={u.data_quality_score} /> : '-'}</td>
              <td>{new Date(u.uploaded_at).toLocaleString('en-IN')}</td>
              <td>
                <button className="btn btn-ghost" title="Delete Upload" style={{ padding: '0.4rem 0.6rem', fontSize: '1.1rem' }} onClick={() => handleDelete(u.id)} disabled={deleting === u.id}>
                  {deleting === u.id ? '⏳' : '🗑️'}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
