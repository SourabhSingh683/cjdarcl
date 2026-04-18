import { useState, useEffect } from 'react';
import {
  fetchProfitSummary, fetchProfitLanes, fetchProfitTrends,
  fetchProfitAlerts, fetchProfitDrilldown, fetchProfitInsights,
  fetchProfitLaneShipments,
} from '../api';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  LineChart, Line, PieChart, Pie, Cell, Legend,
} from 'recharts';

const CATEGORY_CONFIG = {
  good: { label: 'Good Lane (>7%)', color: '#10b981', icon: '🟢', bg: 'rgba(16,185,129,0.08)', border: 'rgba(16,185,129,0.25)' },
  average: { label: 'Average Lane (3-7%)', color: '#3b82f6', icon: '🔵', bg: 'rgba(59,130,246,0.08)', border: 'rgba(59,130,246,0.25)' },
  low_margin: { label: 'Low Margin (0-3%)', color: '#f59e0b', icon: '🟡', bg: 'rgba(245,158,11,0.08)', border: 'rgba(245,158,11,0.25)' },
  bad: { label: 'Loss Lane (<0%)', color: '#f43f5e', icon: '🔴', bg: 'rgba(244,63,94,0.08)', border: 'rgba(244,63,94,0.25)' },
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

// --- Optimized Form Input to prevent Lag ---
const FilterInput = ({ label, type = "text", placeholder, value, onChange, onKeyDown }) => {
  const [localVal, setLocalVal] = useState(value);

  useEffect(() => {
    setLocalVal(value);
  }, [value]);

  const handleChange = (e) => {
    const v = e.target.value;
    setLocalVal(v);
    onChange(v);
  };

  const inputStyle = {
    padding: '0.65rem 0.85rem', borderRadius: '10px', border: '1px solid #e2e8f0',
    fontSize: '0.85rem', flex: '1', minWidth: '150px', background: '#f8fafc',
    color: '#0f172a', outline: 'none', transition: 'all 0.2s', width: '100%',
    boxSizing: 'border-box'
  };
  
  const labelStyle = {
    fontSize: '0.7rem', fontWeight: 700, color: '#64748b', marginBottom: '0.35rem',
    textTransform: 'uppercase', letterSpacing: '0.04em', display: 'block',
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', minWidth: '160px', flex: '1' }}>
      <label style={labelStyle}>{label}</label>
      <input 
        type={type} 
        placeholder={placeholder} 
        value={localVal || ''} 
        onChange={handleChange} 
        onKeyDown={onKeyDown} 
        style={inputStyle} 
      />
    </div>
  );
};

// --- Isolated Filter Section to Prevent Dashboard Re-renders while Typing ---
const FilterSection = ({ initialFilters, onApply, onClear }) => {
  const [localFilters, setLocalFilters] = useState(initialFilters);

  useEffect(() => {
    setLocalFilters(initialFilters);
  }, [initialFilters]);

  const handleChange = (field, val) => {
    setLocalFilters(prev => ({ ...prev, [field]: val }));
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') {
      onApply(localFilters);
    }
  };

  return (
    <div style={{
      background: '#fff', padding: '1.5rem', borderRadius: '16px',
      border: '1px solid #e2e8f0', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.05)',
      display: 'flex', flexDirection: 'column', gap: '1.25rem', marginBottom: '1.5rem',
    }}>
      <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
        <FilterInput label="From Date" type="date" value={localFilters.from} onChange={v => handleChange('from', v)} onKeyDown={handleKeyDown} />
        <FilterInput label="To Date" type="date" value={localFilters.to} onChange={v => handleChange('to', v)} onKeyDown={handleKeyDown} />
        <FilterInput label="Origin City" placeholder="e.g. Jamshedpur" value={localFilters.orig} onChange={v => handleChange('orig', v)} onKeyDown={handleKeyDown} />
        <FilterInput label="Destination City" placeholder="e.g. Pune" value={localFilters.dest} onChange={v => handleChange('dest', v)} onKeyDown={handleKeyDown} />
      </div>
      <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
        <FilterInput label="CN No / SAP No" placeholder="e.g. 8000..." value={localFilters.cn} onChange={v => handleChange('cn', v)} onKeyDown={handleKeyDown} />
        <FilterInput label="Material" placeholder="e.g. Steel" value={localFilters.mat} onChange={v => handleChange('mat', v)} onKeyDown={handleKeyDown} />
        <FilterInput label="Transporter" placeholder="e.g. Agent Name" value={localFilters.trans} onChange={v => handleChange('trans', v)} onKeyDown={handleKeyDown} />
        <FilterInput label="Region" placeholder="e.g. East" value={localFilters.reg} onChange={v => handleChange('reg', v)} onKeyDown={handleKeyDown} />
        <FilterInput label="Customer" placeholder="e.g. TATA" value={localFilters.cust} onChange={v => handleChange('cust', v)} onKeyDown={handleKeyDown} />
        <div style={{ display: 'flex', flexDirection: 'column', minWidth: '160px', flex: '1' }}>
          <label style={{ fontSize: '0.7rem', fontWeight: 700, color: '#64748b', marginBottom: '0.35rem', textTransform: 'uppercase', letterSpacing: '0.04em' }}>Margin Type</label>
          <select 
            value={localFilters.margin_type || ''} 
            onChange={e => handleChange('margin_type', e.target.value)}
            style={{ 
              padding: '0.65rem 0.85rem', borderRadius: '10px', border: '1px solid #e2e8f0', 
              fontSize: '0.85rem', flex: '1', background: '#f8fafc', color: '#0f172a', outline: 'none' 
            }}
          >
            <option value="">All Lanes</option>
            <option value="profit">Only Profit Lanes</option>
            <option value="loss">Only Loss Lanes</option>
          </select>
        </div>
      </div>
      <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '0.5rem' }}>
        <button onClick={onClear} style={{
          padding: '0.6rem 1.5rem', borderRadius: '10px', border: '1px solid #e2e8f0',
          background: '#fff', color: '#64748b', fontWeight: 600, fontSize: '0.85rem', cursor: 'pointer',
        }}>Clear Filters</button>
        <button onClick={() => onApply(localFilters)} style={{
          padding: '0.6rem 2rem', borderRadius: '10px', border: 'none',
          background: '#3b82f6', color: '#fff', fontWeight: 600, fontSize: '0.85rem', cursor: 'pointer',
          boxShadow: '0 4px 10px rgba(59,130,246,0.3)',
        }}>Apply Search</button>
      </div>
    </div>
  );
};

export default function ProfitAnalysis() {
  const [summary, setSummary] = useState(null);
  const [lanes, setLanes] = useState(null);
  const [trends, setTrends] = useState([]);
  const [trendsQuality, setTrendsQuality] = useState(null);
  const [trendsTabSummary, setTrendsTabSummary] = useState(null);
  const [trendSubTab, setTrendSubTab] = useState('critical');
  const [alerts, setAlerts] = useState([]);
  const [insights, setInsights] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [drilldown, setDrilldown] = useState(null);
  const [drillLoading, setDrillLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('overview');
  const [categoryFilter, setCategoryFilter] = useState('all');
  const [laneSearch, setLaneSearch] = useState('');
  const [expandedLane, setExpandedLane] = useState(null); // {id: 'City-City', shipments: [], loading: false}
  
  const tabs = [
    { key: 'overview', label: '📊 Overview' },
    { key: 'lanes', label: '🛤️ Lanes' },
    { key: 'trends', label: '📈 Trends' },
    { key: 'customer_search', label: '🔍 Customer Search' },
  ];

  // --- Search Filters ---
  const [filters, setFilters] = useState({
    from: '', to: '', orig: '', dest: '', cn: '', 
    mat: '', trans: '', reg: '', cust: '', margin_type: ''
  });
  const [activeFilters, setActiveFilters] = useState({});
  const [searchShipments, setSearchShipments] = useState([]);
  const [searchShipmentsLoading, setSearchShipmentsLoading] = useState(false);

  useEffect(() => {
    loadAll();
  }, []);

  const loadAll = async (f = activeFilters) => {
    setLoading(true); setError(null);
    try {
      const [s, l, tRaw, a, ins] = await Promise.all([
        fetchProfitSummary(f), fetchProfitLanes(f), fetchProfitTrends(f),
        fetchProfitAlerts(f), fetchProfitInsights(f),
      ]);
      setSummary(s); setLanes(l); setAlerts(a); setInsights(ins);
      // Handle new trends response: { trends: [...], data_quality: {...}, tab_summary: {...} }
      if (tRaw && typeof tRaw === 'object' && !Array.isArray(tRaw)) {
        setTrends(tRaw.trends || []);
        setTrendsQuality(tRaw.data_quality || null);
        setTrendsTabSummary(tRaw.tab_summary || null);
        // Auto-select tab with most items
        const ts = tRaw.tab_summary;
        if (ts) {
          if (ts.critical > 0) setTrendSubTab('critical');
          else if (ts.warning > 0) setTrendSubTab('warning');
          else setTrendSubTab('good');
        }
      } else {
        setTrends(Array.isArray(tRaw) ? tRaw : []);
        setTrendsQuality(null);
        setTrendsTabSummary(null);
      }
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
    
    // Fetch shipment details for the search results (no limit as requested)
    setSearchShipmentsLoading(true);
    try {
      const sData = await fetchProfitLaneShipments("", "", f);
      setSearchShipments(sData || []);
    } catch (e) { console.error("Failed to fetch search shipments:", e); }
    finally { setSearchShipmentsLoading(false); }
  };

  const applyFilters = (newFilters) => {
    setFilters(newFilters);
    setActiveFilters(newFilters);
    loadAll(newFilters);
  };

  const clearFilters = () => {
    const empty = { 
      from: '', to: '', orig: '', dest: '', cn: '', 
      mat: '', trans: '', reg: '', cust: '', margin_type: '' 
    };
    setFilters(empty);
    setActiveFilters(empty);
    loadAll(empty);
  };

  const openDrilldown = async (loadingCity, deliveryCity) => {
    setDrillLoading(true);
    try {
      const d = await fetchProfitDrilldown(loadingCity, deliveryCity, activeFilters);
      setDrilldown(d);
    } catch (e) { alert(`Error: ${e.message}`); }
    finally { setDrillLoading(false); }
  };

  const toggleLaneDetails = async (lane) => {
    const laneId = `${lane.loading_city}-${lane.delivery_city}`;
    if (expandedLane?.id === laneId) {
      setExpandedLane(null);
      return;
    }

    setExpandedLane({ id: laneId, shipments: [], loading: true });
    try {
      const data = await fetchProfitLaneShipments(lane.loading_city, lane.delivery_city, activeFilters);
      setExpandedLane({ id: laneId, shipments: data, loading: false });
    } catch (e) {
      alert(`Failed to fetch shipment details: ${e.message}`);
      setExpandedLane(null);
    }
  };

  if (loading) return <div style={{ padding: '3rem', textAlign: 'center', color: '#94a3b8' }}>⏳ Loading Profit Intelligence...</div>;
  if (error) return <div style={{ padding: '2rem', color: '#f43f5e' }}>Error: {error}</div>;
  if (summary?.error) return (
    <div style={{ padding: '5rem 2rem', textAlign: 'center', background: '#fff', borderRadius: '24px', border: '1px dashed #cbd5e1' }}>
      <div style={{ fontSize: '4rem', marginBottom: '1.5rem' }}>📊</div>
      <h2 style={{ color: '#0f172a', marginBottom: '0.5rem' }}>No profit data available</h2>
      <p style={{ color: '#64748b', maxWidth: '400px', margin: '0 auto' }}>
        Upload a Gross Margin MIS file to get started with profit intelligence and lane analysis.
      </p>
    </div>
  );

  if (summary?.no_results && activeTab !== 'customer_search') return (
    <div style={{ padding: '2rem' }}>
      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem' }}>
        {tabs.map(t => (
          <button key={t.key} onClick={() => setActiveTab(t.key)} style={{
            padding: '0.5rem 1.25rem', borderRadius: '999px', border: activeTab === t.key ? '2px solid #3b82f6' : '1px solid #e2e8f0',
            background: activeTab === t.key ? 'rgba(59,130,246,0.08)' : '#fff', color: activeTab === t.key ? '#3b82f6' : '#64748b',
            fontWeight: 600, fontSize: '0.85rem', cursor: 'pointer',
          }}>{t.label}</button>
        ))}
      </div>
      
      <div style={{ padding: '5rem 2rem', textAlign: 'center', background: '#fff', borderRadius: '24px', border: '1px dashed #e2e8f0' }}>
        <div style={{ fontSize: '4rem', marginBottom: '1.5rem' }}>🔍</div>
        <h2 style={{ color: '#0f172a', marginBottom: '0.5rem' }}>No data for such filters</h2>
        <p style={{ color: '#64748b', maxWidth: '400px', margin: '0 auto 2rem' }}>
          We couldn't find any profit records matching your current search criteria. Try adjusting or clearing your filters.
        </p>
        <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center' }}>
           <button onClick={() => setActiveTab('customer_search')} style={{
            padding: '0.75rem 2.5rem', borderRadius: '12px', background: '#f1f5f9', color: '#475569',
            fontWeight: 700, border: 'none', cursor: 'pointer'
          }}>Edit Filters</button>
          <button onClick={clearFilters} style={{
            padding: '0.75rem 2.5rem', borderRadius: '12px', background: '#3b82f6', color: '#fff',
            fontWeight: 700, border: 'none', cursor: 'pointer', boxShadow: '0 4px 12px rgba(59,130,246,0.3)'
          }}>Clear All Filters</button>
        </div>
      </div>
    </div>
  );

  const filteredLanes = lanes?.lanes?.filter(l => categoryFilter === 'all' || l.category === categoryFilter) || [];

  // Pie data for lane distribution
  const pieData = lanes?.summary ? Object.entries(lanes.summary).filter(([,v]) => v > 0).map(([k, v]) => ({
    name: CATEGORY_CONFIG[k]?.label || k, value: v, color: CATEGORY_CONFIG[k]?.color || '#94a3b8'
  })) : [];

  const totalAlertRoutes = alerts.reduce((sum, a) => sum + (a.routes?.length || 0), 0);


  /* ── Helper: render the routes table inside a consolidated alert card ── */
  const renderAlertRouteTable = (alert) => {
    const routes = alert.routes || [];
    if (routes.length === 0) return null;

    const thStyle = {
      padding: '0.5rem 0.75rem', textAlign: 'left', fontWeight: 700, fontSize: '0.7rem',
      textTransform: 'uppercase', letterSpacing: '0.04em', color: '#64748b',
      borderBottom: '2px solid #e2e8f0', whiteSpace: 'nowrap',
    };
    const tdStyle = {
      padding: '0.5rem 0.75rem', fontSize: '0.82rem', fontWeight: 600,
      color: '#0f172a', borderBottom: '1px solid #f1f5f9', whiteSpace: 'nowrap',
    };

    if (alert.type === 'cost_increase') {
      return (
        <div style={{ overflowX: 'auto', marginTop: '0.5rem' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                <th style={thStyle}>#</th>
                <th style={thStyle}>Route</th>
                <th style={thStyle}>Increase %</th>
                <th style={thStyle}>From (₹/T)</th>
                <th style={thStyle}>To (₹/T)</th>
                <th style={thStyle}>Months</th>
              </tr>
            </thead>
            <tbody>
              {routes.map((r, i) => (
                <tr key={i} style={{ background: i % 2 === 0 ? 'transparent' : 'rgba(0,0,0,0.015)' }}>
                  <td style={tdStyle}>{i + 1}</td>
                  <td style={{ ...tdStyle, fontWeight: 700 }}>{r.lane_name}</td>
                  <td style={{ ...tdStyle, color: '#dc2626' }}>+{r.pct_change}%</td>
                  <td style={tdStyle}>₹{r.from_cpt?.toLocaleString('en-IN')}</td>
                  <td style={tdStyle}>₹{r.to_cpt?.toLocaleString('en-IN')}</td>
                  <td style={tdStyle}>{r.months}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
    }

    if (alert.type === 'high_deduction') {
      return (
        <div style={{ overflowX: 'auto', marginTop: '0.5rem' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                <th style={thStyle}>#</th>
                <th style={thStyle}>Route</th>
                <th style={thStyle}>Deduction %</th>
                <th style={thStyle}>Deductions</th>
                <th style={thStyle}>Freight</th>
                <th style={thStyle}>Shipments</th>
              </tr>
            </thead>
            <tbody>
              {routes.map((r, i) => (
                <tr key={i} style={{ background: i % 2 === 0 ? 'transparent' : 'rgba(0,0,0,0.015)' }}>
                  <td style={tdStyle}>{i + 1}</td>
                  <td style={{ ...tdStyle, fontWeight: 700 }}>{r.lane_name}</td>
                  <td style={{ ...tdStyle, color: '#d97706' }}>{r.deduction_pct}%</td>
                  <td style={tdStyle}>{fmt(r.total_deductions)}</td>
                  <td style={tdStyle}>{fmt(r.total_freight)}</td>
                  <td style={tdStyle}>{r.total_shipments}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
    }

    // Default for loss, high_performance, abnormal_loss, abnormal_profit
    return (
      <div style={{ overflowX: 'auto', marginTop: '0.5rem' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              <th style={thStyle}>#</th>
              <th style={thStyle}>Route</th>
              <th style={thStyle}>Margin %</th>
              <th style={thStyle}>Profit</th>
              <th style={thStyle}>Freight</th>
              <th style={thStyle}>Shipments</th>
            </tr>
          </thead>
          <tbody>
            {routes.map((r, i) => (
              <tr key={i} style={{ background: i % 2 === 0 ? 'transparent' : 'rgba(0,0,0,0.015)' }}>
                <td style={tdStyle}>{i + 1}</td>
                <td style={{ ...tdStyle, fontWeight: 700 }}>{r.lane_name}</td>
                <td style={{ ...tdStyle, color: r.margin_pct >= 0 ? '#059669' : '#dc2626' }}>{r.margin_pct}%</td>
                <td style={{ ...tdStyle, color: r.total_profit >= 0 ? '#059669' : '#dc2626' }}>{fmt(r.total_profit)}</td>
                <td style={tdStyle}>{fmt(r.total_freight)}</td>
                <td style={tdStyle}>{r.total_shipments}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  };

  const renderFilters = () => {
    return (
      <FilterSection 
        initialFilters={filters} 
        onApply={applyFilters} 
        onClear={clearFilters} 
      />
    );
  };

  const filtersCount = Object.values(activeFilters).filter(v => v !== '').length;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      
      {/* Tab Navigation */}
      <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', alignItems: 'center' }}>
        {tabs.map(t => (
          <button key={t.key} onClick={() => setActiveTab(t.key)} style={{
            padding: '0.5rem 1.25rem', borderRadius: '999px', border: activeTab === t.key ? '2px solid #3b82f6' : '1px solid #e2e8f0',
            background: activeTab === t.key ? 'rgba(59,130,246,0.08)' : '#fff', color: activeTab === t.key ? '#3b82f6' : '#64748b',
            fontWeight: 600, fontSize: '0.85rem', cursor: 'pointer', transition: 'all 0.2s', fontFamily: 'inherit',
            position: 'relative'
          }}>
            {t.label}
            {t.key === 'customer_search' && filtersCount > 0 && (
              <span style={{
                position: 'absolute', top: '-5px', right: '-5px', background: '#3b82f6', color: '#fff',
                fontSize: '0.6rem', padding: '2px 6px', borderRadius: '10px', border: '2px solid #f8fafc'
              }}>{filtersCount}</span>
            )}
          </button>
        ))}
        {filtersCount > 0 && activeTab !== 'customer_search' && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.4rem 1rem', background: 'rgba(59,130,246,0.06)', borderRadius: '999px', border: '1px solid rgba(59,130,246,0.2)' }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 600, color: '#3b82f6' }}>✨ Filters Applied</span>
            <button onClick={clearFilters} style={{ background: 'none', border: 'none', color: '#3b82f6', fontSize: '0.75rem', fontWeight: 800, cursor: 'pointer', textDecoration: 'underline' }}>Clear</button>
          </div>
        )}
      </div>

      {activeTab === 'customer_search' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', animation: 'fadeIn 0.3s ease' }}>
          {renderFilters()}
          
          <div style={{ borderTop: '1px solid #e2e8f0', paddingTop: '1.5rem' }}>
             <h3 style={{ margin: '0 0 1rem 0', fontSize: '1.1rem', color: '#0f172a' }}>Search Results Summary</h3>
             <div className="kpi-grid">
               {[
                 { label: 'Freight', value: fmt(summary.total_freight), icon: '💰', color: 'blue' },
                 { label: 'Cost', value: fmt(summary.total_cost), icon: '📦', color: 'amber' },
                 { label: 'Margin', value: `${summary.overall_margin_pct}%`, icon: '🎯', color: summary.overall_margin_pct >= 3 ? 'emerald' : 'rose' },
                 { label: 'Shipments', value: summary.total_records, icon: '🚛', color: 'slate' },
               ].map((kpi, i) => (
                 <div key={i} className={`kpi-card ${kpi.color}`}>
                   <div className="kpi-header"><div className={`kpi-icon ${kpi.color}`}>{kpi.icon}</div></div>
                   <div className="kpi-label">{kpi.label}</div>
                   <div className="kpi-value">{kpi.value}</div>
                 </div>
               ))}
             </div>
             <p style={{ marginTop: '1rem', fontSize: '0.85rem', color: '#64748b' }}>
               Switch to <b>Overview</b>, <b>Lanes</b>, or <b>Trends</b> to see detailed visualizations for this selection.
             </p>
          </div>

          <div style={{ background: '#fff', borderRadius: '16px', border: '1px solid #e2e8f0', overflow: 'hidden' }}>
            <div style={{ padding: '1.25rem', borderBottom: '1px solid #f1f5f9', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h4 style={{ margin: 0, fontSize: '0.95rem', color: '#1e293b' }}>Itemized Shipments</h4>
              <div style={{ fontSize: '0.78rem', color: '#64748b' }}>Showing all {searchShipments.length} records matching filters</div>
            </div>
            
            {searchShipmentsLoading ? (
               <div style={{ padding: '3rem', textAlign: 'center', color: '#94a3b8' }}>⏳ Loading shipments...</div>
            ) : (
              <div style={{ overflowX: 'auto', maxHeight: '600px' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead style={{ position: 'sticky', top: 0, background: '#f8fafc', zIndex: 10 }}>
                    <tr>
                      {['Date', 'SAP External No', 'Origin → Destination', 'Material', 'Vehicle', 'Weight (T)', 'Freight', 'Cost', 'Margin', 'C/T'].map(h => (
                        <th key={h} style={{ padding: '0.75rem', textAlign: 'left', fontSize: '0.7rem', fontWeight: 700, color: '#64748b', textTransform: 'uppercase', borderBottom: '2px solid #f1f5f9' }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {searchShipments.map((s, idx) => (
                      <tr key={idx} style={{ borderBottom: '1px solid #f8fafc', background: idx % 2 === 0 ? 'transparent' : 'rgba(0,0,0,0.01)' }}>
                        <td style={{ padding: '0.75rem', fontSize: '0.78rem', color: '#475569' }}>{s.cn_date}</td>
                        <td style={{ padding: '0.75rem', fontSize: '0.78rem', fontWeight: 600 }}>{s.sap_external_no}</td>
                        <td style={{ padding: '0.75rem', fontSize: '0.78rem', fontWeight: 600 }}>{s.loading_city} → {s.delivery_city}</td>
                        <td style={{ padding: '0.75rem', fontSize: '0.78rem', color: '#475569' }}>{s.material_name}</td>
                        <td style={{ padding: '0.75rem', fontSize: '0.78rem', color: '#475569' }}>{s.vehicle}</td>
                        <td style={{ padding: '0.75rem', fontSize: '0.78rem', fontWeight: 600 }}>{Math.round(s.weight)}</td>
                        <td style={{ padding: '0.75rem', fontSize: '0.78rem', fontWeight: 600 }}>₹{Math.round(s.freight).toLocaleString('en-IN')}</td>
                        <td style={{ padding: '0.75rem', fontSize: '0.78rem', fontWeight: 600 }}>₹{Math.round(s.cost).toLocaleString('en-IN')}</td>
                        <td style={{ padding: '0.75rem', fontSize: '0.78rem', fontWeight: 700, color: s.profit < 0 ? '#dc2626' : '#059669' }}>₹{Math.round(s.profit).toLocaleString('en-IN')}</td>
                        <td style={{ padding: '0.75rem', fontSize: '0.78rem', fontWeight: 600 }}>₹{Math.round(s.cpt).toLocaleString('en-IN')}</td>
                      </tr>
                    ))}
                    {searchShipments.length === 0 && (
                      <tr><td colSpan="10" style={{ padding: '3rem', textAlign: 'center', color: '#94a3b8' }}>No shipment records found for these filters.</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ──── OVERVIEW TAB ──── */}
      {activeTab === 'overview' && (
        <>
          {/* KPI Cards */}
          <div className="kpi-grid">
            {[
              { label: 'Total Freight', value: fmt(summary.total_freight), icon: '💰', color: 'blue', sub: `${summary.total_records} records` },
              { label: 'Total Cost', value: fmt(summary.total_cost), icon: '📦', color: 'amber', sub: 'Transport + Operations' },
              { label: 'Gross Profit (GM1)', value: fmt(summary.total_profit), icon: summary.total_profit >= 0 ? '📈' : '📉', color: summary.total_profit >= 0 ? 'emerald' : 'rose', sub: `Final GM7: ${fmt(summary.final_profit_gm7)}` },
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
                  <PieChart margin={{ top: 20, right: 30, left: 30, bottom: 20 }}>
                    <Pie 
                      data={pieData} 
                      cx="50%" 
                      cy="50%" 
                      innerRadius={70} 
                      outerRadius={90} 
                      dataKey="value" 
                      labelLine={false}
                      label={({ name, value }) => `${name}: ${value}`}
                    >
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
                {alerts.map((a, i) => {
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

        </>
      )}

      {/* ──── LANES TAB ──── */}
      {activeTab === 'lanes' && (() => {
        const searchTerm = (laneSearch || '').toLowerCase();
        const sorted = (lanes?.lanes || [])
          .filter(l => categoryFilter === 'all' || l.category === categoryFilter)
          .filter(l => !searchTerm || l.lane_name.toLowerCase().includes(searchTerm))
          .sort((a, b) => (b.cpt_pct_change || 0) - (a.cpt_pct_change || 0));

        return (
        <>
          {/* Search Bar */}
          <div style={{ marginBottom: '0.75rem' }}>
            <div style={{ position: 'relative' }}>
              <span style={{ position: 'absolute', left: '0.85rem', top: '50%', transform: 'translateY(-50%)', fontSize: '1rem', color: '#94a3b8', pointerEvents: 'none' }}>🔍</span>
              <input
                type="text"
                value={laneSearch}
                onChange={e => setLaneSearch(e.target.value)}
                placeholder="Search routes... e.g. bokaro, jamshedpur → pune"
                style={{
                  width: '100%', padding: '0.7rem 1rem 0.7rem 2.5rem', borderRadius: '12px', fontSize: '0.88rem',
                  border: '1px solid #e2e8f0', outline: 'none', fontFamily: 'inherit', color: '#0f172a',
                  background: '#fff', boxSizing: 'border-box', transition: 'border-color 0.2s',
                }}
                onFocus={e => e.target.style.borderColor = '#3b82f6'}
                onBlur={e => e.target.style.borderColor = '#e2e8f0'}
              />
              {laneSearch && (
                <button onClick={() => setLaneSearch('')} style={{
                  position: 'absolute', right: '0.75rem', top: '50%', transform: 'translateY(-50%)',
                  background: '#f1f5f9', border: 'none', borderRadius: '50%', width: '22px', height: '22px',
                  cursor: 'pointer', fontSize: '0.7rem', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#64748b',
                }}>✕</button>
              )}
            </div>
            {searchTerm && (
              <div style={{ fontSize: '0.78rem', color: '#64748b', marginTop: '0.4rem' }}>
                Found {sorted.length} route{sorted.length !== 1 ? 's' : ''} matching "{laneSearch}"
              </div>
            )}
          </div>

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

          {/* Lane Rows (Transitioned from Cards) */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginTop: '1rem' }}>
            {sorted.map((lane, i) => {
              const cat = CATEGORY_CONFIG[lane.category] || CATEGORY_CONFIG.good;
              const isExpanded = expandedLane?.id === `${lane.loading_city}-${lane.delivery_city}`;
              
              return (
                <div key={i} style={{
                  background: '#fff', border: `1px solid ${isExpanded ? cat.color : '#e2e8f0'}`, borderRadius: '12px',
                  overflow: 'hidden', transition: 'all 0.2s',
                  boxShadow: isExpanded ? '0 4px 20px rgba(0,0,0,0.08)' : 'none',
                }}>
                  {/* Row Header */}
                  <div 
                    onClick={() => toggleLaneDetails(lane)}
                    style={{
                      display: 'flex', alignItems: 'center', padding: '1rem 1.25rem', cursor: 'pointer',
                      background: isExpanded ? 'rgba(0,0,0,0.01)' : 'transparent',
                    }}
                  >
                    <div style={{ flex: '1', minWidth: 0 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                        <div style={{ fontSize: '1rem', fontWeight: 700, color: '#0f172a' }}>{lane.lane_name}</div>
                        <span style={{ fontSize: '0.65rem', fontWeight: 700, color: cat.color, background: cat.bg, padding: '2px 8px', borderRadius: '999px', border: `1px solid ${cat.border}` }}>{cat.label}</span>
                      </div>
                      <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '0.2rem' }}>
                        {lane.total_shipments} shipments • ₹{lane.total_freight.toLocaleString('en-IN')} revenue
                      </div>
                    </div>

                    <div style={{ display: 'flex', gap: '1.5rem', alignItems: 'center', padding: '0 1rem' }}>
                      <div style={{ minWidth: '80px' }}>
                        <div style={{ fontSize: '0.6rem', color: '#94a3b8', fontWeight: 700, textTransform: 'uppercase' }}>Margin</div>
                        <div style={{ fontSize: '0.9rem', fontWeight: 700, color: lane.margin_pct < 0 ? '#dc2626' : '#059669' }}>
                          ₹{lane.total_profit.toLocaleString('en-IN')}
                        </div>
                        <div style={{ fontSize: '0.7rem', fontWeight: 600, color: lane.margin_pct < 0 ? '#dc2626' : '#059669' }}>
                          {lane.margin_pct}%
                        </div>
                      </div>
                      <div style={{ minWidth: '80px' }}>
                        <div style={{ fontSize: '0.6rem', color: '#94a3b8', fontWeight: 700, textTransform: 'uppercase' }}>Cost/T</div>
                        <div style={{ fontSize: '0.9rem', fontWeight: 700, color: '#0f172a' }}>₹{Math.round(lane.cost_per_tonne)?.toLocaleString('en-IN')}</div>
                      </div>
                      <div style={{ width: '100px' }}>
                        <div style={{ fontSize: '0.6rem', color: '#94a3b8', fontWeight: 700, textTransform: 'uppercase' }}>Trend</div>
                        <div style={{ fontSize: '0.75rem', fontWeight: 700, color: lane.cpt_pct_change > 0 ? '#dc2626' : '#059669' }}>
                          {lane.cpt_pct_change > 0 ? '📈 +' : '📉 '}{lane.cpt_pct_change}%
                        </div>
                      </div>
                    </div>

                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                      <button 
                        onClick={(e) => { e.stopPropagation(); openDrilldown(lane.loading_city, lane.delivery_city); }}
                        style={{
                          padding: '0.4rem 0.8rem', borderRadius: '8px', fontSize: '0.75rem', fontWeight: 600,
                          background: '#f8fafc', border: '1px solid #e2e8f0', color: '#475569', cursor: 'pointer',
                        }}
                      >Waterfall</button>
                      <div style={{ fontSize: '1.2rem', color: '#94a3b8', paddingLeft: '0.5rem' }}>{isExpanded ? '▴' : '▾'}</div>
                    </div>
                  </div>

                  {/* Expanded Shipment Details */}
                  {isExpanded && (
                    <div style={{ borderTop: '1px solid #f1f5f9', padding: '1.25rem', background: '#fdfdfe' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                        <h4 style={{ margin: 0, fontSize: '0.9rem', color: '#1e293b' }}>Itemized Shipments Details</h4>
                        <div style={{ fontSize: '0.75rem', color: '#64748b' }}>Showing all shipments for this lane</div>
                      </div>

                      {expandedLane.loading ? (
                        <div style={{ padding: '2rem', textAlign: 'center', color: '#94a3b8', fontSize: '0.8rem' }}>Loading shipments...</div>
                      ) : (
                        <div style={{ overflowX: 'auto' }}>
                          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                            <thead>
                              <tr>
                                {['Date', 'SAP External No', 'Customer', 'Vehicle', 'Weight (T)', 'Freight', 'Cost', 'Margin', 'C/T'].map(h => (
                                  <th key={h} style={{ padding: '0.75rem', textAlign: 'left', fontSize: '0.7rem', fontWeight: 700, color: '#64748b', textTransform: 'uppercase', borderBottom: '2px solid #f1f5f9' }}>{h}</th>
                                ))}
                              </tr>
                            </thead>
                            <tbody>
                              {expandedLane.shipments.map((s, idx) => (
                                <tr key={idx} style={{ borderBottom: '1px solid #f8fafc' }}>
                                  <td style={{ padding: '0.75rem', fontSize: '0.78rem', color: '#475569' }}>{s.cn_date}</td>
                                  <td style={{ padding: '0.75rem', fontSize: '0.78rem', fontWeight: 600 }}>{s.sap_external_no}</td>
                                  <td style={{ padding: '0.75rem', fontSize: '0.78rem', color: '#475569', maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{s.customer}</td>
                                  <td style={{ padding: '0.75rem', fontSize: '0.78rem', color: '#475569' }}>{s.vehicle}</td>
                                  <td style={{ padding: '0.75rem', fontSize: '0.78rem', fontWeight: 600 }}>{Math.round(s.weight)}</td>
                                  <td style={{ padding: '0.75rem', fontSize: '0.78rem', fontWeight: 600 }}>₹{Math.round(s.freight).toLocaleString('en-IN')}</td>
                                  <td style={{ padding: '0.75rem', fontSize: '0.78rem', fontWeight: 600 }}>₹{Math.round(s.cost).toLocaleString('en-IN')}</td>
                                  <td style={{ padding: '0.75rem', fontSize: '0.78rem', fontWeight: 700, color: s.profit < 0 ? '#dc2626' : '#059669' }}>₹{Math.round(s.profit).toLocaleString('en-IN')}</td>
                                  <td style={{ padding: '0.75rem', fontSize: '0.78rem', fontWeight: 600 }}>₹{Math.round(s.cpt).toLocaleString('en-IN')}</td>
                                </tr>
                              ))}
                              {expandedLane.shipments.length === 0 && (
                                <tr><td colSpan="9" style={{ padding: '2rem', textAlign: 'center', color: '#94a3b8' }}>No shipment records found.</td></tr>
                              )}
                            </tbody>
                          </table>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
            {sorted.length === 0 && (
              <div style={{ padding: '3rem', textAlign: 'center', color: '#94a3b8', background: '#fff', borderRadius: '12px', border: '1px dashed #e2e8f0' }}>
                {laneSearch ? `No routes found matching "${laneSearch}"` : 'No lanes found in this category'}
              </div>
            )}
          </div>

        </>
        );
      })()}

      {/* ──── TRENDS TAB (Intelligent Decision Support) ──── */}
      {activeTab === 'trends' && (() => {
        const CATEGORY_BADGE = {
          loss_making: { label: 'Loss Making', color: '#dc2626', bg: 'rgba(220,38,38,0.08)' },
          high_cost_increase: { label: 'High Cost ↑', color: '#d97706', bg: 'rgba(217,119,6,0.08)' },
          declining_profit: { label: 'Declining Profit', color: '#ea580c', bg: 'rgba(234,88,12,0.08)' },
          top_performing: { label: 'Top Performer', color: '#059669', bg: 'rgba(5,150,105,0.08)' },
          abnormal: { label: 'Abnormal', color: '#7c3aed', bg: 'rgba(124,58,237,0.08)' },
          stable: { label: 'Stable', color: '#64748b', bg: 'rgba(100,116,139,0.08)' },
        };

        const SUB_TABS = [
          { key: 'critical', label: '🚨 Critical', color: '#dc2626', count: trendsTabSummary?.critical || 0 },
          { key: 'warning', label: '⚠️ Warning', color: '#d97706', count: trendsTabSummary?.warning || 0 },
          { key: 'good', label: '✅ Good', color: '#059669', count: trendsTabSummary?.good || 0 },
        ];

        const filteredTrends = trends.filter(t => t.tab === trendSubTab);

        return (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>

            {/* ── Summary Bar ── */}
            {trendsTabSummary && (
              <div className="chart-card" style={{ padding: '1rem 1.5rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '0.75rem' }}>
                  <div>
                    <div style={{ fontWeight: 700, fontSize: '0.95rem', color: '#0f172a' }}>
                      🧠 Intelligent Trend Analysis
                    </div>
                    <div style={{ fontSize: '0.8rem', color: '#64748b', marginTop: '0.15rem' }}>
                      Showing {trendsTabSummary.total_displayed} high-impact routes out of {trendsTabSummary.total_analyzed} analyzed
                      {trendsQuality && (
                        <> · Data Quality: <span style={{
                          fontWeight: 700,
                          color: trendsQuality.label === 'good' ? '#059669' : trendsQuality.label === 'warning' ? '#d97706' : '#dc2626',
                        }}>{trendsQuality.score}% {trendsQuality.label}</span></>
                      )}
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: '0.75rem', fontSize: '0.78rem' }}>
                    {SUB_TABS.map(tab => (
                      <div key={tab.key} style={{
                        display: 'flex', alignItems: 'center', gap: '0.35rem',
                        padding: '0.3rem 0.6rem', borderRadius: '8px',
                        background: tab.count > 0 ? tab.color + '12' : '#f1f5f9',
                      }}>
                        <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: tab.color, display: 'inline-block' }} />
                        <span style={{ fontWeight: 700, color: tab.color }}>{tab.count}</span>
                        <span style={{ color: '#64748b' }}>{tab.label.split(' ').pop()}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Transparency messages */}
                {trendsQuality?.messages?.length > 0 && (
                  <div style={{ marginTop: '0.75rem', display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
                    {trendsQuality.messages.map((msg, i) => (
                      <div key={i} style={{
                        fontSize: '0.75rem', color: '#475569', padding: '0.3rem 0.6rem',
                        background: 'rgba(59,130,246,0.03)', borderRadius: '6px', borderLeft: '2px solid #cbd5e1',
                      }}>ℹ️ {msg}</div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* ── Sub-Tab Navigation ── */}
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              {SUB_TABS.map(tab => {
                const isActive = trendSubTab === tab.key;
                return (
                  <button key={tab.key} onClick={() => setTrendSubTab(tab.key)} style={{
                    padding: '0.6rem 1.25rem', borderRadius: '12px', cursor: 'pointer', fontFamily: 'inherit',
                    fontWeight: 700, fontSize: '0.85rem', transition: 'all 0.2s',
                    background: isActive ? tab.color : '#fff',
                    color: isActive ? '#fff' : tab.color,
                    border: `2px solid ${isActive ? tab.color : tab.color + '40'}`,
                    boxShadow: isActive ? `0 4px 14px ${tab.color}30` : 'none',
                  }}>
                    {tab.label} ({tab.count})
                  </button>
                );
              })}
            </div>

            {/* ── Lane Cards ── */}
            {filteredTrends.map((t, i) => {
              const chartData = (t.data || []).filter(d => d.cost_per_tonne !== null && d.cost_per_tonne > 0);
              const hasValidChart = chartData.length >= 2;
              const primaryCategory = (t.categories || [])[0] || 'stable';
              const badge = CATEGORY_BADGE[primaryCategory] || CATEGORY_BADGE.stable;
              const tabBorderColor = trendSubTab === 'critical' ? '#dc2626'
                : trendSubTab === 'warning' ? '#d97706' : '#10b981';

              return (
                <div key={i} className="chart-card" style={{ borderLeft: `4px solid ${tabBorderColor}` }}>
                  {/* Header */}
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.5rem' }}>
                    <div style={{ flex: 1 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '0.25rem' }}>
                        <span style={{ fontSize: '1rem', fontWeight: 800, color: '#0f172a' }}>{t.lane_name}</span>
                        {/* Category badges */}
                        {(t.categories || []).filter(c => c !== 'stable').map((cat, j) => {
                          const b = CATEGORY_BADGE[cat] || CATEGORY_BADGE.stable;
                          return (
                            <span key={j} style={{
                              fontSize: '0.65rem', fontWeight: 700, padding: '2px 8px', borderRadius: '999px',
                              background: b.bg, color: b.color, border: `1px solid ${b.color}30`,
                            }}>{b.label}</span>
                          );
                        })}
                        {t.tab_reason && (
                          <span style={{
                            fontSize: '0.62rem', fontWeight: 600, padding: '2px 6px', borderRadius: '4px',
                            background: '#f1f5f9', color: '#64748b',
                          }}>{t.tab_reason}</span>
                        )}
                      </div>
                      <div style={{ fontSize: '0.78rem', color: '#64748b' }}>
                        {t.total_shipments} shipments · Freight: {fmt(t.total_freight)} · 
                        Margin: <span style={{ fontWeight: 700, color: t.margin_pct >= 0 ? '#059669' : '#dc2626' }}>{t.margin_pct}%</span>
                      </div>
                    </div>
                    {/* KPI pills */}
                    <div style={{ display: 'flex', gap: '0.5rem', flexShrink: 0 }}>
                      <div style={{
                        padding: '0.35rem 0.75rem', borderRadius: '10px', textAlign: 'center',
                        background: t.pct_change > 5 ? 'rgba(220,38,38,0.08)' : t.pct_change < -5 ? 'rgba(16,185,129,0.08)' : 'rgba(59,130,246,0.06)',
                      }}>
                        <div style={{ fontSize: '0.6rem', color: '#94a3b8', fontWeight: 700, textTransform: 'uppercase' }}>Cost Δ</div>
                        <div style={{
                          fontSize: '0.85rem', fontWeight: 800,
                          color: t.pct_change > 5 ? '#dc2626' : t.pct_change < -5 ? '#059669' : '#3b82f6',
                        }}>{t.pct_change > 0 ? '+' : ''}{t.pct_change}%</div>
                      </div>
                      <div style={{
                        padding: '0.35rem 0.75rem', borderRadius: '10px', textAlign: 'center',
                        background: t.total_profit >= 0 ? 'rgba(16,185,129,0.08)' : 'rgba(220,38,38,0.08)',
                      }}>
                        <div style={{ fontSize: '0.6rem', color: '#94a3b8', fontWeight: 700, textTransform: 'uppercase' }}>Profit</div>
                        <div style={{
                          fontSize: '0.85rem', fontWeight: 800,
                          color: t.total_profit >= 0 ? '#059669' : '#dc2626',
                        }}>{fmt(t.total_profit)}</div>
                      </div>
                    </div>
                  </div>

                  {/* Insights first (decision-focused) */}
                  {t.insights?.length > 0 && (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem', marginBottom: '0.75rem' }}>
                      {t.insights.slice(0, 3).map((ins, j) => {
                        const insIcon = ins.type === 'success' ? '✅' : ins.type === 'danger' ? '🚨' : ins.type === 'warning' ? '⚠️' : 'ℹ️';
                        const insBg = ins.type === 'success' ? 'rgba(16,185,129,0.05)'
                          : ins.type === 'danger' ? 'rgba(244,63,94,0.05)'
                          : ins.type === 'warning' ? 'rgba(245,158,11,0.05)' : 'rgba(59,130,246,0.04)';
                        const insBorder = ins.type === 'success' ? '#10b981'
                          : ins.type === 'danger' ? '#f43f5e'
                          : ins.type === 'warning' ? '#f59e0b' : '#94a3b8';
                        return (
                          <div key={j} style={{
                            fontSize: '0.8rem', padding: '0.5rem 0.75rem', background: insBg,
                            borderRadius: '8px', borderLeft: `3px solid ${insBorder}`,
                            color: '#334155', lineHeight: 1.5,
                          }}>
                            {insIcon} {ins.text}
                          </div>
                        );
                      })}
                    </div>
                  )}

                  {/* Chart */}
                  {hasValidChart ? (
                    <ResponsiveContainer width="100%" height={200}>
                      <LineChart data={chartData}>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(0,0,0,0.05)" />
                        <XAxis dataKey="month" tick={{ fontSize: 11, fill: '#94a3b8' }} />
                        <YAxis yAxisId="left" tick={{ fontSize: 11, fill: '#94a3b8' }} />
                        <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11, fill: '#94a3b8' }} />
                        <Tooltip
                          contentStyle={{ background: 'rgba(255,255,255,0.97)', border: '1px solid rgba(0,0,0,0.08)', borderRadius: '10px', fontSize: '0.82rem' }}
                          formatter={(value, name) => {
                            if (name === 'Cost/Tonne') return [`₹${Number(value).toLocaleString('en-IN')}`, name];
                            if (name === 'Profit') return [`₹${Number(value).toLocaleString('en-IN')}`, name];
                            return [value, name];
                          }}
                        />
                        <Legend wrapperStyle={{ fontSize: '0.72rem' }} />
                        <Line yAxisId="left" type="monotone" dataKey="cost_per_tonne" name="Cost/Tonne" stroke="#3b82f6" strokeWidth={2.5} dot={{ r: 4, fill: '#3b82f6' }} activeDot={{ r: 6 }} />
                        <Line yAxisId="right" type="monotone" dataKey="profit" name="Profit" stroke="#10b981" strokeWidth={2} dot={{ r: 3, fill: '#10b981' }} />
                      </LineChart>
                    </ResponsiveContainer>
                  ) : (
                    <div style={{ padding: '1.5rem', textAlign: 'center', background: 'rgba(148,163,184,0.04)', borderRadius: '8px' }}>
                      <div style={{ fontSize: '0.85rem', color: '#94a3b8' }}>⚠️ Insufficient data points for chart — only {t.quality?.valid_points || 0} valid</div>
                    </div>
                  )}

                  {/* ── Detailed Graph Explanation ── */}
                  {(() => {
                    const avgCPT = chartData.length > 0 ? Math.round(chartData.reduce((s, d) => s + (d.cost_per_tonne || 0), 0) / chartData.length) : 0;
                    const totalShip = chartData.reduce((s, d) => s + (d.shipments || 0), 0);
                    const totalFr = chartData.reduce((s, d) => s + (d.freight || 0), 0);
                    const totalPr = chartData.reduce((s, d) => s + (d.profit || 0), 0);
                    const totalWt = chartData.reduce((s, d) => s + (d.total_weight || 0), 0);
                    const firstCPT = chartData.length > 0 ? chartData[0].cost_per_tonne : 0;
                    const lastCPT = chartData.length > 0 ? chartData[chartData.length - 1].cost_per_tonne : 0;
                    const cptDelta = lastCPT - firstCPT;
                    const firstProfit = chartData.length > 0 ? chartData[0].profit : 0;
                    const lastProfit = chartData.length > 0 ? chartData[chartData.length - 1].profit : 0;

                    return (
                      <div style={{ marginTop: '0.75rem', background: '#f8fafc', borderRadius: '10px', border: '1px solid #e2e8f0', overflow: 'hidden' }}>
                        {/* Section Header */}
                        <div style={{ padding: '0.6rem 1rem', background: '#f1f5f9', borderBottom: '1px solid #e2e8f0', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          <span style={{ fontSize: '0.85rem' }}>📋</span>
                          <span style={{ fontWeight: 700, fontSize: '0.82rem', color: '#334155' }}>Graph Details — Monthly Breakdown</span>
                        </div>

                        {/* Monthly Data Table */}
                        {chartData.length > 0 && (
                          <div style={{ overflowX: 'auto' }}>
                            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.78rem' }}>
                              <thead>
                                <tr style={{ background: '#f1f5f9' }}>
                                  {['Month', 'Cost/Tonne', 'Profit', 'Freight', 'Shipments', 'Weight (MT)', 'Margin %'].map(h => (
                                    <th key={h} style={{ padding: '0.5rem 0.75rem', textAlign: 'left', fontWeight: 700, color: '#475569', borderBottom: '1px solid #e2e8f0', whiteSpace: 'nowrap' }}>{h}</th>
                                  ))}
                                </tr>
                              </thead>
                              <tbody>
                                {chartData.map((d, k) => (
                                  <tr key={k} style={{ borderBottom: '1px solid #f1f5f9' }}
                                    onMouseEnter={e => e.currentTarget.style.background = '#f0f9ff'}
                                    onMouseLeave={e => e.currentTarget.style.background = ''}
                                  >
                                    <td style={{ padding: '0.45rem 0.75rem', fontWeight: 600, color: '#0f172a' }}>{d.month}</td>
                                    <td style={{ padding: '0.45rem 0.75rem', color: '#3b82f6', fontWeight: 600 }}>₹{(d.cost_per_tonne || 0).toLocaleString('en-IN')}</td>
                                    <td style={{ padding: '0.45rem 0.75rem', color: d.profit >= 0 ? '#059669' : '#dc2626', fontWeight: 600 }}>{fmt(d.profit || 0)}</td>
                                    <td style={{ padding: '0.45rem 0.75rem', color: '#475569' }}>{fmt(d.freight || 0)}</td>
                                    <td style={{ padding: '0.45rem 0.75rem', color: '#475569' }}>{d.shipments || 0}</td>
                                    <td style={{ padding: '0.45rem 0.75rem', color: '#475569' }}>{(d.total_weight || 0).toLocaleString('en-IN')}</td>
                                    <td style={{ padding: '0.45rem 0.75rem', fontWeight: 600, color: (d.margin_pct || 0) >= 0 ? '#059669' : '#dc2626' }}>{d.margin_pct != null ? `${d.margin_pct}%` : '—'}</td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        )}

                        {/* Summary Stats Row */}
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '1.5rem', padding: '0.75rem 1rem', borderTop: '1px solid #e2e8f0', background: '#fff' }}>
                          {[
                            { label: 'Period', value: chartData.length > 0 ? `${chartData[0].month} → ${chartData[chartData.length - 1].month}` : '—' },
                            { label: 'Avg Cost/T', value: `₹${avgCPT.toLocaleString('en-IN')}` },
                            { label: 'Cost Δ', value: `₹${Math.abs(Math.round(cptDelta)).toLocaleString('en-IN')} ${cptDelta > 0 ? '↑' : cptDelta < 0 ? '↓' : '→'}`, color: cptDelta > 0 ? '#dc2626' : cptDelta < 0 ? '#059669' : '#64748b' },
                            { label: 'Total Shipments', value: totalShip },
                            { label: 'Total Freight', value: fmt(totalFr) },
                            { label: 'Net Profit', value: fmt(totalPr), color: totalPr >= 0 ? '#059669' : '#dc2626' },
                            { label: 'Total Weight', value: `${totalWt.toLocaleString('en-IN')} MT` },
                          ].map((s, k) => (
                            <div key={k}>
                              <div style={{ fontSize: '0.6rem', color: '#94a3b8', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em' }}>{s.label}</div>
                              <div style={{ fontSize: '0.85rem', fontWeight: 700, color: s.color || '#0f172a' }}>{s.value}</div>
                            </div>
                          ))}
                        </div>

                        {/* Trend Explanation */}
                        <div style={{ padding: '0.75rem 1rem', borderTop: '1px solid #e2e8f0', fontSize: '0.8rem', color: '#334155', lineHeight: 1.6 }}>
                          <div style={{ fontWeight: 700, marginBottom: '0.3rem', color: '#0f172a' }}>📊 What this graph shows:</div>
                          <div style={{ marginBottom: '0.4rem' }}>
                            The <span style={{ color: '#3b82f6', fontWeight: 600 }}>blue line (Cost/Tonne)</span> represents the transportation cost per metric tonne for this route each month.  
                            The <span style={{ color: '#10b981', fontWeight: 600 }}>green line (Profit)</span> shows the monthly profit (freight revenue minus all costs).
                          </div>
                          {chartData.length >= 2 && (
                            <div style={{ marginBottom: '0.4rem' }}>
                              • Cost/Tonne moved from <strong>₹{firstCPT?.toLocaleString('en-IN')}</strong> to <strong>₹{lastCPT?.toLocaleString('en-IN')}</strong>
                              {' '}({cptDelta > 0 ? `an increase of ₹${Math.round(cptDelta).toLocaleString('en-IN')}` : cptDelta < 0 ? `a decrease of ₹${Math.abs(Math.round(cptDelta)).toLocaleString('en-IN')}` : 'no change'}).
                              <br />
                              • Profit moved from <strong>{fmt(firstProfit)}</strong> to <strong>{fmt(lastProfit)}</strong> over {chartData.length} months.
                            </div>
                          )}
                          <div style={{ fontWeight: 700, marginTop: '0.5rem', marginBottom: '0.3rem', color: '#0f172a' }}>💡 Recommendation:</div>
                          <div style={{ color: '#475569' }}>
                            {t.tab === 'critical' && t.total_profit < 0
                              ? `This route is losing ₹${Math.abs(Math.round(t.total_profit)).toLocaleString('en-IN')} in total. Review freight rates, renegotiate with transporters, or consider suspending operations on this lane until rates are corrected.`
                              : t.tab === 'critical'
                              ? 'Abnormal cost patterns detected. Verify the raw data for this route and investigate any unusual operational expenses or data entry errors.'
                              : t.tab === 'warning' && t.pct_change > 5
                              ? `Cost per tonne has risen by ${t.pct_change}%. Explore alternate transporters, consolidate loads, or renegotiate contract terms to contain costs.`
                              : t.tab === 'warning'
                              ? 'Profit margins are declining. Analyze deductions, detention charges, and freight rate trends to identify the root cause.'
                              : `This lane is performing well with ${t.margin_pct}% margin. Maintain current operations and consider increasing shipment volume to maximize returns.`
                            }
                          </div>
                        </div>
                      </div>
                    );
                  })()}
                </div>
              );
            })}

            {/* Empty state */}
            {filteredTrends.length === 0 && (
              <div style={{ padding: '3rem', textAlign: 'center', color: '#94a3b8' }}>
                <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>
                  {trendSubTab === 'critical' ? '✅' : trendSubTab === 'warning' ? '✅' : '📊'}
                </div>
                <div style={{ fontWeight: 600, marginBottom: '0.25rem' }}>
                  {trendSubTab === 'good'
                    ? 'No top-performing lanes found in this dataset'
                    : `No ${trendSubTab} issues detected — all routes are operating within normal parameters`}
                </div>
              </div>
            )}
          </div>
        );
      })()}

      {/* ──── ALERTS TAB (Consolidated) ──── */}
      {activeTab === 'alerts' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          {alerts.map((a, i) => {
            const c = ALERT_COLOR[a.level] || ALERT_COLOR.yellow;
            const routeCount = a.routes?.length || 0;
            return (
              <div key={i} style={{
                background: '#fff', border: `1px solid ${c.border}`, borderRadius: '16px',
                overflow: 'hidden', boxShadow: '0 2px 12px rgba(0,0,0,0.04)',
              }}>
                {/* Card Header */}
                <div style={{
                  background: c.bg, padding: '1.25rem 1.5rem',
                  borderBottom: `1px solid ${c.border}`,
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                }}>
                  <div>
                    <div style={{ fontWeight: 800, color: c.text, fontSize: '1.05rem', marginBottom: '0.25rem' }}>{a.title}</div>
                    <div style={{ fontSize: '0.85rem', color: '#475569', lineHeight: 1.5 }}>{a.insight}</div>
                  </div>
                  <div style={{
                    background: c.border, color: '#fff', fontWeight: 800, fontSize: '1.1rem',
                    width: '42px', height: '42px', borderRadius: '12px', display: 'flex',
                    alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                  }}>{routeCount}</div>
                </div>

                {/* Routes Table */}
                <div style={{ padding: '0.5rem 1rem 1rem' }}>
                  {renderAlertRouteTable(a)}
                </div>

                {/* Recommendation */}
                <div style={{
                  margin: '0 1rem 1rem', fontSize: '0.82rem', color: '#475569',
                  background: c.bg, padding: '0.75rem 1rem', borderRadius: '10px',
                  borderLeft: `3px solid ${c.border}`,
                }}>
                  {a.recommendation}
                </div>
              </div>
            );
          })}
          {alerts.length === 0 && <div style={{ padding: '3rem', textAlign: 'center', color: '#94a3b8' }}>✅ No alerts — all lanes operating within expected parameters.</div>}
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
                <p style={{ margin: '0.25rem 0 0', color: '#64748b', fontSize: '0.82rem' }}>{drilldown.total_shipments} shipments · Margin: {drilldown.margin_pct}%</p>
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
