/**
 * DriverPanel.jsx  —  Light Theme (matches Manager Dashboard)
 */
import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../context/AuthContext';
import { fetchShipments, uploadPOD, downloadInvoice } from '../api';
import NotificationBell from './NotificationBell';

// ── Design tokens (light, matches index.css) ─────────────────────────────────
const C = {
  bg:       '#f8fafc',
  card:     '#ffffff',
  border:   '#e2e8f0',
  text:     '#0f172a',
  sub:      '#475569',
  muted:    '#94a3b8',
  blue:     '#3b82f6',
  blueGlow: 'rgba(59,130,246,0.12)',
  green:    '#10b981',
  greenGlow:'rgba(16,185,129,0.12)',
  rose:     '#f43f5e',
  roseGlow: 'rgba(244,63,94,0.12)',
  amber:    '#f59e0b',
  amberGlow:'rgba(245,158,11,0.12)',
  teal:     '#0d9488',
  tealGlow: 'rgba(13,148,136,0.12)',
  shadow:   '0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04)',
  shadowMd: '0 4px 12px rgba(0,0,0,0.07)',
};

export default function DriverPanel() {
  const { user, logout }              = useAuth();
  const [shipments, setShipments]     = useState([]);
  const [loading, setLoading]         = useState(true);
  const [error, setError]             = useState(null);
  const [uploadingId, setUploadingId] = useState(null);
  const [uploadMsg, setUploadMsg]     = useState({});
  const [search, setSearch]           = useState('');

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const res = await fetchShipments({ page_size: 200 });
      setShipments(res.results || []);
    } catch (e) { setError(e.message); }
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  async function handlePODUpload(shipmentId, file) {
    setUploadingId(shipmentId);
    setUploadMsg(p => ({ ...p, [shipmentId]: '' }));
    try {
      await uploadPOD(shipmentId, file);
      setUploadMsg(p => ({ ...p, [shipmentId]: '✅ POD uploaded!' }));
      load();
    } catch (e) {
      setUploadMsg(p => ({ ...p, [shipmentId]: `❌ ${e.message}` }));
    }
    setUploadingId(null);
  }

  const filtered = shipments.filter(s =>
    !search ||
    s.shipment_id?.toLowerCase().includes(search.toLowerCase()) ||
    s.vehicle_no?.toLowerCase().includes(search.toLowerCase())
  );

  const stats = {
    total:   shipments.length,
    podDone: shipments.filter(s => s.pod_status === 'Uploaded').length,
    pending: shipments.filter(s => s.pod_status !== 'Uploaded').length,
    delayed: shipments.filter(s => !s.is_on_time).length,
  };

  return (
    <div style={{ minHeight: '100vh', background: C.bg, fontFamily: "'Inter','Segoe UI',sans-serif" }}>

      {/* ── Header ──────────────────────────────────────────────────────── */}
      <header style={{
        background: C.card,
        borderBottom: `1px solid ${C.border}`,
        padding: '0.9rem 2rem',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        position: 'sticky', top: 0, zIndex: 100,
        boxShadow: C.shadow,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          {/* logo */}
          <img src="/manncj.png" alt="CJ Darcl"
            onError={e => { e.currentTarget.style.display='none'; }}
            style={{ height: '40px', objectFit: 'contain' }} />
          <div style={{ width: '1px', height: '32px', background: C.border }} />
          <div>
            <div style={{ fontWeight: 800, fontSize: '1.05rem', color: C.text }}>Driver Panel</div>
            <div style={{ fontSize: '0.72rem', color: C.muted }}>
              {user?.full_name || user?.username}
              {user?.profile?.vehicle_no && (
                <span> · Vehicle: <span style={{ color: C.teal, fontWeight: 700 }}>
                  {user.profile.vehicle_no}
                </span></span>
              )}
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <NotificationBell />
          <RoleBadge color={C.teal} bg={C.tealGlow} label="DRIVER" icon="🚚" />
          <button id="driver-logout-btn" onClick={logout} style={ghostBtn}>Sign Out</button>
        </div>
      </header>

      {/* ── Page body ───────────────────────────────────────────────────── */}
      <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '1.75rem 2rem' }}>

        {/* Stat cards */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginBottom: '1.5rem' }}>
          <StatCard icon="📦" label="Total Assigned" value={stats.total}   accent={C.teal}  bg={C.tealGlow} />
          <StatCard icon="✅" label="POD Uploaded"   value={stats.podDone} accent={C.green} bg={C.greenGlow} />
          <StatCard icon="⏳" label="POD Pending"    value={stats.pending} accent={C.amber} bg={C.amberGlow} />
          <StatCard icon="⚠️" label="Delayed"        value={stats.delayed} accent={C.rose}  bg={C.roseGlow}  />
        </div>

        {/* Search + refresh */}
        <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '1.25rem' }}>
          <div style={{ position: 'relative', flex: 1 }}>
            <span style={{ position: 'absolute', left: '0.85rem', top: '50%', transform: 'translateY(-50%)', color: C.muted, pointerEvents: 'none' }}>🔍</span>
            <input
              placeholder="Search by CN No. or Vehicle No…"
              value={search}
              onChange={e => setSearch(e.target.value)}
              style={{ ...lightInput, paddingLeft: '2.2rem', width: '100%', boxSizing: 'border-box' }}
            />
          </div>
          <button onClick={load} style={outlineBtn(C.teal)}>↻ Refresh</button>
        </div>

        {/* Error */}
        {error && (
          <div style={{ background: '#FEF2F2', border: `1px solid ${C.rose}30`, borderRadius: '8px', padding: '0.75rem 1rem', color: '#B91C1C', marginBottom: '1rem', fontSize: '0.85rem' }}>
            ⚠️ {error}
          </div>
        )}

        {/* Shipment list */}
        {loading ? (
          <LoadingState text="Loading your assigned shipments…" />
        ) : filtered.length === 0 ? (
          <EmptyState icon="🚫" title="No shipments found" sub={search ? `No results for "${search}"` : 'No shipments are assigned to your vehicle'} />
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
            {filtered.map(s => (
              <ShipmentCard
                key={s.id}
                s={s}
                uploading={uploadingId === s.shipment_id}
                msg={uploadMsg[s.shipment_id]}
                onUpload={handlePODUpload}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}


// ─── Shipment Card ────────────────────────────────────────────────────────────
function ShipmentCard({ s, uploading, msg, onUpload }) {
  const podDone     = s.pod_status === 'Uploaded';
  const onTime      = s.is_on_time;
  const statusColor = onTime ? C.green : C.rose;

  function handleFile(e) {
    const file = e.target.files[0];
    if (file) onUpload(s.shipment_id, file);
    e.target.value = '';
  }

  return (
    <div style={{
      background: C.card,
      border: `1px solid ${C.border}`,
      borderRadius: '12px',
      overflow: 'hidden',
      boxShadow: C.shadow,
      transition: 'box-shadow 0.2s, transform 0.2s',
    }}
      onMouseEnter={e => { e.currentTarget.style.boxShadow = C.shadowMd; e.currentTarget.style.transform = 'translateY(-1px)'; }}
      onMouseLeave={e => { e.currentTarget.style.boxShadow = C.shadow;   e.currentTarget.style.transform = 'translateY(0)'; }}
    >
      {/* Top bar */}
      <div style={{
        background: `linear-gradient(to right, ${podDone ? C.green : C.amber}18, transparent)`,
        borderBottom: `1px solid ${podDone ? C.green : C.amber}25`,
        padding: '0.65rem 1.25rem',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      }}>
        <span style={{ fontWeight: 800, fontSize: '0.92rem', color: C.text, fontFamily: 'monospace' }}>
          {s.shipment_id}
        </span>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <Pill bg={`${statusColor}15`} color={statusColor} border={`${statusColor}35`}>
            {onTime ? '✅ On Time' : `⏱️ Delayed ${s.delay_days || 0}d`}
          </Pill>
          <Pill bg={podDone ? `${C.green}15` : `${C.amber}12`} color={podDone ? C.green : C.amber} border={podDone ? `${C.green}35` : `${C.amber}30`}>
            {podDone ? '📄 POD Done' : '⏳ POD Pending'}
          </Pill>
        </div>
      </div>

      {/* Detail grid */}
      <div style={{ padding: '1rem 1.25rem', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '0.75rem 1.5rem' }}>
        {[
          ['🗺️ Route',    `${s.origin || '—'} → ${s.destination || '—'}`],
          ['📅 Dispatch', s.dispatch_date || '—'],
          ['📦 Delivery', s.delivery_date || 'Pending'],
          ['🚗 Vehicle',  s.vehicle_no || '—'],
          ['⚖️ Weight',   s.net_weight ? `${s.net_weight} MT` : '—'],
          ['💰 Freight',  s.revenue ? `₹${Number(s.revenue).toLocaleString('en-IN')}` : '—'],
        ].map(([label, val]) => (
          <div key={label}>
            <div style={{ fontSize: '0.67rem', color: C.muted, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em' }}>{label}</div>
            <div style={{ fontSize: '0.88rem', color: C.text, fontWeight: 600, marginTop: '0.1rem' }}>{val}</div>
          </div>
        ))}
      </div>

      {/* Actions */}
      <div style={{ borderTop: `1px solid ${C.border}`, padding: '0.75rem 1.25rem', display: 'flex', gap: '0.75rem', alignItems: 'center', flexWrap: 'wrap', background: '#fafafa' }}>
        {podDone ? (
          <span style={{ color: C.green, fontWeight: 600, fontSize: '0.85rem' }}>✅ POD Submitted</span>
        ) : (
          <label style={{
            padding: '0.48rem 1rem',
            background: `linear-gradient(135deg, ${C.teal}, #0f766e)`,
            color: '#fff', borderRadius: '7px', fontWeight: 700,
            fontSize: '0.82rem', cursor: uploading ? 'not-allowed' : 'pointer',
            opacity: uploading ? 0.6 : 1, transition: 'opacity 0.2s',
          }}>
            {uploading ? '⬆️ Uploading…' : '📤 Upload POD'}
            <input type="file" accept=".pdf,.jpg,.jpeg,.png" onChange={handleFile} style={{ display: 'none' }} disabled={uploading} />
          </label>
        )}

        <a
          href={`${downloadInvoice(s.shipment_id)}?token=${localStorage.getItem('access_token') || ''}`}
          target="_blank" rel="noreferrer"
          style={{ padding: '0.48rem 1rem', background: C.card, border: `1px solid ${C.border}`, color: C.sub, borderRadius: '7px', fontSize: '0.82rem', fontWeight: 600, textDecoration: 'none' }}
        >
          📄 Invoice
        </a>

        {msg && (
          <span style={{ fontSize: '0.8rem', color: msg.startsWith('✅') ? C.green : C.rose, fontWeight: 600 }}>
            {msg}
          </span>
        )}
      </div>
    </div>
  );
}


// ─── Shared widgets ───────────────────────────────────────────────────────────
function StatCard({ icon, label, value, accent, bg }) {
  return (
    <div style={{
      background: C.card, border: `1px solid ${C.border}`,
      borderRadius: '12px', padding: '1.1rem 1.25rem',
      borderTop: `3px solid ${accent}`,
      boxShadow: C.shadow,
    }}>
      <div style={{ width: '38px', height: '38px', borderRadius: '8px', background: bg, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1.1rem', marginBottom: '0.6rem' }}>{icon}</div>
      <div style={{ fontSize: '1.75rem', fontWeight: 800, color: accent, lineHeight: 1 }}>{value}</div>
      <div style={{ fontSize: '0.75rem', color: C.muted, marginTop: '0.25rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em' }}>{label}</div>
    </div>
  );
}

function RoleBadge({ color, bg, label, icon }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', padding: '0.3rem 0.75rem', background: bg, border: `1px solid ${color}30`, borderRadius: '999px' }}>
      <span style={{ fontSize: '0.85rem' }}>{icon}</span>
      <span style={{ fontSize: '0.68rem', fontWeight: 700, color, letterSpacing: '0.06em' }}>{label}</span>
    </div>
  );
}

function Pill({ bg, color, border, children }) {
  return (
    <span style={{ padding: '0.2rem 0.65rem', borderRadius: '999px', fontSize: '0.72rem', fontWeight: 700, background: bg, color, border: `1px solid ${border}` }}>
      {children}
    </span>
  );
}

function LoadingState({ text }) {
  return (
    <div style={{ textAlign: 'center', padding: '4rem 2rem', color: C.muted }}>
      <div style={{ fontSize: '2rem', marginBottom: '0.75rem' }}>⏳</div>
      <div style={{ fontSize: '0.9rem' }}>{text}</div>
    </div>
  );
}

function EmptyState({ icon, title, sub }) {
  return (
    <div style={{ textAlign: 'center', padding: '4rem 2rem', background: C.card, borderRadius: '12px', border: `1px solid ${C.border}` }}>
      <div style={{ fontSize: '2.5rem', marginBottom: '0.75rem' }}>{icon}</div>
      <div style={{ fontWeight: 700, color: C.text, fontSize: '1rem' }}>{title}</div>
      <div style={{ fontSize: '0.82rem', color: C.muted, marginTop: '0.3rem' }}>{sub}</div>
    </div>
  );
}

// ─── Style helpers ────────────────────────────────────────────────────────────
const lightInput = {
  padding: '0.65rem 1rem', background: C.card,
  border: `1px solid ${C.border}`, borderRadius: '8px',
  color: C.text, fontSize: '0.9rem', outline: 'none',
  fontFamily: 'inherit',
};

const ghostBtn = {
  padding: '0.45rem 1rem', background: 'transparent',
  border: `1px solid ${C.border}`, borderRadius: '7px',
  color: C.sub, cursor: 'pointer', fontSize: '0.82rem', fontWeight: 600,
  fontFamily: 'inherit',
};

function outlineBtn(color) {
  return {
    padding: '0.65rem 1.1rem',
    background: `${color}10`, border: `1px solid ${color}40`,
    borderRadius: '8px', color, fontWeight: 700,
    cursor: 'pointer', fontSize: '0.88rem', fontFamily: 'inherit',
  };
}
