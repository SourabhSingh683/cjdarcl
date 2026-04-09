import { useState } from 'react';
import { useAuth } from '../context/AuthContext';

const C = {
  bg:      '#f1f5f9',
  card:    '#ffffff',
  border:  '#e2e8f0',
  text:    '#0f172a',
  sub:     '#475569',
  muted:   '#94a3b8',
  teal:    '#0d9488',
  tealDk:  '#0f766e',
  tealGlow:'rgba(13,148,136,0.12)',
  blue:    '#3b82f6',
  blueDk:  '#2563eb',
  shadowLg:'0 20px 40px rgba(0,0,0,0.08)',
};

const inputStyle = {
  width: '100%', padding: '0.72rem 1rem',
  background: '#f8fafc',
  border: `1px solid ${C.border}`,
  borderRadius: '8px', color: C.text,
  fontSize: '0.95rem', outline: 'none',
  boxSizing: 'border-box', fontFamily: 'inherit',
  transition: 'border-color 0.2s, box-shadow 0.2s',
};

export default function LoginPage({ onLoginSuccess }) {
  const { login } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState('');

  const handleLogin = async (e) => {
    e.preventDefault();
    if (!username || !password) { setErr('Please enter your username and password.'); return; }
    setLoading(true); setErr('');
    try {
      await login(username, password);
      onLoginSuccess('manager');
    } catch (ex) {
      setErr(ex.message || 'Login failed. Check your credentials.');
    }
    setLoading(false);
  };

  return (
    <div style={{
      minHeight: '100vh', background: C.bg,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontFamily: "'Inter','Segoe UI',sans-serif", padding: '1.5rem',
    }}>
      <div style={{ width: '100%', maxWidth: '400px' }}>
        <div style={{ textAlign: 'center', marginBottom: '1.75rem' }}>
          <img src="/manncj.png" alt="CJ Darcl" style={{ height: '52px' }} 
            onError={e => e.currentTarget.style.display = 'none'} />
          <div style={{ fontWeight: 800, fontSize: '0.85rem', color: C.muted, marginTop: '0.6rem', textTransform: 'uppercase' }}>
            Logistics Management System
          </div>
        </div>

        <div style={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: '16px', padding: '2rem', boxShadow: C.shadowLg }}>
          <div style={{ marginBottom: '1.75rem', textAlign: 'center' }}>
            <div style={{ fontSize: '1.1rem', fontWeight: 800, color: C.text }}>Branch Manager Sign In</div>
            <div style={{ fontSize: '0.8rem', color: C.sub }}>Authenticated access only</div>
          </div>

          <form onSubmit={handleLogin}>
            <label style={{ display: 'block', marginBottom: '1rem' }}>
              <span style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, marginBottom: '0.4rem', textTransform: 'uppercase' }}>Username</span>
              <input style={inputStyle} value={username} onChange={e => setUsername(e.target.value)} placeholder="Username" />
            </label>
            <label style={{ display: 'block', marginBottom: '1.25rem' }}>
              <span style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, marginBottom: '0.4rem', textTransform: 'uppercase' }}>Password</span>
              <input type="password" style={inputStyle} value={password} onChange={e => setPassword(e.target.value)} placeholder="••••••••" />
            </label>
            
            {err && (
              <div style={{ background: '#FEF2F2', padding: '0.75rem', borderRadius: '8px', color: '#B91C1C', fontSize: '0.85rem', marginBottom: '1rem' }}>
                ⚠️ {err}
              </div>
            )}

            <button type="submit" disabled={loading} style={{
              width: '100%', padding: '0.85rem', background: `linear-gradient(135deg, ${C.blue}, ${C.blueDk})`,
              color: '#fff', border: 'none', borderRadius: '8px', fontWeight: 700, cursor: loading ? 'not-allowed' : 'pointer',
              opacity: loading ? 0.7 : 1
            }}>
              {loading ? 'Signing in...' : 'Sign In →'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
