/**
 * CustomerPanel.jsx  —  Light Theme (matches Manager Dashboard)
 */
import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { fetchShipments, downloadInvoiceAction } from '../api';

// ── Design tokens ─────────────────────────────────────────────────────────────
const C = {
  bg:       '#f8fafc',
  card:     '#ffffff',
  border:   '#e2e8f0',
  text:     '#0f172a',
  sub:      '#475569',
  muted:    '#94a3b8',
  blue:     '#3b82f6',
  blueGlow: 'rgba(59,130,246,0.10)',
  green:    '#10b981',
  greenGlow:'rgba(16,185,129,0.11)',
  rose:     '#f43f5e',
  roseGlow: 'rgba(244,63,94,0.10)',
  amber:    '#f59e0b',
  amberGlow:'rgba(245,158,11,0.10)',
  teal:     '#0d9488',
  tealGlow: 'rgba(13,148,136,0.10)',
  violet:   '#8b5cf6',
  violetGlow:'rgba(139,92,246,0.10)',
  shadow:   '0 1px 3px rgba(0,0,0,0.05), 0 1px 2px rgba(0,0,0,0.03)',
  shadowMd: '0 4px 12px rgba(0,0,0,0.07)',
};

const STATUS_STEPS = [
  { key: 'Dispatched', icon: '📦', label: 'Picked Up' },
  { key: 'In Transit', icon: '🚛', label: 'In Transit' },
  { key: 'Delivered',  icon: '✅', label: 'Delivered' },
];
const STEP_ORDER = ['Dispatched', 'In Transit', 'Delivered'];

function inferStatus(s) {
  if (s.delivery_date) return 'Delivered';
  if (s.dispatch_date) return 'In Transit';
  return 'Dispatched';
}

export default function CustomerPanel() {
  const { user, logout }            = useAuth();
  const [shipments, setShipments]   = useState([]);
  const [loading, setLoading]       = useState(true);
  const [error, setError]           = useState(null);
  const [search, setSearch]         = useState('');
  const [selected, setSelected]     = useState(null);

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const res = await fetchShipments({ page_size: 200 });
      setShipments(res.results || []);
    } catch (e) { setError(e.message); }
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const filtered = shipments.filter(s =>
    !search ||
    s.shipment_id?.toLowerCase().includes(search.toLowerCase()) ||
    s.consignee_name?.toLowerCase().includes(search.toLowerCase())
  );

  const stats = {
    total:     shipments.length,
    delivered: shipments.filter(s => !!s.delivery_date).length,
    inTransit: shipments.filter(s => s.dispatch_date && !s.delivery_date).length,
    delayed:   shipments.filter(s => !s.is_on_time && !s.delivery_date).length,
  };

  return (
    <div style={{ minHeight: '100vh', background: C.bg, fontFamily: "'Inter','Segoe UI',sans-serif" }}>

      {/* ── Header ────────────────────────────────────────────────────── */}
      <header style={{
        background: C.card,
        borderBottom: `1px solid ${C.border}`,
        padding: '0.9rem 2rem',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        position: 'sticky', top: 0, zIndex: 100,
        boxShadow: C.shadow,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <img src="/manncj.png" alt="CJ Darcl"
            onError={e => { e.currentTarget.style.display = 'none'; }}
            style={{ height: '40px', objectFit: 'contain' }} />
          <div style={{ width: '1px', height: '32px', background: C.border }} />
          <div>
            <div style={{ fontWeight: 800, fontSize: '1.05rem', color: C.text }}>Shipment Tracker</div>
            <div style={{ fontSize: '0.72rem', color: C.muted }}>
              {user?.full_name || user?.username} · CJ Darcl Jamshedpur
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          {/* Role badge */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', padding: '0.3rem 0.75rem', background: C.violetGlow, border: `1px solid ${C.violet}30`, borderRadius: '999px' }}>
            <span style={{ fontSize: '0.85rem' }}>👤</span>
            <span style={{ fontSize: '0.68rem', fontWeight: 700, color: C.violet, letterSpacing: '0.06em' }}>CUSTOMER</span>
          </div>
          <button id="customer-logout-btn" onClick={logout} style={ghostBtn}>Sign Out</button>
        </div>
      </header>

      <div style={{ maxWidth: '1100px', margin: '0 auto', padding: '1.75rem 2rem' }}>

        {/* ── Welcome banner ───────────────────────────────────────────── */}
        <div style={{
          background: `linear-gradient(135deg, ${C.violetGlow}, ${C.tealGlow})`,
          border: `1px solid ${C.violet}20`,
          borderRadius: '14px', padding: '1.5rem 2rem',
          marginBottom: '1.5rem',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem',
        }}>
          <div>
            <div style={{ fontSize: '1.3rem', fontWeight: 800, color: C.text }}>
              Welcome, {user?.full_name || user?.username}
            </div>
            <div style={{ color: C.sub, fontSize: '0.85rem', marginTop: '0.3rem' }}>
              Track your shipments, check delivery status, and download invoices.
            </div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: '2.2rem', fontWeight: 800, color: C.violet, lineHeight: 1 }}>{stats.total}</div>
            <div style={{ fontSize: '0.72rem', color: C.muted, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em' }}>Total Shipments</div>
          </div>
        </div>

        {/* ── Stat strip ───────────────────────────────────────────────── */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(190px, 1fr))', gap: '1rem', marginBottom: '1.5rem' }}>
          {[
            { icon: '✅', label: 'Delivered',  value: stats.delivered, accent: C.green,  bg: C.greenGlow  },
            { icon: '🚛', label: 'In Transit', value: stats.inTransit, accent: C.teal,   bg: C.tealGlow   },
            { icon: '⚠️', label: 'Delayed',    value: stats.delayed,   accent: C.rose,   bg: C.roseGlow   },
          ].map(({ icon, label, value, accent, bg }) => (
            <div key={label} style={{
              background: C.card, border: `1px solid ${C.border}`,
              borderRadius: '12px', padding: '1.1rem 1.25rem',
              borderTop: `3px solid ${accent}`, boxShadow: C.shadow,
            }}>
              <div style={{ width: '38px', height: '38px', borderRadius: '8px', background: bg, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1.1rem', marginBottom: '0.6rem' }}>{icon}</div>
              <div style={{ fontSize: '1.75rem', fontWeight: 800, color: accent, lineHeight: 1 }}>{value}</div>
              <div style={{ fontSize: '0.72rem', color: C.muted, marginTop: '0.25rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em' }}>{label}</div>
            </div>
          ))}
        </div>

        {/* ── CN Search ────────────────────────────────────────────────── */}
        <div style={{ position: 'relative', marginBottom: '1.25rem' }}>
          <span style={{ position: 'absolute', left: '0.9rem', top: '50%', transform: 'translateY(-50%)', color: C.muted, pointerEvents: 'none' }}>🔍</span>
          <input
            id="customer-search"
            placeholder="Enter CN No. to track your shipment…"
            value={search}
            onChange={e => setSearch(e.target.value)}
            style={{
              width: '100%', padding: '0.75rem 1rem 0.75rem 2.5rem',
              background: C.card, border: `1px solid ${search ? C.teal : C.border}`,
              borderRadius: '10px', color: C.text, fontSize: '0.95rem',
              outline: 'none', boxSizing: 'border-box',
              fontFamily: 'inherit',
              boxShadow: search ? `0 0 0 3px ${C.tealGlow}` : 'none',
              transition: 'border-color 0.2s, box-shadow 0.2s',
            }}
          />
        </div>

        {/* Error */}
        {error && (
          <div style={{ background: '#FEF2F2', border: `1px solid ${C.rose}30`, borderRadius: '8px', padding: '0.75rem 1rem', color: '#B91C1C', marginBottom: '1rem', fontSize: '0.85rem' }}>
            ⚠️ {error}
          </div>
        )}

        {/* ── Shipment list ─────────────────────────────────────────────── */}
        {loading ? (
          <div style={{ textAlign: 'center', padding: '4rem', color: C.muted }}>
            <div style={{ fontSize: '2rem', marginBottom: '0.75rem' }}>⏳</div>
            <div>Loading your shipments…</div>
          </div>
        ) : filtered.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '4rem', background: C.card, borderRadius: '12px', border: `1px solid ${C.border}` }}>
            <div style={{ fontSize: '2.5rem', marginBottom: '0.75rem' }}>📭</div>
            <div style={{ fontWeight: 700, color: C.text }}>
              {search ? `No results for "${search}"` : 'No shipments found'}
            </div>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
            {filtered.map(s => (
              <CustomerShipmentCard
                key={s.id}
                s={s}
                expanded={selected === s.id}
                onToggle={() => setSelected(selected === s.id ? null : s.id)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}


// ─── Shipment card ────────────────────────────────────────────────────────────
function CustomerShipmentCard({ s, expanded, onToggle }) {
  const status      = inferStatus(s);
  const statusColor = status === 'Delivered' ? C.green : status === 'In Transit' ? C.teal : C.amber;
  const [dlLoading, setDlLoading] = useState(false);
  const podDone     = s.pod_status === 'Uploaded';

  const handleDownload = async (e) => {
    e.preventDefault(); e.stopPropagation();
    setDlLoading(true);
    try { await downloadInvoiceAction(s.shipment_id); } 
    catch (err) { alert(err.message); }
    setDlLoading(false);
  };

  return (
    <div style={{
      background: C.card,
      border: `1px solid ${expanded ? C.teal : C.border}`,
      borderRadius: '12px',
      overflow: 'hidden',
      boxShadow: expanded ? C.shadowMd : C.shadow,
      transition: 'all 0.2s',
    }}>
      {/* Header row (always visible) */}
      <div
        onClick={onToggle}
        style={{
          padding: '1rem 1.25rem', cursor: 'pointer',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          gap: '1rem', flexWrap: 'wrap',
          background: expanded ? `${C.teal}05` : C.card,
        }}
      >
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', flex: 1 }}>
          {/* Status icon */}
          <div style={{
            width: '42px', height: '42px',
            background: `${statusColor}12`,
            border: `1px solid ${statusColor}30`,
            borderRadius: '10px',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: '1.25rem', flexShrink: 0,
          }}>
            {status === 'Delivered' ? '✅' : status === 'In Transit' ? '🚛' : '📦'}
          </div>
          <div>
            <div style={{ fontWeight: 800, fontSize: '0.95rem', fontFamily: 'monospace', color: C.text }}>
              {s.shipment_id}
            </div>
            <div style={{ fontSize: '0.78rem', color: C.muted, marginTop: '0.1rem' }}>
              {s.origin || '—'} → {s.destination || '—'}
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexWrap: 'wrap' }}>
          <Pill color={statusColor}>{status}</Pill>
          {!s.is_on_time && status !== 'Delivered' && (
            <Pill color={C.rose}>⚠️ Delayed {s.delay_days || 0}d</Pill>
          )}
          {podDone && <Pill color={C.green}>POD ✓</Pill>}
          <span style={{ color: C.muted, fontSize: '0.9rem', marginLeft: '0.25rem' }}>{expanded ? '▲' : '▼'}</span>
        </div>
      </div>

      {/* Expanded detail */}
      {expanded && (
        <div style={{ borderTop: `1px solid ${C.border}`, padding: '1.25rem' }}>

          {/* Delivery Timeline */}
          <div style={{ marginBottom: '1.25rem' }}>
            <div style={{ fontSize: '0.68rem', color: C.muted, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '1rem' }}>
              Delivery Timeline
            </div>
            <div style={{ display: 'flex', alignItems: 'center' }}>
              {STATUS_STEPS.map((step, i) => {
                const reached = STEP_ORDER.indexOf(status) >= i;
                const active  = step.key === status;
                return (
                  <div key={step.key} style={{ display: 'flex', alignItems: 'center', flex: i < STATUS_STEPS.length - 1 ? 1 : 0 }}>
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.4rem' }}>
                      <div style={{
                        width: '40px', height: '40px', borderRadius: '50%',
                        background: reached ? `${C.teal}12` : C.bg,
                        border: `2px solid ${reached ? C.teal : C.border}`,
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        fontSize: '1rem',
                        boxShadow: active ? `0 0 0 4px ${C.teal}18` : 'none',
                        transition: 'all 0.2s',
                      }}>
                        {step.icon}
                      </div>
                      <div style={{ fontSize: '0.67rem', fontWeight: reached ? 700 : 500, color: reached ? C.teal : C.muted, whiteSpace: 'nowrap' }}>
                        {step.label}
                      </div>
                    </div>
                    {i < STATUS_STEPS.length - 1 && (
                      <div style={{
                        flex: 1, height: '2px', margin: '0 6px', marginBottom: '18px',
                        background: STEP_ORDER.indexOf(status) > i ? C.teal : C.border,
                        transition: 'background 0.3s',
                        borderRadius: '1px',
                      }} />
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Detail grid */}
          <div style={{
            display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(145px, 1fr))',
            gap: '0.75rem 1.5rem', marginBottom: '1.25rem',
            padding: '1rem', background: C.bg, borderRadius: '8px', border: `1px solid ${C.border}`,
          }}>
            {[
              ['📅 Dispatch',   s.dispatch_date || '—'],
              ['📅 Delivery',   s.delivery_date || 'Pending'],
              ['⚖️ Weight',     s.net_weight ? `${s.net_weight} MT` : '—'],
              ['📦 Material',   s.material_type || '—'],
              ['🚗 Vehicle',    s.vehicle_no || '—'],
              ['📄 POD Status', s.pod_status || 'Pending'],
              ['🧾 Billing',    s.billing_status || 'Pending'],
            ].map(([label, value]) => (
              <div key={label}>
                <div style={{ fontSize: '0.67rem', color: C.muted, textTransform: 'uppercase', letterSpacing: '0.04em', fontWeight: 600 }}>{label}</div>
                <div style={{ fontSize: '0.88rem', color: C.text, fontWeight: 600, marginTop: '0.15rem' }}>{value}</div>
              </div>
            ))}
          </div>

          {/* Invoice button */}
          <button
            onClick={handleDownload}
            disabled={dlLoading}
            style={{
              display: 'inline-flex', alignItems: 'center', gap: '0.4rem',
              padding: '0.55rem 1.25rem',
              background: dlLoading ? C.bg : `${C.teal}10`, 
              border: `1px solid ${C.teal}35`,
              borderRadius: '8px', color: C.teal,
              fontSize: '0.85rem', fontWeight: 700, cursor: dlLoading ? 'not-allowed' : 'pointer',
              transition: 'all 0.2s',
            }}
          >
            {dlLoading ? '⏳ Generating...' : '📄 Download Invoice'}
          </button>
        </div>
      )}
    </div>
  );
}


// ─── Shared ───────────────────────────────────────────────────────────────────
function Pill({ color, children }) {
  return (
    <span style={{
      padding: '0.22rem 0.7rem', borderRadius: '999px',
      fontSize: '0.72rem', fontWeight: 700,
      background: `${color}14`, color, border: `1px solid ${color}30`,
    }}>
      {children}
    </span>
  );
}

const ghostBtn = {
  padding: '0.45rem 1rem', background: 'transparent',
  border: '1px solid #e2e8f0', borderRadius: '7px',
  color: '#475569', cursor: 'pointer', fontSize: '0.82rem',
  fontWeight: 600, fontFamily: 'inherit',
};
