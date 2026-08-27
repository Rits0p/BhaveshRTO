import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';
import toast from 'react-hot-toast';
import logo from '../assets/logo.png';

export default function Login() {
  const { login, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  // 'credentials' → email+password form; 'otp' → 6-digit code sent by email.
  const [step, setStep] = useState('credentials');
  const [otpEmail, setOtpEmail] = useState('');

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm();

  const {
    register: registerOtp,
    handleSubmit: handleOtpSubmit,
    formState: { errors: otpErrors, isSubmitting: otpSubmitting },
  } = useForm();

  useEffect(() => {
    if (isAuthenticated) {
      navigate('/dashboard', { replace: true });
    }
  }, [isAuthenticated, navigate]);

  const onCredentialsSubmit = async (data) => {
    try {
      const res = await api.post('/auth/login', {
        email: data.email,
        password: data.password,
      }, { withCredentials: true });

      if (res.data.otp_required) {
        setOtpEmail(data.email);
        setStep('otp');
        toast.success(res.data.message || 'Login code sent to your email.');
      }
    } catch (err) {
      toast.error(err.response?.data?.message || 'Login failed');
    }
  };

  const onOtpSubmit = async (data) => {
    try {
      const res = await api.post('/auth/login/verify-otp', {
        email: otpEmail,
        otp: data.otp.trim(),
      }, { withCredentials: true });

      login(res.data.user);
      toast.success('Welcome back!');
      navigate('/dashboard');
    } catch (err) {
      toast.error(err.response?.data?.message || 'Invalid code');
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-logo">
          <img src={logo} alt="Bhavesh Solanki" className="auth-logo-img" />
          <h1>Bhavesh RTO CRM</h1>
          <p>RTO & Insurance Advisor Portal</p>
        </div>

        {step === 'credentials' && (
          <form onSubmit={handleSubmit(onCredentialsSubmit)}>
            <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 20, color: '#1e293b' }}>Sign in to your account</h2>

            <div className="form-group">
              <label className="form-label">Email Address</label>
              <input
                type="email"
                className={`form-control ${errors.email ? 'error' : ''}`}
                placeholder="admin@example.com"
                {...register('email', { required: 'Email is required', pattern: { value: /\S+@\S+\.\S+/, message: 'Invalid email' } })}
              />
              {errors.email && <p className="form-error">{errors.email.message}</p>}
            </div>

            <div className="form-group">
              <label className="form-label">Password</label>
              <input
                type="password"
                className={`form-control ${errors.password ? 'error' : ''}`}
                placeholder="••••••••"
                {...register('password', { required: 'Password is required' })}
              />
              {errors.password && <p className="form-error">{errors.password.message}</p>}
            </div>

            <button type="submit" className="btn btn-primary" style={{ width: '100%', padding: '12px', fontSize: 15, marginTop: 8 }} disabled={isSubmitting}>
              {isSubmitting ? <span className="spinner" /> : 'Sign In →'}
            </button>
          </form>
        )}

        {step === 'otp' && (
          <form onSubmit={handleOtpSubmit(onOtpSubmit)}>
            <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 10, color: '#1e293b' }}>Enter login code</h2>
            <p style={{ fontSize: 13, color: '#64748b', marginBottom: 18, lineHeight: 1.5 }}>
              We emailed a 6-digit code to <strong>{otpEmail}</strong>. It expires in 5 minutes.
            </p>

            <div className="form-group">
              <label className="form-label">6-Digit Code</label>
              <input
                type="text"
                inputMode="numeric"
                autoComplete="one-time-code"
                maxLength={6}
                className={`form-control ${otpErrors.otp ? 'error' : ''}`}
                placeholder="••••••"
                style={{ textAlign: 'center', fontSize: 22, letterSpacing: 8 }}
                {...registerOtp('otp', {
                  required: 'Code is required',
                  pattern: { value: /^\d{6}$/, message: 'Enter the 6-digit code' },
                })}
              />
              {otpErrors.otp && <p className="form-error">{otpErrors.otp.message}</p>}
            </div>

            <button type="submit" className="btn btn-primary" style={{ width: '100%', padding: '12px', fontSize: 15, marginTop: 8 }} disabled={otpSubmitting}>
              {otpSubmitting ? <span className="spinner" /> : 'Verify Code →'}
            </button>

            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 18, fontSize: 13 }}>
              <button
                type="button"
                onClick={() => setStep('credentials')}
                style={{ background: 'none', border: 'none', color: '#6366f1', cursor: 'pointer', padding: 0, fontSize: 13 }}
              >
                ← Use a different account
              </button>
              <Link to="/forgot-password" style={{ color: '#6366f1', textDecoration: 'none' }}>
                Forgot password?
              </Link>
            </div>
          </form>
        )}

        {step === 'credentials' && (
          <div style={{ textAlign: 'center', marginTop: 18, fontSize: 13 }}>
            <Link to="/forgot-password" style={{ color: '#6366f1', textDecoration: 'none' }}>
              Forgot password?
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
