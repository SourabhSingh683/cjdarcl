import { useState } from 'react';
import { useAuth } from '../context/AuthContext';

const C = {
  bgGradient: 'linear-gradient(135deg, #ffffff 0%, #f0f7ff 100%)',
  card:       'rgba(255, 255, 255, 0.7)',
  cardBorder: 'rgba(255, 255, 255, 0.4)',
  text:       '#0f172a',
  sub:        '#475569',
  muted:      '#94a3b8',
  blue:       '#3b82f6',
  blueDk:     '#2563eb',
  errorBg:    'rgba(254, 242, 242, 0.8)',
  errorText:  '#b91c1c',
};

const inputStyle = {
  width: '100%', padding: '0.85rem 1rem',
  background: 'rgba(255, 255, 255, 0.5)',
  border: '1px solid rgba(226, 232, 240, 0.8)',
  borderRadius: '12px', color: '#0f172a',
  fontSize: '0.95rem', outline: 'none',
  boxSizing: 'border-box', fontFamily: 'inherit',
  transition: 'all 0.2s ease',
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
      // Requirements: if user enters wrong id or password it should display "wrong credentials"
      const msg = ex.message || '';
      if (msg.includes('401') || msg.includes('400') || msg.toLowerCase().includes('credentials') || msg.toLowerCase().includes('fail')) {
        setErr('Wrong credentials. Please check your username and password.');
      } else {
        setErr(msg || 'An unexpected error occurred. Please try again.');
      }
    }
    setLoading(false);
  };

  return (
    <div style={{
      minHeight: '100vh', 
      background: C.bgGradient,
      display: 'flex', 
      alignItems: 'center', 
      justifyContent: 'center',
      fontFamily: "'Inter','Segoe UI',sans-serif", 
      padding: '2rem',
      position: 'relative',
      overflow: 'hidden'
    }}>
      {/* Background Watermark */}
      <div style={{
        position: 'absolute',
        top: '50%',
        left: '50%',
        width: '2200px',
        height: '2200px',
        opacity: 0.25,
        filter: 'blur(4px)',
        zIndex: 0,
        pointerEvents: 'none',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        animation: 'slowRotate 120s linear infinite'
      }}>
        <img src="/petal_logo.png" alt="" style={{ width: '100%', height: 'auto' }} 
           onError={e => {
             // Fallback if petal_logo.png is missing: use manncj.png or just hide
             e.currentTarget.src = "/manncj.png";
             e.currentTarget.style.width = "100%";
           }}
        />
      </div>

      <div style={{ width: '100%', maxWidth: '420px', position: 'relative', zIndex: 1, animation: 'fadeIn 0.6s ease-out' }}>
        <div style={{ textAlign: 'center', marginBottom: '2.5rem' }}>
          <img src="/manncj.png" alt="CJ Darcl" style={{ height: '60px', marginBottom: '1rem' }} />
          <div style={{ fontWeight: 800, fontSize: '0.8rem', color: C.muted, textTransform: 'uppercase', letterSpacing: '0.1rem' }}>
            Logistics Management System
          </div>
        </div>

        <div style={{ 
          background: C.card, 
          backdropFilter: 'blur(16px)',
          WebkitBackdropFilter: 'blur(16px)',
          border: `1px solid ${C.cardBorder}`, 
          borderRadius: '24px', 
          padding: '2.5rem', 
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.1)',
        }}>
          <div style={{ marginBottom: '2rem', textAlign: 'center' }}>
            <h1 style={{ fontSize: '1.5rem', fontWeight: 800, color: C.text, margin: '0 0 0.5rem 0' }}>Welcome Back</h1>
            <p style={{ fontSize: '0.9rem', color: C.sub, margin: 0 }}>Authenticated access for Branch Managers</p>
          </div>

          <form onSubmit={handleLogin}>
            <div style={{ marginBottom: '1.25rem' }}>
              <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: C.text, marginBottom: '0.5rem', textTransform: 'uppercase' }}>
                Username
              </label>
              <input 
                style={inputStyle} 
                value={username} 
                onChange={e => setUsername(e.target.value)} 
                placeholder="Enter username"
                onFocus={e => { e.target.style.borderColor = C.blue; e.target.style.boxShadow = '0 0 0 4px rgba(59, 130, 246, 0.1)'; }}
                onBlur={e => { e.target.style.borderColor = 'rgba(226, 232, 240, 0.8)'; e.target.style.boxShadow = 'none'; }}
              />
            </div>
            
            <div style={{ marginBottom: '1.75rem' }}>
              <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 700, color: C.text, marginBottom: '0.5rem', textTransform: 'uppercase' }}>
                Password
              </label>
              <input 
                type="password" 
                style={inputStyle} 
                value={password} 
                onChange={e => setPassword(e.target.value)} 
                placeholder="••••••••"
                onFocus={e => { e.target.style.borderColor = C.blue; e.target.style.boxShadow = '0 0 0 4px rgba(59, 130, 246, 0.1)'; }}
                onBlur={e => { e.target.style.borderColor = 'rgba(226, 232, 240, 0.8)'; e.target.style.boxShadow = 'none'; }}
              />
            </div>
            
            {err && (
              <div style={{ 
                background: C.errorBg, 
                padding: '1rem', 
                borderRadius: '12px', 
                color: C.errorText, 
                fontSize: '0.85rem', 
                marginBottom: '1.5rem',
                border: '1px solid rgba(185, 28, 28, 0.1)',
                display: 'flex',
                gap: '0.5rem',
                alignItems: 'center'
              }}>
                <span>⚠️</span>
                <span>{err}</span>
              </div>
            )}

            <style>{`
              @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
              @keyframes slowRotate { 
                from { transform: translate(-50%, -50%) rotate(0deg); } 
                to { transform: translate(-50%, -50%) rotate(360deg); } 
              }
              .signin-btn {
                width: 100%; padding: 1rem; 
                background: linear-gradient(135deg, #3b82f6, #2563eb);
                color: #fff; border: none; borderRadius: 12px; 
                fontWeight: 700; cursor: pointer;
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                box-shadow: 0 4px 6px -1px rgba(59, 130, 246, 0.2), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
              }
              .signin-btn:hover:not(:disabled) {
                transform: translateY(-2px);
                box-shadow: 0 10px 15px -3px rgba(59, 130, 246, 0.3), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
                filter: brightness(1.1);
              }
              .signin-btn:active:not(:disabled) {
                transform: translateY(0);
              }
            `}</style>
            
            <button 
              type="submit" 
              disabled={loading} 
              className="signin-btn"
              style={{
                width: '100%', padding: '1rem', background: `linear-gradient(135deg, ${C.blue}, ${C.blueDk})`,
                color: '#fff', border: 'none', borderRadius: '12px', fontWeight: 700, 
                cursor: loading ? 'not-allowed' : 'pointer',
                opacity: loading ? 0.7 : 1
              }}
            >
              {loading ? 'Authenticating...' : 'Sign In →'}
            </button>
          </form>
        </div>
        
        <div style={{ textAlign: 'center', marginTop: '2rem', fontSize: '0.8rem', color: C.muted }}>
          Powered by CJ Darcl Logistics Intelligence
        </div>
      </div>
    </div>
  );
}

