/**
 * LoginPage.jsx  —  Light Theme + Role Quick-Select
 * ==================================================
 * White card login matching the Manager Dashboard aesthetic.
 * Features:
 *   • Password login tab
 *   • Mobile OTP login tab (2-step)
 *   • Quick-select role buttons (pre-fills demo credentials)
 */

import { useState } from 'react';
import { useAuth } from '../context/AuthContext';

// ── Tokens ────────────────────────────────────────────────────────────────────
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
  blueGlow:'rgba(59,130,246,0.10)',
  violet:  '#8b5cf6',
  violetGL:'rgba(139,92,246,0.10)',
  amber:   '#f59e0b',
  amberGL: 'rgba(245,158,11,0.10)',
  red:     '#ef4444',
  shadow:  '0 4px 6px -1px rgba(0,0,0,0.05), 0 2px 4px -2px rgba(0,0,0,0.03)',
  shadowLg:'0 20px 40px rgba(0,0,0,0.08)',
};

// Demo role presets
const ROLES = [
  {
    role: 'manager',
    label: 'Branch Manager',
    icon: '👔',
    username: 'manager1',
    password: 'Darcl@1234',
    color: C.teal,
    bg: C.tealGlow,
    desc: 'Full analytics & all shipments',
  },
  {
    role: 'driver',
    label: 'Driver',
    icon: '🚚',
    username: 'driver1',
    password: 'Darcl@1234',
    color: C.blue,
    bg: C.blueGlow,
    desc: 'Assigned shipments & POD upload',
  },
  {
    role: 'customer',
    label: 'Customer',
    icon: '📦',
    username: 'customer1',
    password: 'Darcl@1234',
    color: C.violet,
    bg: C.violetGL,
    desc: 'Track your shipments & invoices',
  },
];

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
  const { login, loginVehicle, requestOTP, loginOTP } = useAuth();

  const [mode, setMode]         = useState('password');
  const [vehicleNo, setVehicleNo] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [phone, setPhone]       = useState('');
  const [otpStep, setOtpStep]   = useState(1);
  const [otpCode, setOtpCode]   = useState('');
  const [demoOtp, setDemoOtp]   = useState('');
  const [loading, setLoading]   = useState(false);
  const [err, setErr]           = useState('');

  // ── Quick role select ──────────────────────────────────────────────────────
  function prefillRole(r) {
    setMode('password');
    setUsername(r.username);
    setPassword(r.password);
    setErr('');
  }

  // ── Password login ─────────────────────────────────────────────────────────
  async function handlePasswordLogin(e) {
    e.preventDefault();
    if (!username || !password) { setErr('Please enter your username and password.'); return; }
    setLoading(true); setErr('');
    try {
      const user = await login(username, password);
      onLoginSuccess(user.role);
    } catch (ex) {
      setErr(ex.message || 'Login failed. Check your credentials.');
    }
    setLoading(false);
  }

  // ── OTP step 1 ─────────────────────────────────────────────────────────────
  async function handleOTPRequest(e) {
    e.preventDefault();
    if (!phone) { setErr('Please enter your mobile number.'); return; }
    setLoading(true); setErr('');
    try {
      const res = await requestOTP(phone);
      setDemoOtp(res._demo_otp || '');
      setOtpStep(2);
    } catch (ex) {
      setErr(ex.message || 'Failed to send OTP.');
    }
    setLoading(false);
  }

  // ── OTP step 2 ─────────────────────────────────────────────────────────────
  async function handleOTPVerify(e) {
    e.preventDefault();
    if (!otpCode) { setErr('Please enter the OTP.'); return; }
    setLoading(true); setErr('');
    try {
      const user = await loginOTP(phone, otpCode);
      onLoginSuccess(user.role);
    } catch (ex) {
      setErr(ex.message || 'Invalid OTP. Please try again.');
    }
    setLoading(false);
  }

  function resetOtp() { setOtpStep(1); setOtpCode(''); setDemoOtp(''); setErr(''); }

  // ── Vehicle login ──────────────────────────────────────────────────────────
  async function handleVehicleLogin(e) {
    e.preventDefault();
    if (!vehicleNo) { setErr('Please enter Gaadi Number.'); return; }
    setLoading(true); setErr('');
    try {
      const user = await loginVehicle(vehicleNo);
      onLoginSuccess(user.role);
    } catch (ex) {
      setErr(ex.message || 'Login failed. Gaadi number not found.');
    }
    setLoading(false);
  }

  return (
    <div style={{
      minHeight: '100vh',
      background: C.bg,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontFamily: "'Inter','Segoe UI',sans-serif",
      padding: '1.5rem',
    }}>
      {/* Subtle grid */}
      <div style={{
        position: 'fixed', inset: 0, pointerEvents: 'none',
        backgroundImage: 'linear-gradient(rgba(13,148,136,0.035) 1px, transparent 1px), linear-gradient(90deg, rgba(13,148,136,0.035) 1px, transparent 1px)',
        backgroundSize: '48px 48px',
      }} />

      <div style={{ width: '100%', maxWidth: '460px', position: 'relative', zIndex: 1 }}>

        {/* Logo + brand */}
        <div style={{ textAlign: 'center', marginBottom: '1.75rem' }}>
          <img src="/manncj.png" alt="CJ Darcl"
            onError={e => {
              e.currentTarget.style.display = 'none';
              document.getElementById('login-fallback-logo').style.display = 'flex';
            }}
            style={{ height: '52px', objectFit: 'contain' }}
          />
          <div id="login-fallback-logo" style={{
            display: 'none', width: '52px', height: '52px', borderRadius: '14px',
            background: `linear-gradient(135deg, ${C.teal}, ${C.tealDk})`,
            alignItems: 'center', justifyContent: 'center',
            fontSize: '1.8rem', margin: '0 auto',
            boxShadow: `0 8px 24px ${C.teal}30`,
          }}>📦</div>
          <div style={{ fontWeight: 800, fontSize: '0.85rem', color: C.muted, marginTop: '0.6rem', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
            Logistics Management System
          </div>
        </div>

        {/* Main card */}
        <div style={{
          background: C.card,
          border: `1px solid ${C.border}`,
          borderRadius: '16px',
          padding: '2rem',
          boxShadow: C.shadowLg,
        }}>

          {/* ── Role quick-select ─────────────────────────────────────────── */}
          <div style={{ marginBottom: '1.75rem' }}>
            <div style={{ fontSize: '0.7rem', fontWeight: 700, color: C.muted, textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: '0.65rem' }}>
              Sign in as
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '0.6rem' }}>
              {ROLES.map(r => (
                <button
                  key={r.role}
                  onClick={() => prefillRole(r)}
                  title={r.desc}
                  style={{
                    padding: '0.75rem 0.5rem',
                    background: username === r.username ? r.bg : '#f8fafc',
                    border: `1.5px solid ${username === r.username ? r.color : C.border}`,
                    borderRadius: '10px',
                    cursor: 'pointer', textAlign: 'center', fontFamily: 'inherit',
                    transition: 'all 0.2s',
                    boxShadow: username === r.username ? `0 0 0 3px ${r.color}18` : 'none',
                  }}
                >
                  <div style={{ fontSize: '1.4rem', marginBottom: '0.3rem' }}>{r.icon}</div>
                  <div style={{
                    fontSize: '0.72rem', fontWeight: 700,
                    color: username === r.username ? r.color : C.sub,
                    lineHeight: 1.2,
                  }}>
                    {r.label}
                  </div>
                </button>
              ))}
            </div>
            {/* Role description */}
            {username && (() => {
              const found = ROLES.find(r => r.username === username);
              return found ? (
                <div style={{
                  marginTop: '0.6rem', padding: '0.5rem 0.75rem',
                  background: `${found.color}08`, border: `1px solid ${found.color}20`,
                  borderRadius: '7px', fontSize: '0.76rem', color: found.color, fontWeight: 600,
                }}>
                  {found.icon} {found.desc}
                </div>
              ) : null;
            })()}
          </div>

          {/* ── Mode toggle ───────────────────────────────────────────────── */}
          <div style={{
            display: 'grid', gridTemplateColumns: '1fr 1fr',
            background: '#f1f5f9', borderRadius: '8px',
            padding: '3px', marginBottom: '1.5rem', gap: '3px',
          }}>
            {[['password', '🔑 Password'], ['vehicle', '🚚 Gaadi No.'], ['otp', '📱 Mobile OTP']].map(([m, label]) => (
              <button key={m}
                onClick={() => { setMode(m); setErr(''); resetOtp(); }}
                style={{
                  padding: '0.55rem', borderRadius: '6px', border: 'none',
                  background: mode === m ? C.card : 'transparent',
                  color: mode === m ? C.teal : C.muted,
                  fontWeight: 700, fontSize: '0.82rem', cursor: 'pointer',
                  fontFamily: 'inherit',
                  boxShadow: mode === m ? C.shadow : 'none',
                  transition: 'all 0.2s',
                }}
              >
                {label}
              </button>
            ))}
          </div>

          {/* ── Password form ─────────────────────────────────────────────── */}
          {mode === 'password' && (
            <form onSubmit={handlePasswordLogin}>
              <label style={{ display: 'block', marginBottom: '1rem' }}>
                <FieldLabel>Username</FieldLabel>
                <input
                  id="login-username"
                  style={inputStyle}
                  placeholder="Enter username"
                  value={username}
                  onChange={e => setUsername(e.target.value)}
                  autoComplete="username"
                />
              </label>
              <label style={{ display: 'block', marginBottom: '1.25rem' }}>
                <FieldLabel>Password</FieldLabel>
                <input
                  id="login-password"
                  type="password"
                  style={inputStyle}
                  placeholder="Enter password"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  autoComplete="current-password"
                />
              </label>
              {err && <ErrorBox msg={err} />}
              <button
                id="login-submit"
                type="submit"
                disabled={loading}
                style={primaryBtn(C.teal, C.tealDk, loading)}
              >
                {loading ? '…Signing in' : 'Sign In →'}
              </button>
            </form>
          )}

          {/* ── Vehicle form ──────────────────────────────────────────────── */}
          {mode === 'vehicle' && (
            <form onSubmit={handleVehicleLogin}>
              <label style={{ display: 'block', marginBottom: '1.25rem' }}>
                <FieldLabel>Gaadi Number (Vehicle No.)</FieldLabel>
                <input
                  id="login-vehicle"
                  style={inputStyle}
                  placeholder="e.g. HR26-88219"
                  value={vehicleNo}
                  onChange={e => setVehicleNo(e.target.value)}
                />
                <div style={{ fontSize: '0.72rem', color: C.muted, marginTop: '0.4rem' }}>
                  Drivers: Enter your vehicle number to see assigned loads.
                </div>
              </label>
              {err && <ErrorBox msg={err} />}
              <button
                id="vehicle-login-submit"
                type="submit"
                disabled={loading}
                style={primaryBtn(C.blue, '#1d4ed8', loading)}
              >
                {loading ? '…Scanning' : '🚚 Enter Driver Panel →'}
              </button>
            </form>
          )}

          {/* ── OTP step 1 ───────────────────────────────────────────────── */}
          {mode === 'otp' && otpStep === 1 && (
            <form onSubmit={handleOTPRequest}>
              <label style={{ display: 'block', marginBottom: '1.25rem' }}>
                <FieldLabel>Mobile Number</FieldLabel>
                <input
                  id="otp-phone"
                  style={inputStyle}
                  placeholder="+91 98XXXXXXXX"
                  value={phone}
                  onChange={e => setPhone(e.target.value)}
                  type="tel"
                />
              </label>
              {err && <ErrorBox msg={err} />}
              <button type="submit" disabled={loading} style={primaryBtn(C.teal, C.tealDk, loading)}>
                {loading ? '…Sending OTP' : 'Send OTP →'}
              </button>
            </form>
          )}

          {/* ── OTP step 2 ───────────────────────────────────────────────── */}
          {mode === 'otp' && otpStep === 2 && (
            <form onSubmit={handleOTPVerify}>
              <div style={{
                background: '#f0fdf4', border: `1px solid ${C.teal}25`,
                borderRadius: '8px', padding: '0.75rem 1rem', marginBottom: '1.25rem',
                fontSize: '0.85rem', color: C.sub, display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              }}>
                <span>OTP sent to <strong style={{ color: C.text }}>{phone}</strong></span>
                {demoOtp && (
                  <span style={{ color: C.teal, fontWeight: 800, fontFamily: 'monospace', fontSize: '0.95rem' }}>
                    {demoOtp}
                  </span>
                )}
              </div>
              <label style={{ display: 'block', marginBottom: '1.25rem' }}>
                <FieldLabel>Enter OTP</FieldLabel>
                <input
                  id="otp-code"
                  style={{ ...inputStyle, letterSpacing: '0.3em', fontSize: '1.35rem', textAlign: 'center' }}
                  placeholder="_ _ _ _ _ _"
                  value={otpCode}
                  onChange={e => setOtpCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                  maxLength={6}
                  inputMode="numeric"
                />
              </label>
              {err && <ErrorBox msg={err} />}
              <button type="submit" disabled={loading} style={primaryBtn(C.teal, C.tealDk, loading)}>
                {loading ? '…Verifying' : 'Verify OTP →'}
              </button>
              <button type="button" onClick={resetOtp}
                style={{ width: '100%', marginTop: '0.75rem', background: 'transparent', border: 'none', color: C.muted, cursor: 'pointer', fontSize: '0.83rem', fontFamily: 'inherit' }}>
                ← Change number
              </button>
            </form>
          )}
        </div>

        {/* Footer */}
        <p style={{ textAlign: 'center', color: C.muted, fontSize: '0.72rem', marginTop: '1.25rem' }}>
          CJ Darcl Logistics Ltd. · Jamshedpur Branch · All rights reserved
        </p>
      </div>
    </div>
  );
}

// ─── Helpers ─────────────────────────────────────────────────────────────────
function FieldLabel({ children }) {
  return (
    <span style={{
      display: 'block', fontSize: '0.75rem',
      fontWeight: 700, color: '#475569',
      textTransform: 'uppercase', letterSpacing: '0.05em',
      marginBottom: '0.4rem',
    }}>
      {children}
    </span>
  );
}

function ErrorBox({ msg }) {
  return (
    <div style={{
      background: '#FEF2F2', border: '1px solid rgba(239,68,68,0.25)',
      borderRadius: '7px', padding: '0.6rem 0.9rem',
      color: '#B91C1C', fontSize: '0.85rem', marginBottom: '1rem',
    }}>
      ⚠️ {msg}
    </div>
  );
}

function primaryBtn(color, dark, loading) {
  return {
    width: '100%', padding: '0.85rem',
    background: `linear-gradient(135deg, ${color}, ${dark})`,
    color: '#fff', border: 'none', borderRadius: '8px',
    fontSize: '1rem', fontWeight: 700, cursor: loading ? 'not-allowed' : 'pointer',
    letterSpacing: '0.03em', opacity: loading ? 0.65 : 1,
    fontFamily: 'inherit',
    transition: 'opacity 0.2s, transform 0.1s',
    boxShadow: `0 4px 14px ${color}35`,
  };
}
