import { useEffect, useState, useCallback } from 'react';
import api from '../services/api';
import toast from 'react-hot-toast';
import Pagination from '../components/Pagination';
import { useLayout } from '../context/LayoutContext';

const EMPTY_FORM = { customer_id: '', text: '' };

export default function Remarks() {
  const [remarks, setRemarks] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [search, setSearch] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const ITEMS_PER_PAGE = 10;

  const [showModal, setShowModal] = useState(false);
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const { setHeaderActions } = useLayout();

  const load = useCallback(async (showLoader = false) => {
    if (showLoader) { setLoading(true); } else { setRefreshing(true); }
    try {
      const [remarksRes, customersRes] = await Promise.all([
        api.get('/remarks'),
        api.get('/customers', { params: { page_size: '10000' } }),
      ]);
      setRemarks(remarksRes.data.data);
      setCustomers(customersRes.data.data);
    } catch {
      toast.error('Failed to load remarks');
    } finally {
      if (showLoader) { setLoading(false); } else { setRefreshing(false); }
    }
  }, []);

  useEffect(() => { load(true); }, [load]);

  const openCreate = useCallback(() => {
    setEditing(null);
    setForm(EMPTY_FORM);
    setShowModal(true);
  }, []);

  // Register the "Add Remark" action into the shared top bar
  useEffect(() => {
    setHeaderActions(
      <button className="btn btn-primary" onClick={openCreate} style={{ flexShrink: 0 }}>
        <svg width="15" height="15" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" style={{ marginRight: 6 }}>
          <line x1="12" y1="5" x2="12" y2="19" />
          <line x1="5" y1="12" x2="19" y2="12" />
        </svg>
        Add Remark
      </button>
    );
    return () => setHeaderActions(null);
  }, [setHeaderActions, openCreate]);

  const openEdit = (r) => {
    setEditing(r);
    setForm({ customer_id: r.customer, text: r.text });
    setShowModal(true);
  };

  const closeModal = () => { if (!saving) setShowModal(false); };

  const handleFormChange = (e) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.customer_id) { toast.error('Please select a customer.'); return; }
    if (!form.text.trim()) { toast.error('Remark text is required.'); return; }

    setSaving(true);
    try {
      if (editing) {
        await api.put(`/remarks/${editing.id}`, { customer: form.customer_id, text: form.text.trim() });
        toast.success('Remark updated.');
      } else {
        await api.post('/remarks', { customer: form.customer_id, text: form.text.trim() });
        toast.success('Remark added.');
      }
      setShowModal(false);
      load(false);
    } catch {
      toast.error(editing ? 'Failed to update remark.' : 'Failed to add remark.');
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (r) => {
    if (!window.confirm(`Delete this remark for "${r.customer_name}"? This cannot be undone.`)) return;
    try {
      await api.delete(`/remarks/${r.id}`);
      toast.success('Remark deleted.');
      load(false);
    } catch {
      toast.error('Failed to delete remark.');
    }
  };

  const customerMap = new Map(customers.map((c) => [c.id, c]));

  const filtered = remarks.filter((r) => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      (r.customer_name || '').toLowerCase().includes(q) ||
      (r.vehicle_number || '').toLowerCase().includes(q) ||
      (r.text || '').toLowerCase().includes(q)
    );
  });

  useEffect(() => {
    setCurrentPage(1);
  }, [search]);

  if (loading) return (
    <div className="app-content">
      <div style={{ display: 'flex', justifyContent: 'center', padding: 80 }}>
        <div className="spinner" style={{ width: 36, height: 36, border: '3px solid #e2e8f0', borderTopColor: '#1e3a5f' }} />
      </div>
    </div>
  );

  return (
    <div className="app-content">
      {/* Table card */}
      <div className="card">
        <div className="card-header" style={{ flexWrap: 'wrap', gap: 12, paddingBottom: 12 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <h2 className="card-title" style={{ margin: 0 }}>All Remarks</h2>
            {refreshing && <span className="spinner" style={{ width: 14, height: 14, borderTopColor: '#1e3a5f', borderColor: '#e2e8f0' }} />}
          </div>
          <input
            className="form-control"
            style={{ width: 240, height: 34, padding: '0 13px', flex: '0 0 auto', marginLeft: 'auto' }}
            placeholder="Search customer, vehicle, remark..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <div className="card-body" style={{ padding: 0 }}>
          {remarks.length === 0 ? (
            <div className="empty-state">
              <svg width="56" height="56" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24">
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
              </svg>
              <h3>No remarks yet</h3>
              <p>Click "Add Remark" to save a note against a customer.</p>
            </div>
          ) : (
            <div className="table-wrapper" style={{ borderRadius: 0, border: 'none', borderTop: '1px solid #e2e8f0', opacity: refreshing ? 0.9 : 1, transition: 'opacity 0.2s ease' }}>
              <table>
                <thead>
                  <tr>
                    <th style={{ width: 45 }}>#</th>
                    <th>Customer</th>
                    <th>Vehicle No.</th>
                    <th>Remark</th>
                    <th>Date</th>
                    <th style={{ textAlign: 'center', width: 110 }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.length === 0 ? (
                    <tr>
                      <td colSpan={6} style={{ textAlign: 'center', padding: 40, color: '#94a3b8' }}>
                        No remarks match your search.
                      </td>
                    </tr>
                  ) : filtered.slice((currentPage - 1) * ITEMS_PER_PAGE, currentPage * ITEMS_PER_PAGE).map((r, i) => (
                    <tr key={r.id}>
                      <td style={{ color: '#94a3b8', fontSize: 12 }}>{(currentPage - 1) * ITEMS_PER_PAGE + i + 1}</td>
                      <td style={{ fontWeight: 600, color: '#0f172a' }}>
                        {r.customer_name || (customerMap.get(r.customer)?.name || '—')}
                        <span style={{ display: 'block', fontSize: 12, fontWeight: 400, color: '#94a3b8' }}>
                          {customerMap.get(r.customer)?.contact_number || ''}
                        </span>
                      </td>
                      <td style={{ fontSize: 13, color: '#475569', fontFamily: 'monospace' }}>
                        {r.vehicle_number || customerMap.get(r.customer)?.vehicle_number || '—'}
                      </td>
                      <td style={{ color: '#334155', maxWidth: 380, whiteSpace: 'normal' }}>{r.text}</td>
                      <td style={{ fontSize: 13, color: '#64748b', whiteSpace: 'nowrap' }}>
                        {new Date(r.created_at).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })}
                      </td>
                      <td style={{ textAlign: 'center' }}>
                        <div style={{ display: 'flex', gap: 6, justifyContent: 'center' }}>
                          <button className="btn btn-ghost btn-sm" onClick={() => openEdit(r)}>Edit</button>
                          <button className="btn btn-danger-ghost btn-sm" onClick={() => handleDelete(r)} title="Delete">
                            <svg width="13" height="13" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                              <polyline points="3 6 5 6 21 6" />
                              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                              <line x1="10" y1="11" x2="10" y2="17" />
                              <line x1="14" y1="11" x2="14" y2="17" />
                            </svg>
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
        {!loading && filtered.length > 0 && (
          <Pagination
            currentPage={currentPage}
            totalItems={filtered.length}
            pageSize={ITEMS_PER_PAGE}
            onPageChange={setCurrentPage}
          />
        )}
      </div>

      {/* Add / Edit Remark Modal */}
      {showModal && (
        <div className="modal-overlay" onClick={(e) => { if (e.target === e.currentTarget) closeModal(); }} style={{ zIndex: 1000 }}>
          <div className="modal" style={{ maxWidth: 520, width: '100%' }} onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3 className="modal-title">{editing ? 'Edit Remark' : 'Add Remark'}</h3>
              <button className="btn btn-ghost btn-sm" onClick={closeModal} disabled={saving} aria-label="Close">
                <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                  <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            </div>

            <div className="modal-body">
              <form onSubmit={handleSubmit}>
                <div style={{ marginBottom: 16 }}>
                  <label className="form-label" htmlFor="rm-customer">Customer <span style={{ color: '#e11d48' }}>*</span></label>
                  <select id="rm-customer" className="form-control" name="customer_id" value={form.customer_id} onChange={handleFormChange} required>
                    <option value="">-- Select a customer --</option>
                    {customers.map((c) => (
                      <option key={c.id} value={c.id}>{c.name} {c.vehicle_number ? `(${c.vehicle_number})` : ''}</option>
                    ))}
                  </select>
                </div>
                <div style={{ marginBottom: 16 }}>
                  <label className="form-label" htmlFor="rm-text">Remark <span style={{ color: '#e11d48' }}>*</span></label>
                  <textarea
                    id="rm-text"
                    className="form-control"
                    name="text"
                    value={form.text}
                    onChange={handleFormChange}
                    placeholder="Enter your remark..."
                    rows={4}
                    style={{ resize: 'vertical', minHeight: 90 }}
                    required
                  />
                </div>
                <div className="modal-footer" style={{ paddingTop: 16, borderTop: '1px solid #e2e8f0' }}>
                  <button type="button" className="btn btn-ghost" onClick={closeModal} disabled={saving}>Cancel</button>
                  <button type="submit" className="btn btn-primary" disabled={saving}>
                    {saving ? (
                      <><span className="spinner" style={{ borderColor: 'rgba(255,255,255,0.3)', borderTopColor: '#fff', width: 14, height: 14, marginRight: 8 }} />Saving...</>
                    ) : (
                      editing ? 'Save Changes' : 'Save Remark'
                    )}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
