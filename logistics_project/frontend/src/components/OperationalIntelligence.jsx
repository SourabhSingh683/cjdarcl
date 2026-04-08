import React, { useState, useEffect } from 'react';
import { fetchOperationalIntelligence } from '../api';

export default function OperationalIntelligence({ filters }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    fetchOperationalIntelligence(filters)
      .then((res) => {
        if (isMounted) {
          if (res.error) setError(res.error);
          else {
            setData(res);
            setError(null);
          }
          setLoading(false);
        }
      })
      .catch((err) => {
        if (isMounted) {
          setError(err.message);
          setLoading(false);
        }
      });
    return () => { isMounted = false; };
  }, [filters]);

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '400px', flexDirection: 'column', gap: '1rem', color: 'var(--text-muted)' }}>
        <div className="spinner" style={{ width: '30px', height: '30px', border: '3px solid rgba(13,148,136,0.3)', borderTopColor: '#0D9488', borderRadius: '50%', animation: 'spin 1s linear infinite' }} />
        <span>Compiling Operational Intelligence...</span>
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  if (error) {
    return (
      <div className="empty-state">
        <div className="empty-icon">⚠️</div>
        <h2>Analysis Failed</h2>
        <p style={{ color: 'var(--text-muted)' }}>{error}</p>
      </div>
    );
  }

  if (!data) return null;

  const { alerts, transporters, routes, best_route, worst_route, billing_sla } = data;

  const getAlertColor = (level) => {
    switch(level) {
      case 'red': return { bg: '#fef2f2', border: '#fecaca', text: '#ef4444', icon: '🚨' };
      case 'yellow': return { bg: '#fffbeb', border: '#fde68a', text: '#f59e0b', icon: '⚠️' };
      case 'green': return { bg: '#ecfdf5', border: '#a7f3d0', text: '#10b981', icon: '✅' };
      default: return { bg: '#f8fafc', border: '#e2e8f0', text: '#64748b', icon: '💡' };
    }
  };

  return (
    <div className="analytics-view fade-in" style={{ paddingBottom: '2rem' }}>
      <div style={{ marginBottom: '2rem' }}>
        <h2 style={{ fontSize: '1.5rem', marginBottom: '0.5rem', color: 'var(--text-primary)' }}>Operational Intelligence & Alerts</h2>
        <p style={{ color: 'var(--text-muted)' }}>Actionable supply chain insights based on historical shipment data</p>
      </div>

      {/* 🔴 SECTION 1: MANAGEMENT ALERTS */}
      <h3 style={{ fontSize: '1.1rem', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <span>🎯</span> Priority Management Alerts
      </h3>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1rem', marginBottom: '2.5rem' }}>
        {alerts.length > 0 ? alerts.map((alert, idx) => {
          const style = getAlertColor(alert.level);
          return (
            <div key={idx} style={{ 
              background: style.bg, border: `1px solid ${style.border}`, borderRadius: '12px', padding: '1.25rem',
              display: 'flex', flexDirection: 'column', gap: '0.75rem', boxShadow: '0 2px 5px rgba(0,0,0,0.02)'
            }}>
              <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', color: style.text, fontWeight: 700, fontSize: '0.95rem' }}>
                <span>{style.icon}</span> <span>{alert.title}</span>
              </div>
              <p style={{ fontSize: '0.9rem', color: '#334155', fontWeight: 500, lineHeight: 1.4 }}>{alert.insight}</p>
              <div style={{ marginTop: 'auto', fontSize: '0.8rem', color: '#475569', background: 'rgba(255,255,255,0.5)', padding: '0.5rem 0.75rem', borderRadius: '6px' }}>
                {alert.recommendation}
              </div>
            </div>
          );
        }) : (
          <div style={{ gridColumn: '1 / -1', padding: '2rem', textAlign: 'center', background: 'rgba(16,185,129,0.05)', border: '1px dashed rgba(16,185,129,0.3)', borderRadius: '12px', color: '#059669' }}>
            🎉 No critical alerts! Operations are looking solid.
          </div>
        )}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: '2rem' }}>
        
        {/* 🟡 SECTION 2: TRANSPORTER PERFORMANCE */}
        <div className="chart-card" style={{ marginBottom: 0 }}>
          <div className="chart-header">
            <div>
              <div className="chart-title">🚚 Transporter Analytics</div>
              <div className="chart-subtitle">Ranked by historical delay percentage</div>
            </div>
          </div>
          <div className="history-table-wrap" style={{ maxHeight: '400px', overflowY: 'auto' }}>
            <table className="history-table">
              <thead style={{ position: 'sticky', top: 0, zIndex: 1, backgroundColor: 'var(--bg-glass)' }}>
                <tr>
                  <th>Transporter Name</th>
                  <th>Shipments</th>
                  <th>Delayed</th>
                  <th>Delay %</th>
                  <th>Avg Delay</th>
                </tr>
              </thead>
              <tbody>
                {transporters.map((t, idx) => {
                  const isBest = idx === transporters.length - 1 && t.delay_pct < 20 && transporters.length > 1;
                  const isWorst = idx === 0 && t.delay_pct > 20 && transporters.length > 1;
                  return (
                    <tr key={idx} style={{ 
                      background: isWorst ? 'rgba(244,63,94,0.05)' : isBest ? 'rgba(16,185,129,0.05)' : 'transparent' 
                    }}>
                      <td style={{ fontWeight: 600 }}>{t.transporter_name}</td>
                      <td>{t.total_shipments}</td>
                      <td>{t.delayed_shipments}</td>
                      <td style={{ fontWeight: 700, color: isWorst ? '#e11d48' : isBest ? '#059669' : 'inherit' }}>
                        {t.delay_pct}%
                      </td>
                      <td>{t.avg_delay_days > 0 ? `${t.avg_delay_days}d` : '-'}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* 🟢 SECTION 3 & 4: ROUTE INTELLIGENCE & SLA IMPACT */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          
          <div className="chart-card">
            <div className="chart-header">
              <div>
                <div className="chart-title">🟣 Billing & SLA Impact</div>
                <div className="chart-subtitle">Financial impact of SLA breaches</div>
              </div>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
              <div style={{ background: 'rgba(139,92,246,0.05)', padding: '1rem', borderRadius: '8px', border: '1px solid rgba(139,92,246,0.2)' }}>
                <div style={{ fontSize: '0.8rem', color: '#6b7280', marginBottom: '0.25rem' }}>Total Billed Freight</div>
                <div style={{ fontSize: '1.4rem', fontWeight: 700, color: '#8b5cf6' }}>₹{(billing_sla.total_billed_freight / 10000000).toFixed(2)} Cr</div>
              </div>
              <div style={{ background: 'rgba(244,63,94,0.05)', padding: '1rem', borderRadius: '8px', border: '1px solid rgba(244,63,94,0.2)' }}>
                <div style={{ fontSize: '0.8rem', color: '#6b7280', marginBottom: '0.25rem' }}>Revenue at Risk (Delayed)</div>
                <div style={{ fontSize: '1.4rem', fontWeight: 700, color: '#e11d48' }}>₹{(billing_sla.revenue_at_risk / 10000000).toFixed(2)} Cr</div>
              </div>
              <div style={{ gridColumn: '1 / -1', background: 'var(--bg-card)', padding: '1rem', borderRadius: '8px', border: '1px solid var(--border-glass)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>Historical SLA Breach Rate</span>
                <span style={{ fontSize: '1.2rem', fontWeight: 700, color: billing_sla.sla_breach_pct > 20 ? '#e11d48' : '#059669' }}>{billing_sla.sla_breach_pct}%</span>
              </div>
            </div>
          </div>

          <div className="chart-card" style={{ flexGrow: 1 }}>
            <div className="chart-header">
              <div>
                <div className="chart-title">📍 Route Intelligence</div>
                <div className="chart-subtitle">Corridor level performance highlights</div>
              </div>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {best_route && (
                <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', background: 'rgba(16,185,129,0.05)', border: '1px solid rgba(16,185,129,0.2)', padding: '1rem', borderRadius: '8px' }}>
                  <div style={{ fontSize: '2rem' }}>🏆</div>
                  <div>
                    <div style={{ fontSize: '0.8rem', color: '#059669', fontWeight: 700, textTransform: 'uppercase', marginBottom: '0.2rem' }}>Best Performing Route</div>
                    <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{best_route.route_name}</div>
                    <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>Only {best_route.delay_pct}% delay across {best_route.total_shipments} shipments</div>
                  </div>
                </div>
              )}
              {worst_route && (
                <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', background: 'rgba(244,63,94,0.05)', border: '1px solid rgba(244,63,94,0.2)', padding: '1rem', borderRadius: '8px' }}>
                  <div style={{ fontSize: '2rem' }}>🚨</div>
                  <div>
                    <div style={{ fontSize: '0.8rem', color: '#e11d48', fontWeight: 700, textTransform: 'uppercase', marginBottom: '0.2rem' }}>Highest Risk Route</div>
                    <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{worst_route.route_name}</div>
                    <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '0.2rem' }}>{worst_route.delay_pct}% delay rate ({worst_route.delayed_shipments} of {worst_route.total_shipments} trips)</div>
                  </div>
                </div>
              )}
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
