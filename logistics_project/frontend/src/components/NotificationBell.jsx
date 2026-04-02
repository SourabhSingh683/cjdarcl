/**
 * NotificationBell.jsx  —  Light Theme
 * ======================================
 * Notification bell with unread badge, dropdown panel, 60s auto-poll.
 */
import { useState, useEffect, useRef, useCallback } from 'react';
import { fetchNotifications, markNotificationRead, markAllNotificationsRead } from '../api';

const C = {
  card:   '#ffffff',
  bg:     '#f8fafc',
  border: '#e2e8f0',
  text:   '#0f172a',
  sub:    '#475569',
  muted:  '#94a3b8',
  teal:   '#0d9488',
  red:    '#ef4444',
  shadow: '0 10px 30px rgba(0,0,0,0.10)',
};

const TYPE_ICONS = {
  shipment_assigned:  '🚚',
  pod_uploaded:       '📄',
  daily_pod_reminder: '⏰',
  general:            '🔔',
};

function timeAgo(dateStr) {
  const diff = Date.now() - new Date(dateStr);
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

export default function NotificationBell() {
  const [open, setOpen]       = useState(false);
  const [notifs, setNotifs]   = useState([]);
  const [unread, setUnread]   = useState(0);
  const [loading, setLoading] = useState(false);
  const dropdownRef           = useRef(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchNotifications({ page_size: 15 });
      setNotifs(data.results || []);
      setUnread(data.unread_count || 0);
    } catch { /* silent */ }
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    const id = setInterval(load, 60_000);
    return () => clearInterval(id);
  }, [load]);

  useEffect(() => {
    const handler = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  async function handleRead(id) {
    await markNotificationRead(id);
    setNotifs(prev => prev.map(n => n.id === id ? { ...n, is_read: true } : n));
    setUnread(prev => Math.max(0, prev - 1));
  }

  async function handleMarkAll() {
    await markAllNotificationsRead();
    setNotifs(prev => prev.map(n => ({ ...n, is_read: true })));
    setUnread(0);
  }

  return (
    <div ref={dropdownRef} style={{ position: 'relative' }}>
      {/* Bell button */}
      <button
        id="notif-bell-btn"
        onClick={() => { setOpen(o => !o); if (!open) load(); }}
        style={{
          position: 'relative',
          background: open ? `${C.teal}10` : 'transparent',
          border: `1px solid ${open ? C.teal + '50' : C.border}`,
          borderRadius: '8px',
          padding: '0.45rem 0.6rem',
          cursor: 'pointer', fontSize: '1.1rem', lineHeight: 1,
          transition: 'all 0.2s',
        }}
      >
        🔔
        {unread > 0 && (
          <span style={{
            position: 'absolute', top: '-5px', right: '-5px',
            background: C.red, color: '#fff',
            borderRadius: '999px', fontSize: '0.62rem', fontWeight: 700,
            minWidth: '17px', height: '17px',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            padding: '0 2px', border: '2px solid #fff',
          }}>
            {unread > 99 ? '99+' : unread}
          </span>
        )}
      </button>

      {/* Dropdown */}
      {open && (
        <div style={{
          position: 'absolute', top: 'calc(100% + 8px)', right: 0,
          width: '340px', maxHeight: '420px',
          background: C.card,
          border: `1px solid ${C.border}`,
          borderRadius: '12px',
          boxShadow: C.shadow,
          zIndex: 1000,
          display: 'flex', flexDirection: 'column',
          overflow: 'hidden',
        }}>
          {/* Header */}
          <div style={{
            padding: '0.85rem 1rem',
            borderBottom: `1px solid ${C.border}`,
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          }}>
            <span style={{ fontWeight: 700, color: C.text, fontSize: '0.88rem' }}>
              🔔 Notifications {unread > 0 && <span style={{ color: C.teal }}>({unread})</span>}
            </span>
            {unread > 0 && (
              <button onClick={handleMarkAll}
                style={{ background: 'none', border: 'none', color: C.teal, fontSize: '0.75rem', cursor: 'pointer', fontWeight: 600 }}>
                Mark all read
              </button>
            )}
          </div>

          {/* Notification list */}
          <div style={{ overflowY: 'auto', flex: 1 }}>
            {loading && notifs.length === 0 && (
              <div style={{ padding: '2rem', textAlign: 'center', color: C.muted, fontSize: '0.85rem' }}>Loading…</div>
            )}
            {!loading && notifs.length === 0 && (
              <div style={{ padding: '2rem', textAlign: 'center', color: C.muted, fontSize: '0.85rem' }}>🎉 You're all caught up!</div>
            )}
            {notifs.map(n => (
              <div
                key={n.id}
                onClick={() => !n.is_read && handleRead(n.id)}
                style={{
                  padding: '0.75rem 1rem',
                  borderBottom: `1px solid ${C.border}`,
                  background: n.is_read ? C.card : `${C.teal}06`,
                  cursor: n.is_read ? 'default' : 'pointer',
                  display: 'flex', gap: '0.75rem', alignItems: 'flex-start',
                  transition: 'background 0.15s',
                }}
              >
                <span style={{ fontSize: '1.2rem', flexShrink: 0, marginTop: '1px' }}>
                  {TYPE_ICONS[n.notif_type] || '🔔'}
                </span>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontWeight: n.is_read ? 500 : 700, color: n.is_read ? C.muted : C.text, fontSize: '0.83rem', marginBottom: '0.15rem' }}>
                    {n.title}
                  </div>
                  <div style={{ color: C.sub, fontSize: '0.76rem', lineHeight: 1.4 }}>{n.message}</div>
                  {n.shipment_ref && (
                    <div style={{ color: C.teal, fontSize: '0.7rem', marginTop: '0.2rem', fontWeight: 600 }}>
                      Shipment: {n.shipment_ref}
                    </div>
                  )}
                  <div style={{ color: C.muted, fontSize: '0.67rem', marginTop: '0.25rem' }}>
                    {timeAgo(n.created_at)}
                  </div>
                </div>
                {!n.is_read && (
                  <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: C.teal, flexShrink: 0, marginTop: '5px' }} />
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
