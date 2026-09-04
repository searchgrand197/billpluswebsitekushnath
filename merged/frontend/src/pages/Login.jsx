import React, { useState } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { Leaf, User, Lock, Eye, EyeOff, ArrowRight, ShieldCheck } from 'lucide-react';
import { useAuth } from '../components/AuthContext';

export default function Login() {
  const { user, login, ready } = useAuth();
  const location = useLocation();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPass, setShowPass] = useState(false);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const from = location.state?.from || '/';

  if (!ready) {
    return (
      <div className="login-screen">
        <div className="login-loading">Loading Billvice…</div>
      </div>
    );
  }
  if (user) {
    return <Navigate to={from} replace />;
  }

  const submit = async (e) => {
    e.preventDefault();
    setError('');
    setBusy(true);
    try {
      await login(username, password);
    } catch (err) {
      setError(err.response?.data?.error || 'Could not sign in. Check username and password.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="login-screen">
      <div className="login-blob login-blob-a" />
      <div className="login-blob login-blob-b" />

      <div className="login-shell">
        <aside className="login-brand">
          <div className="login-brand-mark">
            <Leaf size={28} />
          </div>
          <p className="login-kicker">Ayurvedic manufacturing ERP</p>
          <h1>Billvice</h1>
          <p className="login-lead">
            Billing, stock, purchase, manufacturing and ledgers — one secure workspace for your factory.
          </p>
          <ul className="login-points">
            <li><ShieldCheck size={16} /> Secure sign-in for your workspace</li>
            <li><ShieldCheck size={16} /> GST billing, POS and party ledger</li>
            <li><ShieldCheck size={16} /> Raw materials, recipes and production</li>
          </ul>
        </aside>

        <form className="login-card" onSubmit={submit}>
          <div className="login-card-head">
            <h2>Welcome back</h2>
            <p>Sign in with your Billvice account</p>
          </div>

          <label className="login-label" htmlFor="login-user">Username</label>
          <div className="login-field">
            <User size={18} />
            <input
              id="login-user"
              autoComplete="username"
              autoFocus
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Enter username"
            />
          </div>

          <label className="login-label" htmlFor="login-pass">Password</label>
          <div className="login-field">
            <Lock size={18} />
            <input
              id="login-pass"
              type={showPass ? 'text' : 'password'}
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter password"
            />
            <button type="button" className="login-eye" onClick={() => setShowPass((v) => !v)} aria-label="Show password">
              {showPass ? <EyeOff size={18} /> : <Eye size={18} />}
            </button>
          </div>

          {error && <div className="login-error">{error}</div>}

          <button type="submit" className="login-submit" disabled={busy}>
            {busy ? 'Signing in…' : 'Sign in to Billvice'}
            {!busy && <ArrowRight size={18} />}
          </button>
        </form>
      </div>

      <style>{`
        .login-screen {
          min-height: 100vh;
          position: relative;
          overflow: hidden;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 28px 18px;
          background:
            radial-gradient(1200px 600px at -10% -20%, rgba(13, 148, 136, 0.28), transparent 55%),
            radial-gradient(900px 500px at 110% 10%, rgba(14, 116, 144, 0.22), transparent 50%),
            linear-gradient(165deg, #042f2e 0%, #0f766e 42%, #134e4a 100%);
        }
        .login-blob {
          position: absolute;
          border-radius: 50%;
          filter: blur(40px);
          pointer-events: none;
        }
        .login-blob-a {
          width: 280px; height: 280px; left: 8%; bottom: -80px;
          background: rgba(45, 212, 191, 0.25);
        }
        .login-blob-b {
          width: 220px; height: 220px; right: 6%; top: -60px;
          background: rgba(153, 246, 228, 0.18);
        }
        .login-loading {
          color: #ecfdf5; font-weight: 800; letter-spacing: -0.02em;
        }
        .login-shell {
          width: 100%;
          max-width: 920px;
          display: grid;
          grid-template-columns: 1.05fr 1fr;
          background: rgba(255,255,255,0.08);
          border: 1px solid rgba(255,255,255,0.16);
          border-radius: 24px;
          overflow: hidden;
          box-shadow: 0 30px 80px rgba(2, 44, 34, 0.35);
          position: relative;
          z-index: 1;
        }
        .login-brand {
          padding: 40px 36px;
          color: #f0fdfa;
          background:
            linear-gradient(180deg, rgba(15,118,110,0.35), rgba(4,47,46,0.55));
        }
        .login-brand-mark {
          width: 52px; height: 52px; border-radius: 16px;
          display: flex; align-items: center; justify-content: center;
          background: #ccfbf1; color: #0f766e;
          margin-bottom: 22px;
        }
        .login-kicker {
          font-size: 11px; font-weight: 800; letter-spacing: 0.14em;
          text-transform: uppercase; color: #99f6e4; margin-bottom: 8px;
        }
        .login-brand h1 {
          font-size: 2.15rem; color: #fff; margin-bottom: 12px;
        }
        .login-lead {
          color: rgba(240,253,250,0.82); font-size: 0.92rem; max-width: 34ch;
          margin-bottom: 28px;
        }
        .login-points {
          list-style: none; display: flex; flex-direction: column; gap: 10px;
        }
        .login-points li {
          display: flex; align-items: center; gap: 10px;
          font-size: 0.82rem; font-weight: 600; color: #ccfbf1;
        }
        .login-card {
          background: #fff;
          padding: 36px 32px;
        }
        .login-card-head h2 {
          font-size: 1.35rem; margin-bottom: 4px;
        }
        .login-card-head p {
          margin-bottom: 18px;
        }
        .login-eye {
          border: 0; background: transparent; color: #0f766e; cursor: pointer;
          display: inline-flex; align-items: center; justify-content: center;
          height: 28px; width: 28px; border-radius: 8px;
        }
        .login-eye:hover { background: #ccfbf1; }
        .login-label {
          display: block; font-size: 12px; font-weight: 800; color: #334155;
          margin: 0 0 6px;
        }
        .login-field {
          display: flex; align-items: center; gap: 10px;
          border: 1.5px solid #e2e8f0; border-radius: 12px;
          padding: 0 12px; height: 48px; margin-bottom: 14px;
          background: #f8fafc; color: #64748b;
        }
        .login-field:focus-within {
          border-color: #0f766e; background: #fff;
          box-shadow: 0 0 0 4px rgba(15,118,110,0.12);
          color: #0f766e;
        }
        .login-field input {
          flex: 1; border: 0; outline: none; background: transparent;
          font-size: 14px; font-weight: 600; color: #0f172a; height: 100%;
        }
        .login-error {
          background: #fef2f2; color: #b91c1c; border: 1px solid #fecaca;
          border-radius: 10px; padding: 10px 12px; font-size: 13px;
          font-weight: 700; margin-bottom: 12px;
        }
        .login-submit {
          width: 100%; height: 48px; border: 0; border-radius: 12px;
          background: linear-gradient(180deg, #14b8a6, #0f766e);
          color: #fff; font-weight: 800; font-size: 15px;
          display: flex; align-items: center; justify-content: center; gap: 8px;
          cursor: pointer; box-shadow: 0 10px 20px rgba(15,118,110,0.28);
        }
        .login-submit:hover { filter: brightness(1.05); }
        .login-submit:disabled { opacity: 0.7; cursor: wait; }
        @media (max-width: 820px) {
          .login-shell { grid-template-columns: 1fr; }
          .login-brand { display: none; }
        }
      `}</style>
    </div>
  );
}
