import { useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import api from '../services/api';
import toast from 'react-hot-toast';
import logo from '../assets/logo.png';

export default function ResetPassword() {
  const [searchParams] = useSearchParams();
  const [done, setDone] = useState(false);
  const { register, handleSubmit, watch, formState: { errors, isSubmitting } } = useForm();

  const uid = searchParams.get('uid');
  const token = searchParams.get('token');

  const onSubmit = async (data) => {
    try {
      await api.post('/auth/password-reset/confirm', {
        uid,
        token,
        new_password: data.new_password,
      });
      setDone(true);
      toast.success('Password has been reset. You can now log in.');
    } catch (err) {
      toast.error(err.response?.data?.message || 'Reset failed. The link may have expired.');
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-logo">
          <img src={logo} alt="Bhavesh Solanki" className="auth-logo-img" />
          <h1>Bhavesh RTO CRM</h1>
          <p>Set a new password</p>
        </div>

        {done ? (
          <div style={{ textAlign: 'center' }}>
            <div style={{ width: 48, height: 48, borderRadius: '50%', background: '#dcfce7', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', fontSize: 24, marginBottom: 14 }}>
              ✓
            </div>
            <p style={{ fontSize: 14, color: '#166534', lineHeight: 1.5 }}>Your password has been reset successfully.</p>
            <Link to="/login" className="btn btn-primary" style={{ width: '100%', padding: '12px', fontSize: 15, marginTop: 20, textAlign: 'center', textDecoration: 'none' }}>
              Go to Login
            </Link>
          </div>
        ) : !uid || !token ? (
          <div style={{ textAlign: 'center' }}>
            <p style={{ fontSize: 14, color: '#b91c1c', lineHeight: 1.5 }}>
              This reset link is incomplete or has expired. Please request a new one.
            </p>
            <Link to="/forgot-password" className="btn btn-primary" style={{ width: '100%', padding: '12px', fontSize: 15, marginTop: 20, textAlign: 'center', textDecoration: 'none' }}>
              Request New Link
            </Link>
          </div>
        ) : (
          <form onSubmit={handleSubmit(onSubmit)}>
            <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 10, color: '#1e293b' }}>Choose a new password</h2>
            <p style={{ fontSize: 13, color: '#64748b', marginBottom: 18, lineHeight: 1.5 }}>
              This link can only be used once.
            </p>

            <div className="form-group">
              <label className="form-label">New Password</label>
              <input
                type="password"
                className={`form-control ${errors.new_password ? 'error' : ''}`}
                placeholder="Minimum 6 characters"
                {...register('new_password', { required: 'Password required', minLength: { value: 6, message: 'At least 6 characters' } })}
              />
              {errors.new_password && <p className="form-error">{errors.new_password.message}</p>}
            </div>

            <div className="form-group">
              <label className="form-label">Confirm Password</label>
              <input
                type="password"
                className={`form-control ${errors.confirm ? 'error' : ''}`}
                placeholder="Repeat your password"
                {...register('confirm', {
                  required: 'Please confirm your password',
                  validate: (value) => value === watch('new_password') || 'Passwords do not match',
                })}
              />
              {errors.confirm && <p className="form-error">{errors.confirm.message}</p>}
            </div>

            <button type="submit" className="btn btn-primary" style={{ width: '100%', padding: '12px', fontSize: 15, marginTop: 8 }} disabled={isSubmitting}>
              {isSubmitting ? <span className="spinner" /> : 'Reset Password'}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
