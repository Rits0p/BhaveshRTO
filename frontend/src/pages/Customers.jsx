import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import toast from 'react-hot-toast';
import * as XLSX from 'xlsx';
import Pagination from '../components/Pagination';
import { useLayout } from '../context/LayoutContext';

const CATEGORY_LABELS = {
  insurance: 'Insurance',
  permit: 'Permit',
  fitness: 'Fitness',
  puc: 'PUC',
  tax: 'Tax',
  license: 'License',
};

const CATEGORY_COLORS = {
  insurance: 'badge-info',
  permit: 'badge-success',
  fitness: 'badge-warning',
  puc: 'badge-info',
  tax: 'badge-danger',
  license: 'badge-danger',
};

const MONTH_LABELS = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
];

export default function Customers() {
  const [customers, setCustomers] = useState([]);
  const [currentPage, setCurrentPage] = useState(1);
  const ITEMS_PER_PAGE = 10;
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [search, setSearch] = useState('');
  const [monthFrom, setMonthFrom] = useState('');
  const [monthTo, setMonthTo] = useState('');
  const [remarksModal, setRemarksModal] = useState(null); // { customer, remarks, loading }
  const [editingRemarkId, setEditingRemarkId] = useState(null);
  const [editingRemarkText, setEditingRemarkText] = useState('');
  const [savingRemark, setSavingRemark] = useState(false);
  const navigate = useNavigate();
  const { setHeaderActions } = useLayout();

  // Register the "Add Customer" action into the shared top bar
  useEffect(() => {
    setHeaderActions(
      <button className="btn btn-primary" onClick={() => navigate('/customers/new')}>
        <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
          <line x1="12" y1="5" x2="12" y2="19" />
          <line x1="5" y1="12" x2="19" y2="12" />
        </svg>
        Add Customer
      </button>
    );
    return () => setHeaderActions(null);
  }, [setHeaderActions, navigate]);

  // A reversed range (e.g. To=Mar, From=Jun) is swapped so the user still
  // gets the span they meant instead of an empty result.
  const effectiveMonthRange = () => {
    let from = monthFrom;
    let to = monthTo;
    if (from && to && Number(from) > Number(to)) {
      [from, to] = [to, from];
    }
    return { from, to };
  };

  const loadCustomers = useCallback(async (showLoader = false) => {
    if (showLoader) {
      setLoading(true);
    } else {
      setRefreshing(true);
    }

    try {
      const params = new URLSearchParams();
      if (search) params.set('search', search);
      const { from, to } = effectiveMonthRange();
      if (from) params.set('month_from', from);
      if (to) params.set('month_to', to);
      params.set('page_size', '10000');
      params.set('_refresh', Date.now().toString());
      const res = await api.get('/customers', {
        params,
      });
      setCustomers(res.data.data);
    } catch {
      toast.error('Failed to load customers');
    } finally {
      if (showLoader) {
        setLoading(false);
      } else {
        setRefreshing(false);
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search, monthFrom, monthTo]);

  useEffect(() => {
    setCurrentPage(1);
  }, [search, monthFrom, monthTo]);

  useEffect(() => {
    loadCustomers(true);
    const refreshWhenVisible = () => {
      if (document.visibilityState === 'visible') loadCustomers();
    };
    document.addEventListener('visibilitychange', refreshWhenVisible);
    const refreshTimer = window.setInterval(loadCustomers, 5000);
    return () => {
      document.removeEventListener('visibilitychange', refreshWhenVisible);
      window.clearInterval(refreshTimer);
    };
  }, [loadCustomers]);

  const handleDelete = async (id, name) => {
    if (!window.confirm(`Delete customer "${name}"? This cannot be undone.`)) return;
    try {
      await api.delete(`/customers/${id}`);
      toast.success('Customer deleted');
      loadCustomers();
    } catch {
      toast.error('Delete failed');
    }
  };

  // Exports exactly what the table is showing (search + month filtered set)
  // to a real .xlsx workbook via SheetJS.
  const handleDownloadExcel = () => {
    if (customers.length === 0) {
      toast.error('No records to download.');
      return;
    }
    const rows = customers.map((c) => ({
      'Name': c.name,
      'Contact Number': c.contact_number,
      'Categories': (c.categories?.length ? c.categories : [c.category])
        .map((category) => CATEGORY_LABELS[category] || category).join(', '),
      'Vehicle No.': c.vehicle_number || '',
      'Reference Name': c.reference_name || '',
      'Start Date': c.start_date ? new Date(c.start_date).toLocaleDateString('en-IN') : '',
      'End Date': c.end_date ? new Date(c.end_date).toLocaleDateString('en-IN') : '',
      'Total Amount': parseFloat(c.amount_total || 0),
      'Paid Amount': parseFloat(c.amount_paid || 0),
      'Pending Amount': parseFloat(c.amount_pending || 0),
      'Remarks Count': c.remarks_count || 0,
      'Latest Remark': c.latest_remark || '',
    }));
    const sheet = XLSX.utils.json_to_sheet(rows);
    sheet['!cols'] = [
      { wch: 26 }, { wch: 16 }, { wch: 18 }, { wch: 14 }, { wch: 18 },
      { wch: 12 }, { wch: 12 }, { wch: 13 }, { wch: 13 }, { wch: 14 },
      { wch: 14 }, { wch: 40 },
    ];
    const book = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(book, sheet, 'Customers');
    const { from: exportFrom, to: exportTo } = effectiveMonthRange();
    const monthPart = exportFrom || exportTo
      ? `-${MONTH_LABELS[Number(exportFrom || '1') - 1].slice(0, 3)}-${MONTH_LABELS[Number(exportTo || '12') - 1].slice(0, 3)}`
      : '';
    XLSX.writeFile(book, `customers${monthPart}-${new Date().toISOString().slice(0, 10)}.xlsx`);
    toast.success(`Downloaded ${rows.length} record${rows.length !== 1 ? 's' : ''}.`);
  };

  // Opens a modal with this customer's remarks instead of navigating away
  const openRemarks = async (c) => {
    setEditingRemarkId(null);
    setRemarksModal({ customer: c, remarks: [], loading: true });
    try {
      const res = await api.get('/remarks');
      const remarks = (res.data.data || []).filter((r) => r.customer === c.id);
      setRemarksModal({ customer: c, remarks, loading: false });
    } catch {
      toast.error('Failed to load remarks.');
      setRemarksModal((prev) => (prev ? { ...prev, loading: false } : prev));
    }
  };

  const startEditRemark = (r) => {
    setEditingRemarkId(r.id);
    setEditingRemarkText(r.text);
  };

  const handleSaveRemark = async (r) => {
    if (!editingRemarkText.trim()) {
      toast.error('Remark text is required.');
      return;
    }
    setSavingRemark(true);
    try {
      const res = await api.patch(`/remarks/${r.id}`, { text: editingRemarkText.trim() });
      setRemarksModal((prev) => (prev ? {
        ...prev,
        remarks: prev.remarks.map((x) => (x.id === r.id ? res.data.data : x)),
      } : prev));
      toast.success('Remark updated.');
      setEditingRemarkId(null);
      loadCustomers();
    } catch {
      toast.error('Failed to update remark.');
    } finally {
      setSavingRemark(false);
    }
  };

  return (
    <div className="app-content">
      {/* Filters */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-body" style={{ padding: '14px 20px', display: 'flex', gap: 12, flexWrap: 'wrap' }}>
          <input
            className="form-control"
            style={{ maxWidth: 280 }}
            placeholder="Search by name, contact, vehicle, reference…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <select
            className="form-control"
            style={{ maxWidth: 140 }}
            value={monthFrom}
            onChange={(e) => setMonthFrom(e.target.value)}
          >
            <option value="">From Month</option>
            {MONTH_LABELS.map((label, index) => (
              <option key={label} value={index + 1}>{label}</option>
            ))}
          </select>
          <select
            className="form-control"
            style={{ maxWidth: 140 }}
            value={monthTo}
            onChange={(e) => setMonthTo(e.target.value)}
          >
            <option value="">To Month</option>
            {MONTH_LABELS.map((label, index) => (
              <option key={label} value={index + 1}>{label}</option>
            ))}
          </select>
          {!(monthFrom === '1' && monthTo === '12') ? (
            <button
              className="btn btn-ghost"
              style={{ whiteSpace: 'nowrap' }}
              onClick={() => { setMonthFrom('1'); setMonthTo('12'); }}
              title="Show everything entered this year"
            >
              Full Year
            </button>
          ) : (
            <button
              className="btn btn-ghost"
              style={{ whiteSpace: 'nowrap', color: '#1e3a5f', fontWeight: 600 }}
              onClick={() => { setMonthFrom(''); setMonthTo(''); }}
              title="Clear month range"
            >
              Full Year ✕
            </button>
          )}
          <span style={{ alignSelf: 'center', fontSize: 13, color: '#64748b' }}>
            {customers.length} record{customers.length !== 1 ? 's' : ''}
          </span>
          <button
            className="btn btn-primary"
            style={{ marginLeft: 'auto' }}
            onClick={handleDownloadExcel}
            disabled={loading || customers.length === 0}
            title="Download the currently filtered table as Excel"
          >
            <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2.5" viewBox="0 0 24 24">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="7 10 12 15 17 10" />
              <line x1="12" y1="15" x2="12" y2="3" />
            </svg>
            Download Excel
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="card">
        {loading ? (
          <div style={{ padding: 60, textAlign: 'center' }}>
            <div className="spinner" style={{ width: 32, height: 32, border: '3px solid #e2e8f0', borderTopColor: '#1e3a5f', margin: '0 auto' }} />
          </div>
        ) : customers.length === 0 ? (
          <div className="empty-state">
            <svg width="56" height="56" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24">
              <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" />
            </svg>
            <h3>No customers yet</h3>
            <p>Click "Add Customer" to create your first record.</p>
          </div>
        ) : (
          <div className="table-wrapper" style={{ opacity: refreshing ? 0.9 : 1, transition: 'opacity 0.2s ease' }}>
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Contact</th>
                  <th>Category</th>
                  <th>Vehicle No.</th>
                  <th>End Date</th>
                  <th>Total</th>
                  <th>Paid</th>
                  <th>Pending</th>
                  <th>Remarks</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {customers.slice((currentPage - 1) * ITEMS_PER_PAGE, currentPage * ITEMS_PER_PAGE).map((c) => (
                  <tr key={c.id}>
                    <td style={{ fontWeight: 600 }}>{c.name}</td>
                    <td>{c.contact_number}</td>
                    <td>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                        {(c.categories?.length ? c.categories : [c.category]).map((category) => (
                          <span key={category} className={`badge ${CATEGORY_COLORS[category]}`}>
                            {CATEGORY_LABELS[category]}
                          </span>
                        ))}
                      </div>
                    </td>
                    <td>{c.vehicle_number || '—'}</td>
                    <td>{c.end_date ? new Date(c.end_date).toLocaleDateString('en-IN') : '—'}</td>
                    <td>₹{parseFloat(c.amount_total).toLocaleString('en-IN')}</td>
                    <td style={{ color: '#059669' }}>₹{parseFloat(c.amount_paid).toLocaleString('en-IN')}</td>
                    <td style={{ color: parseFloat(c.amount_pending) > 0 ? '#d97706' : '#059669', fontWeight: 600 }}>
                      ₹{parseFloat(c.amount_pending || 0).toLocaleString('en-IN')}
                    </td>
                    <td>
                      {c.remarks_count > 0 ? (
                        <button
                          className="btn btn-ghost btn-sm"
                          onClick={() => openRemarks(c)}
                          title="View remarks"
                          style={{ width: 200, whiteSpace: 'normal', textAlign: 'left', justifyContent: 'flex-start' }}
                        >
                          <span className="badge badge-warning" style={{ fontSize: 10, padding: '1px 6px' }}>{c.remarks_count}</span>
                          <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', display: '-webkit-box', WebkitLineClamp: 1, WebkitBoxOrient: 'vertical' }}>
                            {c.latest_remark}
                          </span>
                        </button>
                      ) : (
                        <span style={{ color: '#94a3b8' }}>—</span>
                      )}
                    </td>
                    <td>
                      <div style={{ display: 'flex', gap: 6 }}>
                        <button className="btn btn-ghost btn-sm" onClick={() => navigate(`/customers/${c.id}/edit`)}>Edit</button>
                        <button className="btn btn-danger-ghost btn-sm" onClick={() => handleDelete(c.id, c.name)} title="Delete">
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
        {!loading && customers.length > 0 && (
          <Pagination
            currentPage={currentPage}
            totalItems={customers.length}
            pageSize={ITEMS_PER_PAGE}
            onPageChange={setCurrentPage}
          />
        )}
      </div>

      {/* Remarks modal */}
      {remarksModal && (
        <div className="modal-overlay" onClick={(e) => { if (e.target === e.currentTarget) setRemarksModal(null); }} style={{ zIndex: 1000 }}>
          <div className="modal" style={{ maxWidth: 520, width: '100%', maxHeight: '80vh', display: 'flex', flexDirection: 'column' }} onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3 className="modal-title">Remarks — {remarksModal.customer?.name || ''}</h3>
              <button className="btn btn-ghost btn-sm" onClick={() => setRemarksModal(null)} aria-label="Close">
                <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                  <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            </div>
            <div className="modal-body" style={{ overflowY: 'auto' }}>
              {remarksModal.loading ? (
                <div style={{ display: 'flex', justifyContent: 'center', padding: 30 }}>
                  <div className="spinner" style={{ width: 28, height: 28, border: '3px solid #e2e8f0', borderTopColor: '#1e3a5f' }} />
                </div>
              ) : remarksModal.remarks.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '24px 0', color: '#94a3b8' }}>
                  No remarks for this customer.
                </div>
              ) : (
                remarksModal.remarks.map((r) => (
                  <div key={r.id} style={{
                    padding: '12px 14px', borderRadius: 10, border: '1px solid #e2e8f0',
                    background: '#f8fafc', marginBottom: 10,
                  }}>
                    {editingRemarkId === r.id ? (
                      <>
                        <textarea
                          className="form-control"
                          value={editingRemarkText}
                          onChange={(e) => setEditingRemarkText(e.target.value)}
                          rows={3}
                          autoFocus
                          disabled={savingRemark}
                          style={{ resize: 'vertical', minHeight: 70, fontSize: 14 }}
                        />
                        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 10 }}>
                          <button
                            className="btn btn-ghost btn-sm"
                            onClick={() => setEditingRemarkId(null)}
                            disabled={savingRemark}
                          >
                            Cancel
                          </button>
                          <button
                            className="btn btn-primary btn-sm"
                            onClick={() => handleSaveRemark(r)}
                            disabled={savingRemark || !editingRemarkText.trim()}
                          >
                            {savingRemark ? (
                              <><span className="spinner" style={{ borderColor: 'rgba(255,255,255,0.3)', borderTopColor: '#fff', width: 12, height: 12, marginRight: 6 }} />Saving...</>
                            ) : (
                              'Save'
                            )}
                          </button>
                        </div>
                      </>
                    ) : (
                      <>
                        <p style={{ margin: 0, fontSize: 14, color: '#0f172a', lineHeight: 1.5, whiteSpace: 'pre-wrap' }}>{r.text}</p>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 8 }}>
                          <p style={{ margin: 0, fontSize: 11.5, color: '#94a3b8' }}>
                            {new Date(r.created_at).toLocaleString('en-IN', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })}
                          </p>
                          <button
                            className="btn btn-ghost btn-sm"
                            onClick={() => startEditRemark(r)}
                            title="Edit remark"
                          >
                            <svg width="13" height="13" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                              <path d="M17 3a2.828 2.828 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z" />
                            </svg>
                            Edit
                          </button>
                        </div>
                      </>
                    )}
                  </div>
                ))
              )}
            </div>
            <div className="modal-footer" style={{ paddingTop: 14, borderTop: '1px solid #e2e8f0' }}>
              <button className="btn btn-primary" onClick={() => setRemarksModal(null)}>Close</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
