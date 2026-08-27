import { useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import api from '../services/api';
import toast from 'react-hot-toast';

export default function ChangePassword() {
  const navigate = useNavigate();
  const { register, handleSubmit, watch, formState: { errors, isSubmitting } } = useForm();

  const onSubmit = async (data) => {
    try {
      await api.post('/auth/change-password', {
        old_password: data.old_password,
        new_password: data.new_password,
      });
      toast.success('Password changed successfully.');
      navigate('/dashboard');
    } catch (err) {
      toast.error(err.response?.data?.message || 'Password change failed');
    }
  };

  return (
    <div className="app-content">
      <div className="card" style={{ maxWidth: 480 }}>
        <div className="card-header">
          <div className="card-title">Change Password</div>
          <div className="card-description">Update the password for your admin account.</div>
        </div>
        <div className="card-body">
          <form onSubmit={handleSubmit(onSubmit)}>
            <div className="form-group">
              <label className="form-label">Current Password</label>
              <input
                type="password"
                className={`form-control ${errors.old_password ? 'error' : ''}`}
                placeholder="••••••••"
                {...register('old_password', { required: 'Current password is required' })}
              />
              {errors.old_password && <p className="form-error">{errors.old_password.message}</p>}
            </div>

            <div className="form-group">
              <label className="form-label">New Password</label>
              <input
                type="password"
                className={`form-control ${errors.new_password ? 'error' : ''}`}
                placeholder="Minimum 6 characters"
                {...register('new_password', { required: 'New password is required', minLength: { value: 6, message: 'At least 6 characters' } })}
              />
              {errors.new_password && <p className="form-error">{errors.new_password.message}</p>}
            </div>

            <div className="form-group">
              <label className="form-label">Confirm New Password</label>
              <input
                type="password"
                className={`form-control ${errors.confirm ? 'error' : ''}`}
                placeholder="Repeat your new password"
                {...register('confirm', {
                  required: 'Please confirm your new password',
                  validate: (value) => value === watch('new_password') || 'Passwords do not match',
                })}
              />
              {errors.confirm && <p className="form-error">{errors.confirm.message}</p>}
            </div>

            <div style={{ display: 'flex', gap: 10, marginTop: 8 }}>
              <button type="button" className="btn btn-ghost" onClick={() => navigate(-1)}>
                Cancel
              </button>
              <button type="submit" className="btn btn-primary" disabled={isSubmitting}>
                {isSubmitting ? <span className="spinner" /> : 'Update Password'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
