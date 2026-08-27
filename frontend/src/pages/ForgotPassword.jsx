import { Link, useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import api from '../services/api';
import toast from 'react-hot-toast';
import logo from '../assets/logo.png';

export default function ForgotPassword() {
  const navigate = useNavigate();
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm();

  const onSubmit = async (data) => {
    try {
      await api.post('/auth/password-reset/request', { email: data.email });
      toast.success('If that email is registered, a reset link is on its way.');
      navigate('/login');
    } catch (err) {
      toast.error(err.response?.data?.message || 'Request failed. Please try again.');
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-logo">
          <img src={logo} alt="Bhavesh Solanki" className="auth-logo-img" />
          <h1>Bhavesh RTO CRM</h1>
          <p>Reset your password</p>
        </div>

        <form onSubmit={handleSubmit(onSubmit)}>
          <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 10, color: '#1e293b' }}>Forgot password?</h2>
          <p style={{ fontSize: 13, color: '#64748b', marginBottom: 18, lineHeight: 1.5 }}>
            Enter your account email and we'll send you a link to reset your password.
          </p>

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

          <button type="submit" className="btn btn-primary" style={{ width: '100%', padding: '12px', fontSize: 15, marginTop: 8 }} disabled={isSubmitting}>
            {isSubmitting ? <span className="spinner" /> : 'Send Reset Link'}
          </button>

          <div style={{ textAlign: 'center', marginTop: 18, fontSize: 13 }}>
            <Link to="/login" style={{ color: '#6366f1', textDecoration: 'none' }}>
              Back to Login
            </Link>
          </div>
        </form>
      </div>
    </div>
  );
}
