import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import api from '../services/api';
import toast from 'react-hot-toast';

const CATEGORIES = [
  { value: 'insurance', label: 'Insurance' },
  { value: 'fitness', label: 'Fitness' },
  { value: 'puc', label: 'PUC' },
  { value: 'tax', label: 'Tax' },
  { value: 'permit', label: 'Permit' },
  { value: 'license', label: 'License' },
];

export default function CustomerForm({ customer, onSuccess, onClose }) {
  const isEdit = !!customer;
  const {
    register,
    handleSubmit,
    reset,
    watch,
    formState: { errors, isSubmitting },
  } = useForm({
    defaultValues: customer
      ? {
          name: customer.name,
          contact_number: customer.contact_number,
          category: customer.category,
          vehicle_number: customer.vehicle_number || '',
          start_date: customer.start_date || '',
          end_date: customer.end_date || '',
          amount_total: customer.amount_total || 0,
          amount_paid: customer.amount_paid || 0,
          notes: customer.notes || '',
        }
      : { category: 'insurance', amount_total: 0, amount_paid: 0 },
  });

  const category = watch('category');

  const onSubmit = async (data) => {
    // amount_paid is always derived server-side from actual Payment records —
    // it's never accepted as writable input on the customer endpoint itself.
    const { amount_paid, ...customerPayload } = data;
    try {
      if (isEdit) {
        await api.put(`/customers/${customer.id}`, customerPayload);
        const newPaid = Number(amount_paid || 0);
        if (newPaid !== Number(customer.amount_paid || 0)) {
          // Reconcile the Payment records so paid/pending math stays accurate.
          await api.put(`/receipts/${customer.id}/amount`, { amount_paid: newPaid });
        }
        toast.success('Customer updated successfully!');
      } else {
        const res = await api.post('/customers', customerPayload);
        const newCustomerId = res.data?.data?.id;
        const initialPaid = parseFloat(amount_paid);
        if (newCustomerId && initialPaid > 0) {
          await api.post('/payments', { customer_id: newCustomerId, amount: initialPaid });
        }
        toast.success('Customer created successfully!');
      }
      onSuccess?.();
      onClose?.();
    } catch (err) {
      const msg = err.response?.data?.message || 'Something went wrong.';
      toast.error(msg);
    }
  };

  return (
    <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose?.()}>
      <div className="modal">
        <div className="modal-header">
          <h2 className="modal-title">{isEdit ? 'Edit Customer' : 'Add New Customer'}</h2>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>

        <form onSubmit={handleSubmit(onSubmit)}>
          <div className="form-grid">
            <div className="form-group">
              <label className="form-label">Full Name *</label>
              <input
                className={`form-control ${errors.name ? 'error' : ''}`}
                placeholder="Customer full name"
                {...register('name', { required: 'Name is required' })}
              />
              {errors.name && <p className="form-error">{errors.name.message}</p>}
            </div>

            <div className="form-group">
              <label className="form-label">Contact Number *</label>
              <input
                className={`form-control ${errors.contact_number ? 'error' : ''}`}
                placeholder="+91 98765 43210"
                {...register('contact_number', { required: 'Contact number is required' })}
              />
              {errors.contact_number && <p className="form-error">{errors.contact_number.message}</p>}
            </div>
          </div>

          <div className="form-grid">
            <div className="form-group">
              <label className="form-label">Category *</label>
              <select className="form-control" {...register('category', { required: true })}>
                {CATEGORIES.map((c) => (
                  <option key={c.value} value={c.value}>{c.label}</option>
                ))}
              </select>
            </div>

            {(category === 'insurance' || category === 'permit') && (
              <div className="form-group">
                <label className="form-label">Vehicle Number</label>
                <input
                  className="form-control"
                  placeholder="GJ-01-AB-1234"
                  {...register('vehicle_number')}
                />
              </div>
            )}
          </div>

          <div className="form-grid">
            <div className="form-group">
              <label className="form-label">Start Date</label>
              <input type="date" className="form-control" {...register('start_date')} />
            </div>
            <div className="form-group">
              <label className="form-label">End / Expiry Date</label>
              <input type="date" className="form-control" {...register('end_date')} />
            </div>
          </div>

          <div className="form-grid">
            <div className="form-group">
              <label className="form-label">Total Amount (₹) *</label>
              <input
                type="number"
                step="0.01"
                min="0"
                className={`form-control ${errors.amount_total ? 'error' : ''}`}
                placeholder="0.00"
                {...register('amount_total', { required: 'Amount required', min: { value: 0, message: 'Must be ≥ 0' } })}
              />
              {errors.amount_total && <p className="form-error">{errors.amount_total.message}</p>}
            </div>
            <div className="form-group">
              <label className="form-label">
                Amount Paid (₹){isEdit ? ' — edits reconcile payment records' : ' (initial payment, optional)'}
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                className="form-control"
                placeholder="0.00"
                {...register('amount_paid')}
              />
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">Notes</label>
            <textarea
              className="form-control"
              rows={2}
              placeholder="Optional notes..."
              {...register('notes')}
            />
          </div>

          <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end', marginTop: 8 }}>
            <button type="button" className="btn btn-ghost" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={isSubmitting}>
              {isSubmitting ? <span className="spinner" /> : (isEdit ? 'Save Changes' : 'Create Customer')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
