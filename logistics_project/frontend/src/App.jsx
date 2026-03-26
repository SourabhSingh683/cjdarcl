import { useState, useEffect, useCallback, useRef } from 'react';
import './index.css';
import {
  fetchSummary, fetchRevenueTrends, fetchTopRoutes, fetchSmartInsights,
  fetchUploadHistory, fetchRootCause, fetchRisk, fetchComparison,
  fetchQuality, fetchDrilldown, uploadFile, fetchAIAnalysis,
} from './api';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  LineChart, Line, AreaChart, Area, PieChart, Pie, Cell, Legend,
} from 'recharts';

// ─── Constants ─────────────────────────────────────────
const COLORS = {
  blue: '#3b82f6', emerald: '#10b981', rose: '#f43f5e',
  amber: '#f59e0b', violet: '#8b5cf6', cyan: '#06b6d4',
};

const TOOLTIP_STYLE = {
  contentStyle: {
    background: 'rgba(15, 17, 23, 0.95)', border: '1px solid rgba(255,255,255,0.1)',
    borderRadius: '10px', color: '#f1f3f9', fontSize: '0.82rem', padding: '0.75rem 1rem',
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
// APP
// ═══════════════════════════════════════════════════════════
export default function App() {
  const [tab, setTab] = useState('dashboard');
  const [summary, setSummary] = useState(null);
  const [revenueTrends, setRevenueTrends] = useState([]);
  const [topRoutes, setTopRoutes] = useState([]);
  const [insights, setInsights] = useState([]);
  const [uploads, setUploads] = useState([]);
  const [rootCause, setRootCause] = useState(null);
  const [risk, setRisk] = useState(null);
  const [comparison, setComparison] = useState(null);
  const [quality, setQuality] = useState(null);
  const [drilldown, setDrilldown] = useState(null);
  const [drilldownType, setDrilldownType] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [filters, setFilters] = useState({ date_from:'', date_to:'', origin:'', destination:'', vehicle_type:'' });
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const loadDashboard = useCallback(async (f) => {
    setLoading(true); setError(null);
    try {
      const [s, t, r, i, u, c, q] = await Promise.all([
        fetchSummary(f), fetchRevenueTrends({...f, group_by:'day'}),
        fetchTopRoutes(f), fetchSmartInsights(f), fetchUploadHistory(),
        fetchComparison(f), fetchQuality(),
      ]);
      setSummary(s); setRevenueTrends(t); setTopRoutes(r);
      setInsights(i.insights||[]); setUploads(u.results||[]);
      setComparison(c); setQuality(q);
    } catch(e) { setError(e.message); }
    finally { setLoading(false); }
  }, []);

  const loadAnalytics = useCallback(async (f) => {
    setLoading(true); setError(null);
    try {
      const [rc, rk] = await Promise.all([fetchRootCause(f), fetchRisk(f)]);
      setRootCause(rc); setRisk(rk);
    } catch(e) { setError(e.message); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { loadDashboard(filters); }, []);
  useEffect(() => {
    if (tab === 'analytics' && !rootCause) loadAnalytics(filters);
  }, [tab]);

  const handleFilter = () => { loadDashboard(filters); if(rootCause) loadAnalytics(filters); };
  const handleClear = () => {
    const e = {date_from:'',date_to:'',origin:'',destination:'',vehicle_type:''};
    setFilters(e); loadDashboard(e);
  };

  const openDrilldown = async (type) => {
    setDrilldownType(type);
    try {
      const res = await fetchDrilldown({ ...filters, filter: type });
      setDrilldown(res.results || []);
    } catch { setDrilldown([]); }
  };

  const switchTab = (t) => { setTab(t); setSidebarOpen(false); };
  const meta = PAGE_META[tab] || PAGE_META.dashboard;

  return (
    <div className="app">
      {/* Sidebar overlay for mobile */}
      <div className={`sidebar-overlay ${sidebarOpen?'visible':''}`} onClick={()=>setSidebarOpen(false)} />

      {/* Sidebar */}
      <aside className={`sidebar ${sidebarOpen?'open':''}`}>
        <div className="sidebar-brand">
          <div className="sidebar-logo">📦</div>
          <div>
            <div className="sidebar-title">CJ DARCL</div>
            <div className="sidebar-subtitle">Intelligence System</div>
          </div>
        </div>
        <nav className="sidebar-nav">
          <div className="sidebar-label">Navigation</div>
          {NAV_ITEMS.map(item => (
            <button key={item.key} className={`nav-item ${tab===item.key?'active':''}`} onClick={()=>switchTab(item.key)}>
              <span className="nav-icon">{item.icon}</span>
              {item.label}
            </button>
          ))}
        </nav>
        {quality && (
          <div className="sidebar-footer">
            <div className="sidebar-quality">
              <QualityBadge score={quality.data_quality_score} />
              <span style={{fontSize:'0.72rem',color:'var(--text-muted)'}}>Data Quality</span>
            </div>
          </div>
        )}
      </aside>

      {/* Main */}
      <div className="main-wrapper">
        <header className="header">
          <div style={{display:'flex',alignItems:'center',gap:'1rem'}}>
            <button className="mobile-menu-btn" onClick={()=>setSidebarOpen(true)}>☰</button>
            <div className="header-left">
              <div className="header-page-title">{meta.title}</div>
              <div className="header-page-sub">{meta.sub}</div>
            </div>
          </div>
          <div className="header-actions">
            {quality && <QualityBadge score={quality.data_quality_score} />}
            <button className="btn btn-ghost" onClick={()=>loadDashboard(filters)}>↻ Refresh</button>
          </div>
        </header>

        <main className="main-content">
          {tab==='dashboard' && <DashboardView {...{summary,revenueTrends,topRoutes,insights,comparison,loading,error,filters,setFilters}} onFilter={handleFilter} onClear={handleClear} onDrilldown={openDrilldown} />}
          {tab==='analytics' && <AnalyticsView rootCause={rootCause} risk={risk} loading={loading} error={error} />}
          {tab==='ai' && <AICopilotView />}
          {tab==='upload' && <UploadView onUploadDone={()=>{loadDashboard(filters);setTab('dashboard');}} />}
          {tab==='history' && <HistoryView uploads={uploads} loading={loading} />}
        </main>
      </div>

      {drilldown && <DrilldownModal data={drilldown} type={drilldownType} onClose={()=>{setDrilldown(null);setDrilldownType(null);}} />}
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
    <div style={{display:'flex',alignItems:'center',gap:'0.4rem',padding:'0.3rem 0.7rem',
      background:`${color}18`,border:`1px solid ${color}35`,borderRadius:'999px'}}>
      <span style={{fontSize:'0.82rem',fontWeight:800,color}}>{score}%</span>
      <span style={{fontSize:'0.65rem',fontWeight:600,color,textTransform:'uppercase',letterSpacing:'0.04em'}}>{label}</span>
    </div>
  );
}


// ═══════════════════════════════════════════════════════════
// Dashboard View
// ═══════════════════════════════════════════════════════════
function DashboardView({ summary,revenueTrends,topRoutes,insights,comparison,loading,error,filters,setFilters,onFilter,onClear,onDrilldown }) {
  if (error) return <ErrorState msg={error} onRetry={onFilter} />;
  if (loading) return <Spinner text="Loading command center..." />;
  if (!summary || summary.total_shipments===0) return <EmptyState />;

  const trendData = revenueTrends.map(i=>({
    date: i.period ? new Date(i.period).toLocaleDateString('en-IN',{month:'short',day:'numeric'}) : '',
    revenue: Number(i.total_revenue)||0, shipments: i.shipment_count||0,
  }));
  const routeData = topRoutes.map(r=>({
    name:`${r.route__origin} → ${r.route__destination}`, shipments:r.shipment_count,
    onTime:r.on_time_count, delayed:r.delayed_count, revenue:Number(r.total_revenue),
    delayPct: r.shipment_count > 0 ? Math.round((r.delayed_count/r.shipment_count)*100) : 0,
  }));
  const pieData = [
    {name:'On Time',value:summary.on_time_count,color:COLORS.emerald},
    {name:'Delayed',value:summary.delayed_count,color:COLORS.rose},
  ];

  const onTimePct = summary.on_time_percentage;
  const perfStatus = onTimePct >= 90 ? 'good' : onTimePct >= 70 ? 'moderate' : 'critical';
  const perfLabel = onTimePct >= 90 ? '↗ good' : onTimePct >= 70 ? '→ moderate' : '↘ critical';

  return (
    <>
      <Filters filters={filters} setFilters={setFilters} onFilter={onFilter} onClear={onClear} />

      {/* Period Comparison */}
      {comparison && comparison.recent && comparison.prior && (
        <div className="kpi-grid" style={{marginBottom:'0.75rem'}}>
          {[
            ['Shipments',comparison.recent.total_shipments,comparison.changes.total_shipments],
            ['On-Time %',`${comparison.recent.on_time_pct}%`,comparison.changes.on_time_pct],
            ['Penalties',`₹${comparison.recent.total_penalty.toLocaleString('en-IN')}`,comparison.changes.total_penalty],
          ].map(([label,val,change])=>(
            <div key={label} className="kpi-card blue" style={{padding:'1rem'}}>
              <div className="kpi-label" style={{fontSize:'0.62rem'}}>vs Last {comparison.period_days}d</div>
              <div style={{display:'flex',alignItems:'baseline',gap:'0.5rem'}}>
                <span style={{fontSize:'1.2rem',fontWeight:700}}>{val}</span>
                {change != null && <ChangeArrow value={change} />}
              </div>
              <div className="kpi-sub">{label}</div>
            </div>
          ))}
        </div>
      )}

      {/* KPI Cards */}
      <div className="kpi-grid">
        <div onClick={()=>onDrilldown('all')} style={{cursor:'pointer'}}>
          <KpiCard icon="📦" label="Total Shipments" value={summary.total_shipments.toLocaleString()} color="blue"
            status={`${summary.total_shipments} records loaded`} statusType="neutral" />
        </div>
        <div onClick={()=>onDrilldown('on_time')} style={{cursor:'pointer'}}>
          <KpiCard icon="✅" label="On-Time Rate" value={`${summary.on_time_percentage}%`}
            sub={`${summary.on_time_count} shipments`} color="emerald"
            status={perfLabel} statusType={perfStatus} />
        </div>
        <div onClick={()=>onDrilldown('delayed')} style={{cursor:'pointer'}}>
          <KpiCard icon="⏱️" label="Delayed" value={summary.delayed_count.toLocaleString()}
            sub={`Avg ${summary.average_delay_days}d late`} color="rose"
            status={summary.delayed_count > 0 ? '↘ needs attention' : '✓ all clear'} statusType={summary.delayed_count > 0 ? 'critical' : 'good'} />
        </div>
        <div onClick={()=>onDrilldown('penalty')} style={{cursor:'pointer'}}>
          <KpiCard icon="💰" label="Total Revenue" value={`₹${Number(summary.total_revenue).toLocaleString('en-IN')}`}
            sub={`Avg ₹${Number(summary.average_revenue).toLocaleString('en-IN')}`} color="violet" />
        </div>
      </div>

      {/* Charts */}
      <div className="charts-grid">
        {/* Revenue Trend — Area Chart */}
        <div className="chart-card full-width">
          <div className="chart-header">
            <div>
              <div className="chart-title">📈 Revenue Trends</div>
              <div className="chart-subtitle">Daily revenue & shipment volume over time</div>
            </div>
            <div className="chart-legend">
              <div className="legend-item"><div className="legend-dot" style={{background:COLORS.blue}} />Revenue</div>
              <div className="legend-item"><div className="legend-dot" style={{background:COLORS.violet}} />Shipments</div>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={trendData}>
              <defs>
                <linearGradient id="gradRevenue" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={COLORS.blue} stopOpacity={0.3}/>
                  <stop offset="95%" stopColor={COLORS.blue} stopOpacity={0.02}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="date" stroke="#6b7280" fontSize={11} tickLine={false} axisLine={false} />
              <YAxis stroke="#6b7280" fontSize={11} tickLine={false} axisLine={false}
                tickFormatter={v=>`₹${(v/1000).toFixed(0)}k`} />
              <Tooltip {...TOOLTIP_STYLE}
                formatter={(v,name)=>[name==='revenue'?`₹${Number(v).toLocaleString('en-IN')}`:v, name==='revenue'?'Revenue':'Shipments']}
                labelStyle={{color:'#9ca3af',fontSize:'0.75rem'}} />
              <Area type="monotone" dataKey="revenue" stroke={COLORS.blue} strokeWidth={2.5}
                fill="url(#gradRevenue)" dot={false} activeDot={{r:5,stroke:COLORS.blue,strokeWidth:2,fill:'#0f1117'}} />
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
            <BarChart data={routeData.slice(0,6)} layout="vertical" barCategoryGap="20%">
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis type="number" stroke="#6b7280" fontSize={11} tickLine={false} axisLine={false} />
              <YAxis type="category" dataKey="name" stroke="#6b7280" fontSize={10} width={120} tickLine={false} axisLine={false} />
              <Tooltip {...TOOLTIP_STYLE} />
              <Bar dataKey="onTime" stackId="a" fill={COLORS.emerald} name="On Time" radius={[0,0,0,0]} />
              <Bar dataKey="delayed" stackId="a" fill={COLORS.rose} name="Delayed" radius={[0,4,4,0]} />
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
                label={({name,value,percent})=>`${name}: ${value} (${(percent*100).toFixed(0)}%)`}
                labelLine={{stroke:'#6b7280',strokeWidth:1}}>
                {pieData.map((e,i)=><Cell key={i} fill={e.color} />)}
              </Pie>
              <Tooltip {...TOOLTIP_STYLE} />
              <Legend iconType="circle" wrapperStyle={{fontSize:'0.82rem',color:'#9ca3af'}} />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Smart Insights */}
      {insights.length > 0 && (
        <div className="chart-card" style={{marginBottom:'2rem'}}>
          <div className="chart-header">
            <div>
              <div className="chart-title">🧠 Smart Insights</div>
              <div className="chart-subtitle">Data-driven observations from your shipments</div>
            </div>
          </div>
          <ul className="insights-list">
            {insights.map((item,i)=>(
              <li key={i} className="insight-item">
                <span className="insight-icon">{INSIGHT_ICONS[item.type]||'💡'}</span>
                <span>{typeof item==='string'?item:item.text}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </>
  );
}


// ═══════════════════════════════════════════════════════════
// Analytics View
// ═══════════════════════════════════════════════════════════
function AnalyticsView({ rootCause, risk, loading, error }) {
  if (error) return <ErrorState msg={error} />;
  if (loading || !rootCause) return <Spinner text="Loading deep analytics..." />;

  const routeAnalysis = rootCause.by_route || [];
  const monthAnalysis = rootCause.by_month || [];
  const routeRisks = risk?.route_risks || [];

  const MONTH_NAMES = ['','Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];

  return (
    <>
      {/* Risk Summary */}
      {risk && (
        <div className="kpi-grid" style={{marginBottom:'1.5rem'}}>
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
              <div className="legend-item"><div className="legend-dot" style={{background:RISK_COLORS.high}}/>High Risk</div>
              <div className="legend-item"><div className="legend-dot" style={{background:RISK_COLORS.medium}}/>Medium</div>
              <div className="legend-item"><div className="legend-dot" style={{background:RISK_COLORS.low}}/>Low</div>
            </div>
          </div>
          <div className="history-table-wrap" style={{maxHeight:'350px',overflowY:'auto'}}>
            <table className="history-table">
              <thead><tr><th>Route</th><th>Total</th><th>Delayed</th><th>Delay Rate</th><th>Penalty</th><th>Shortage</th><th>Risk</th></tr></thead>
              <tbody>
                {routeRisks.map((r,i)=>(
                  <tr key={i}>
                    <td style={{color:'#f1f3f9',fontWeight:500}}>{r.route__origin} → {r.route__destination}</td>
                    <td>{r.total}</td>
                    <td style={{color:r.delayed>0?COLORS.rose:'inherit',fontWeight:r.delayed>0?600:400}}>{r.delayed}</td>
                    <td style={{fontWeight:600,color:RISK_COLORS[r.risk_level]}}>{r.delay_rate}%</td>
                    <td>₹{Number(r.total_penalty).toLocaleString('en-IN')}</td>
                    <td>{Number(r.total_shortage).toFixed(3)} MT</td>
                    <td><span className={`status-badge ${r.risk_level==='high'?'failed':r.risk_level==='medium'?'partial':'completed'}`}>{r.risk_level}</span></td>
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
              <div className="chart-subtitle">On-time vs delayed per route</div>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={routeAnalysis.slice(0,8).map(r=>({
              name:`${r.route__origin}→${r.route__destination}`.slice(0,20),
              delayed:r.delayed, onTime:r.on_time,
            }))} layout="vertical" barCategoryGap="18%">
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis type="number" stroke="#6b7280" fontSize={11} tickLine={false} axisLine={false} />
              <YAxis type="category" dataKey="name" stroke="#6b7280" fontSize={9} width={120} tickLine={false} axisLine={false} />
              <Tooltip {...TOOLTIP_STYLE} />
              <Bar dataKey="onTime" stackId="a" fill={COLORS.emerald} name="On Time" />
              <Bar dataKey="delayed" stackId="a" fill={COLORS.rose} name="Delayed" radius={[0,4,4,0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Monthly Pattern */}
        <div className="chart-card">
          <div className="chart-header">
            <div>
              <div className="chart-title">📅 Monthly Delay Pattern</div>
              <div className="chart-subtitle">Seasonal trends in delivery delays</div>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={monthAnalysis.map(m=>({
              month: MONTH_NAMES[m.month]||m.month,
              total:m.total, delayed:m.delayed,
              delayPct: m.total>0 ? Math.round((m.delayed/m.total)*100) : 0,
            }))} barCategoryGap="25%">
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="month" stroke="#6b7280" fontSize={12} tickLine={false} axisLine={false} />
              <YAxis stroke="#6b7280" fontSize={11} tickLine={false} axisLine={false} />
              <Tooltip {...TOOLTIP_STYLE}
                formatter={(v,name)=>[v, name==='total'?'Total Shipments':'Delayed']}
                labelFormatter={l=>`Month: ${l}`} />
              <Bar dataKey="total" fill={COLORS.blue} name="Total" radius={[4,4,0,0]}
                label={{position:'top',fill:'#6b7280',fontSize:10}} />
              <Bar dataKey="delayed" fill={COLORS.rose} name="Delayed" radius={[4,4,0,0]}
                label={{position:'top',fill:'#f43f5e',fontSize:10}} />
              <Legend iconType="circle" wrapperStyle={{fontSize:'0.8rem',color:'#9ca3af'}} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Shortage Summary */}
      {rootCause.shortages && rootCause.shortages.total_shortage_shipments > 0 && (
        <div className="chart-card">
          <div className="chart-header"><div><div className="chart-title">📉 Shortage Analysis</div><div className="chart-subtitle">Material shortage impact summary</div></div></div>
          <div style={{display:'flex',gap:'3rem',padding:'0.5rem 0'}}>
            <div>
              <span style={{fontSize:'2rem',fontWeight:800,color:COLORS.amber}}>{rootCause.shortages.total_shortage_shipments}</span>
              <div className="kpi-sub">Affected Shipments</div>
            </div>
            <div>
              <span style={{fontSize:'2rem',fontWeight:800,color:COLORS.amber}}>{rootCause.shortages.total_shortage_mt.toFixed(3)}</span>
              <div className="kpi-sub">Total Shortage (MT)</div>
            </div>
          </div>
        </div>
      )}
    </>
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

  const scrollToBottom = () => messagesEndRef.current?.scrollIntoView({behavior:'smooth'});
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

  const handleKeyDown = (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }};

  return (
    <div className="ai-container">
      <div className="ai-chat-box">
        <div className="ai-messages">
          {messages.length === 0 && (
            <div className="ai-welcome">
              <div className="ai-welcome-icon">🤖</div>
              <div className="ai-welcome-title">AI Logistics Copilot</div>
              <p style={{color:'var(--text-muted)',maxWidth:'500px',margin:'0 auto'}}>
                Ask me anything about your logistics data. I'm powered by Google Gemini and trained to analyze shipment patterns, identify risks, and suggest optimizations.
              </p>
              <div className="ai-suggestions">
                {SUGGESTIONS.map((s,i) => (
                  <button key={i} className="ai-suggestion-btn" onClick={()=>sendMessage(s)}>{s}</button>
                ))}
              </div>
            </div>
          )}
          {messages.map((msg,i) => (
            <div key={i} className={`ai-message ${msg.role}`}>
              {msg.role === 'assistant' ? <FormattedAI text={msg.content} /> : msg.content}
            </div>
          ))}
          {loading && (
            <div className="ai-typing">
              <div className="ai-typing-dots"><span/><span/><span/></div>
              Gemini is analyzing your data...
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
        <div className="ai-input-bar">
          <input className="ai-input" placeholder="Ask about your logistics data..." value={input}
            onChange={e=>setInput(e.target.value)} onKeyDown={handleKeyDown} disabled={loading} />
          <button className="ai-send-btn" onClick={()=>sendMessage()} disabled={loading || !input.trim()}>
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
  const lines = text.split('\n');
  return (
    <div>
      {lines.map((line, i) => {
        if (line.startsWith('## ')) return <h2 key={i}>{line.replace('## ','')}</h2>;
        if (line.startsWith('**') && line.endsWith('**')) return <p key={i}><strong>{line.replace(/\*\*/g,'')}</strong></p>;
        if (line.startsWith('- ') || line.startsWith('* ')) return <div key={i} style={{paddingLeft:'1rem',marginBottom:'0.25rem'}}>• {line.replace(/^[-*]\s/,'')}</div>;
        if (line.trim() === '') return <br key={i} />;
        return <p key={i} style={{marginBottom:'0.3rem'}}>{line}</p>;
      })}
    </div>
  );
}


// ═══════════════════════════════════════════════════════════
// Drilldown Modal
// ═══════════════════════════════════════════════════════════
function DrilldownModal({ data, type, onClose }) {
  const titles = { all:'All Shipments', delayed:'Delayed Shipments', on_time:'On-Time Shipments', shortage:'Shortage Shipments', penalty:'Penalized Shipments' };
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-content" onClick={e=>e.stopPropagation()}>
        <div className="modal-header">
          <h3 className="modal-title">{titles[type]||'Shipments'}</h3>
          <button className="btn btn-ghost" onClick={onClose}>✕ Close</button>
        </div>
        <div className="history-table-wrap">
          <table className="history-table">
            <thead><tr><th>Shipment ID</th><th>Route</th><th>Date</th><th>Vehicle</th><th>Delay</th><th>Penalty</th><th>Shortage</th><th>Revenue</th></tr></thead>
            <tbody>
              {data.map((s,i)=>(
                <tr key={i}>
                  <td style={{color:'#f1f3f9',fontWeight:500}}>{s.shipment_id}</td>
                  <td>{s.origin} → {s.destination}</td>
                  <td>{s.dispatch_date}</td>
                  <td>{s.vehicle_no || s.vehicle_type}</td>
                  <td style={{color:s.delay_days>0?COLORS.rose:COLORS.emerald,fontWeight:600}}>{s.delay_days>0?`+${s.delay_days}d`:'On time'}</td>
                  <td>{Number(s.penalty)>0?`₹${Number(s.penalty).toLocaleString('en-IN')}`:'-'}</td>
                  <td>{Number(s.shortage)>0?`${Number(s.shortage).toFixed(3)} MT`:'-'}</td>
                  <td>₹{Number(s.revenue).toLocaleString('en-IN')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {data.length===0 && <div className="empty-state" style={{padding:'2rem'}}><p>No records found.</p></div>}
      </div>
    </div>
  );
}


// ═══════════════════════════════════════════════════════════
// Shared Components
// ═══════════════════════════════════════════════════════════
function ChangeArrow({ value }) {
  if (value == null) return null;
  const isPositive = value >= 0;
  const color = isPositive ? '#10b981' : '#f43f5e';
  return (
    <span className={`kpi-trend ${isPositive?'up':'down'}`}>
      {isPositive?'▲':'▼'} {Math.abs(value)}%
    </span>
  );
}

function KpiCard({ icon, label, value, sub, color, status, statusType }) {
  return (
    <div className={`kpi-card ${color}`}>
      <div className="kpi-header">
        <div className={`kpi-icon ${color}`}>{icon}</div>
        {status && <span className={`kpi-status ${statusType||''}`}>{status}</span>}
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
      <div className="filter-group"><label className="filter-label">From</label><input type="date" className="filter-input" value={filters.date_from} onChange={e=>setFilters({...filters,date_from:e.target.value})} /></div>
      <div className="filter-group"><label className="filter-label">To</label><input type="date" className="filter-input" value={filters.date_to} onChange={e=>setFilters({...filters,date_to:e.target.value})} /></div>
      <div className="filter-group"><label className="filter-label">Origin</label><input type="text" className="filter-input" placeholder="e.g. Base" value={filters.origin} onChange={e=>setFilters({...filters,origin:e.target.value})} /></div>
      <div className="filter-group"><label className="filter-label">Destination</label><input type="text" className="filter-input" placeholder="e.g. Jamshedpur" value={filters.destination} onChange={e=>setFilters({...filters,destination:e.target.value})} /></div>
      <div className="filter-group"><label className="filter-label">Material</label><input type="text" className="filter-input" placeholder="e.g. sheet" value={filters.vehicle_type} onChange={e=>setFilters({...filters,vehicle_type:e.target.value})} /></div>
      <button className="btn btn-primary" onClick={onFilter}>Apply</button>
      <button className="btn btn-ghost" onClick={onClear}>Clear</button>
    </div>
  );
}

function ErrorState({ msg, onRetry }) {
  return <div className="empty-state"><div className="empty-state-icon">⚠️</div><div className="empty-state-title">Error</div><p>{msg}</p>{onRetry && <button className="btn btn-primary" style={{marginTop:'1rem'}} onClick={onRetry}>Retry</button>}</div>;
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
  const [dragOver,setDragOver] = useState(false);
  const [uploading,setUploading] = useState(false);
  const [result,setResult] = useState(null);
  const [error,setError] = useState(null);

  const handleFile = async (file) => {
    if(!file) return; setUploading(true); setResult(null); setError(null);
    try { const res = await uploadFile(file); setResult(res); setTimeout(()=>onUploadDone(),2500); }
    catch(e) { setError(e.message); }
    finally { setUploading(false); }
  };

  return (
    <div className="upload-container">
      <div className={`upload-zone ${dragOver?'drag-over':''} ${uploading?'uploading':''}`}
        onDragOver={e=>{e.preventDefault();setDragOver(true);}} onDragLeave={()=>setDragOver(false)}
        onDrop={e=>{e.preventDefault();setDragOver(false);handleFile(e.dataTransfer.files[0]);}}
        onClick={()=>document.getElementById('file-input').click()}>
        <div className="upload-icon">{uploading?'⏳':'📁'}</div>
        <div className="upload-title">{uploading?'Processing your data...':'Drop your Excel/CSV file here'}</div>
        <div className="upload-subtitle">Supports .xlsx, .xls, .csv (max 10MB)</div>
        {uploading && <div className="progress-bar-container"><div className="progress-bar-fill" style={{width:'80%'}} /></div>}
        <input id="file-input" className="upload-input" type="file" accept=".xlsx,.xls,.csv" onChange={e=>handleFile(e.target.files[0])} />
      </div>

      {result && (
        <div className="upload-result success">
          <div className="upload-result-title">✅ {result.message}</div>
          <div className="upload-stats">
            <div className="upload-stat"><div className="upload-stat-value">{result.processed_rows}</div><div className="upload-stat-label">Processed</div></div>
            <div className="upload-stat"><div className="upload-stat-value" style={{color:result.error_rows>0?'#f59e0b':'#10b981'}}>{result.error_rows}</div><div className="upload-stat-label">Errors</div></div>
            <div className="upload-stat"><div className="upload-stat-value">{result.duplicates_removed||0}</div><div className="upload-stat-label">Duplicates</div></div>
            <div className="upload-stat"><div className="upload-stat-value">{result.processing_time}</div><div className="upload-stat-label">Time</div></div>
          </div>
          {result.data_quality_score != null && (
            <div style={{marginTop:'1rem',padding:'1rem',background:'var(--bg-glass)',borderRadius:'var(--radius-sm)'}}>
              <div style={{display:'flex',alignItems:'center',gap:'0.75rem',marginBottom:'0.5rem'}}>
                <span style={{fontWeight:600}}>Data Quality Score:</span>
                <QualityBadge score={result.data_quality_score} />
              </div>
              {result.quality_issues?.length > 0 && (
                <ul style={{paddingLeft:'1.25rem',fontSize:'0.8rem',color:'var(--text-secondary)'}}>
                  {result.quality_issues.map((issue,i)=><li key={i} style={{marginBottom:'0.3rem'}}>{issue}</li>)}
                </ul>
              )}
            </div>
          )}
        </div>
      )}
      {error && <div className="upload-result error"><div className="upload-result-title">❌ Upload Failed</div><p style={{color:'#f87171'}}>{error}</p></div>}
    </div>
  );
}


// ═══════════════════════════════════════════════════════════
// History View
// ═══════════════════════════════════════════════════════════
function HistoryView({ uploads, loading }) {
  if (loading) return <Spinner text="Loading upload history..." />;
  if (!uploads?.length) return <div className="empty-state"><div className="empty-state-icon">📋</div><div className="empty-state-title">No Uploads Yet</div><p>Upload your first shipment file to see history here.</p></div>;

  return (
    <div className="history-table-wrap">
      <table className="history-table">
        <thead><tr><th>File</th><th>Status</th><th>Rows</th><th>Processed</th><th>Errors</th><th>Dups</th><th>Quality</th><th>Time</th><th>Uploaded</th></tr></thead>
        <tbody>
          {uploads.map(u=>(
            <tr key={u.id}>
              <td style={{color:'#f1f3f9',fontWeight:500}}>{u.file_name}</td>
              <td><span className={`status-badge ${u.status}`}>{u.status}</span></td>
              <td>{u.total_rows}</td><td>{u.processed_rows}</td>
              <td style={{color:u.error_rows>0?'#f59e0b':'inherit'}}>{u.error_rows}</td>
              <td>{u.duplicate_rows||0}</td>
              <td>{u.data_quality_score != null ? <QualityBadge score={u.data_quality_score} /> : '-'}</td>
              <td>{u.duration_display||'—'}</td>
              <td>{new Date(u.uploaded_at).toLocaleString('en-IN')}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
