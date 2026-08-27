import { useEffect, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import api from '../services/api';
import logo from '../assets/logo.png';

export default function VerifyEmail() {
  const [searchParams] = useSearchParams();
  const [status, setStatus] = useState('loading'); // loading | success | error
  const [message, setMessage] = useState('');
  const fired = useRef(false);

  useEffect(() => {
    if (fired.current) return;
    fired.current = true;

    const uid = searchParams.get('uid');
    const token = searchParams.get('token');

    if (!uid || !token) {
      setStatus('error');
      setMessage('This verification link is incomplete or has expired.');
      return;
    }

    api
      .post('/auth/verify-email', { uid, token })
      .then((res) => {
        setStatus('success');
        setMessage(res.data.message || 'Email verified successfully. You can now log in.');
      })
      .catch((err) => {
        setStatus('error');
        setMessage(err.response?.data?.message || 'Verification failed. The link may have expired.');
      });
  }, [searchParams]);

  const isError = status === 'error';

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-logo">
          <img src={logo} alt="Bhavesh Solanki" className="auth-logo-img" />
          <h1>Bhavesh RTO CRM</h1>
          <p>Email verification</p>
        </div>

        {status === 'loading' && (
          <div style={{ textAlign: 'center', padding: '12px 0' }}>
            <div className="spinner" style={{ width: 28, height: 28, borderWidth: 3 }} />
            <p style={{ marginTop: 12, fontSize: 14, color: '#64748b' }}>Verifying your email…</p>
          </div>
        )}

        {status !== 'loading' && (
          <div style={{ textAlign: 'center' }}>
            <div
              style={{
                width: 48,
                height: 48,
                borderRadius: '50%',
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: 24,
                marginBottom: 14,
                background: isError ? '#fee2e2' : '#dcfce7',
              }}
            >
              {isError ? '✕' : '✓'}
            </div>
            <p style={{ fontSize: 14, color: isError ? '#b91c1c' : '#166534', lineHeight: 1.5 }}>{message}</p>
            <Link to="/login" className="btn btn-primary" style={{ width: '100%', padding: '12px', fontSize: 15, marginTop: 20, textAlign: 'center', textDecoration: 'none' }}>
              Go to Login
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
