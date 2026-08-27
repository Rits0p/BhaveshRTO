import { useEffect, useState, useCallback } from 'react';
import api from '../services/api';
import toast from 'react-hot-toast';
import { useLayout } from '../context/LayoutContext';
import Pagination from '../components/Pagination';

const CATEGORY_LABELS = {
  insurance: 'Insurance',
  permit: 'Permit',
  fitness: 'Fitness',
  puc: 'PUC',
  tax: 'Tax',
  license: 'License',
  fitness_puc: 'Fitness / PUC',
};

const SERVICE_OPTIONS = [
  'Ad to Transfer',
  'Duplication',
  'HP Add',
  'HP Cancel',
  'NOC',
  'Address Change',
  'RC Particulars',
  'Alteration of Vehicle',
  'Other',
];

const METHOD_OPTIONS = ['Cash', 'Online', 'Cheque'];

// Services are stored joined by this separator (a plain CharField on the
// backend, no DB migration needed). Service names never contain a semicolon.
const SERVICE_SEPARATOR = '; ';

const EMPTY_FORM = {
  name: '',
  contact_number: '',
  vehicle_number: '',
  services: [],
  other_service: '',
  date: new Date().toISOString().slice(0, 10),
  amount_total: '',
  amount_paid: '',
  method: '',
};

// ── Filter tab options ──────────────────────────────────────────────────────
const FILTERS = [
  { key: 'all', label: 'All Receipts' },
  { key: 'customer', label: 'Customer Receipts' },
  { key: 'manual', label: 'Manual Receipts' },
];

export default function Receipts() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [pdfLoadingId, setPdfLoadingId] = useState(null);
  const [whatsappLoadingId, setWhatsappLoadingId] = useState(null);
  const [search, setSearch] = useState('');
  const [activeFilter, setActiveFilter] = useState('all');
  const [currentPage, setCurrentPage] = useState(1);
  const ITEMS_PER_PAGE = 10;
  const { setHeaderActions } = useLayout();

  // Manual receipt modal state
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [manualPdfLoading, setManualPdfLoading] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [editingType, setEditingType] = useState(null); // 'manual' | 'customer' | null

  const load = useCallback(async (showLoader = false) => {
    if (showLoader) { setLoading(true); } else { setRefreshing(true); }
    try {
      const res = await api.get('/receipts');
      setData(res.data.data);
    } catch {
      toast.error('Failed to load receipt data');
    } finally {
      if (showLoader) { setLoading(false); } else { setRefreshing(false); }
    }
  }, []);

  useEffect(() => { load(true); }, [load]);

  // ── PDF for DB customer ─────────────────────────────────────────────────
  const handleViewPDF = async (customerId) => {
    setPdfLoadingId(customerId);
    const pdfWindow = window.open('', '_blank');
    try {
      const res = await api.get(`/receipts/${customerId}/pdf`, { responseType: 'blob' });
      const url = URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }));
      if (pdfWindow) { pdfWindow.location.href = url; } else { window.open(url, '_blank'); }
      toast.success('Receipt opened — press Ctrl+P to print.');
    } catch {
      if (pdfWindow) pdfWindow.close();
      toast.error('PDF generation failed. Please try again.');
    } finally {
      setPdfLoadingId(null);
    }
  };

  // ── PDF re-download for saved manual receipt ────────────────────────────
  const handleViewManualPDF = async (receiptId) => {
    setPdfLoadingId(receiptId);
    const pdfWindow = window.open('', '_blank');
    try {
      const res = await api.get(`/receipts/manual/${receiptId}/pdf`, { responseType: 'blob' });
      const url = URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }));
      if (pdfWindow) { pdfWindow.location.href = url; } else { window.open(url, '_blank'); }
      toast.success('Receipt opened — press Ctrl+P to print.');
    } catch {
      if (pdfWindow) pdfWindow.close();
      toast.error('PDF generation failed. Please try again.');
    } finally {
      setPdfLoadingId(null);
    }
  };

  // ── Send receipt PDF via WhatsApp ──────────────────────────────────────
  const handleSendWhatsApp = async (customerId) => {
    setWhatsappLoadingId(customerId);
    try {
      const res = await api.post(`/receipts/${customerId}/send-whatsapp`);
      toast.success(res.data?.message || 'Receipt sent via WhatsApp!');
    } catch (err) {
      toast.error(err.response?.data?.message || 'Failed to send via WhatsApp.');
    } finally {
      setWhatsappLoadingId(null);
    }
  };

  const handleSendManualWhatsApp = async (receiptId) => {
    setWhatsappLoadingId(receiptId);
    try {
      const res = await api.post(`/receipts/manual/${receiptId}/send-whatsapp`);
      toast.success(res.data?.message || 'Receipt sent via WhatsApp!');
    } catch (err) {
      toast.error(err.response?.data?.message || 'Failed to send via WhatsApp.');
    } finally {
      setWhatsappLoadingId(null);
    }
  };

  // ── Manual receipt form helpers ─────────────────────────────────────────
  const amountPending = (() => {
    const total = parseFloat(form.amount_total) || 0;
    const paid = parseFloat(form.amount_paid) || 0;
    return Math.max(0, total - paid).toFixed(2);
  })();

  const handleFormChange = (e) => {
    const { name, value } = e.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const toggleService = (svc) => {
    setForm((prev) => {
      const has = prev.services.includes(svc);
      return { ...prev, services: has ? prev.services.filter((s) => s !== svc) : [...prev.services, svc] };
    });
  };

  const openModal = useCallback(() => { setEditingId(null); setEditingType(null); setForm(EMPTY_FORM); setShowModal(true); }, []);
  const closeModal = () => { if (manualPdfLoading) return; setShowModal(false); };

  // Pre-fill the modal with an existing receipt's data so the user can edit
  // it. Manual receipts keep their full form; customer receipts only allow
  // adjusting the amounts (name/contact/vehicle are read-only).
  const openEdit = (receipt) => {
    const svc = receipt.service || '';
    // Split stored services back into the individual selections. Custom
    // (Other) descriptions are kept separate so they re-fill the text box.
    const parts = svc.split(SERVICE_SEPARATOR).map((s) => s.trim()).filter(Boolean);
    const knownSelected = parts.filter((s) => SERVICE_OPTIONS.includes(s));
    const otherValue = parts.find((s) => !SERVICE_OPTIONS.includes(s)) || '';
    setEditingId(receipt.id);
    setEditingType(receipt.type === 'manual' ? 'manual' : 'customer');
    setForm({
      name: receipt.name || '',
      contact_number: receipt.contact_number || '',
      vehicle_number: receipt.vehicle_number || '',
      services: knownSelected,
      other_service: otherValue,
      date: receipt.date || new Date().toISOString().slice(0, 10),
      amount_total: String(receipt.amount_total ?? ''),
      amount_paid: String(receipt.amount_paid ?? ''),
      method: receipt.method || '',
    });
    setShowModal(true);
  };

  // Customer receipts: adjust Total / Paid directly. Paid is reconciled
  // against the customer's payment records on the backend.
  const handleSaveCustomerAmount = async () => {
    const total = parseFloat(form.amount_total);
    const paid = parseFloat(form.amount_paid);
    if (isNaN(total) || total < 0) { toast.error('Total amount must be a valid number.'); return; }
    if (isNaN(paid) || paid < 0) { toast.error('Paid amount must be a valid number.'); return; }

    setManualPdfLoading(true);
    try {
      await api.put(`/receipts/${editingId}/amount`, { amount_total: total, amount_paid: paid });
      toast.success('Receipt amount updated successfully.');
      setShowModal(false);
      load(false);
    } catch (err) {
      toast.error(err.response?.data?.message || 'Failed to update receipt amount.');
    } finally {
      setManualPdfLoading(false);
    }
  };

  // Register the "Generate Manual Receipt" action into the shared top bar
  useEffect(() => {
    setHeaderActions(
      <button className="btn btn-primary" onClick={openModal} id="btn-manual-receipt" style={{ flexShrink: 0 }}>
        <svg width="15" height="15" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14 2 14 8 20 8" />
          <line x1="12" y1="18" x2="12" y2="12" />
          <line x1="9" y1="15" x2="15" y2="15" />
        </svg>
        Generate Manual Receipt
      </button>
    );
    return () => setHeaderActions(null);
  }, [setHeaderActions, openModal]);

  const handleSaveManual = async (generatePdf = false) => {
    if (!form.name.trim()) { toast.error('Customer name is required.'); return; }
    if (!form.services.length) { toast.error('Please select at least one service.'); return; }
    if (form.services.includes('Other') && !form.other_service.trim()) { toast.error('Please describe the service.'); return; }
    if (!form.method) { toast.error('Please select a payment method.'); return; }

    setManualPdfLoading(true);
    // Substitute the custom description for the 'Other' option, then join
    // all selected services into the stored string.
    const selectedServices = form.services.includes('Other')
      ? [...form.services.filter((s) => s !== 'Other'), form.other_service.trim()]
      : form.services;
    const payload = {
      name: form.name.trim(),
      contact_number: form.contact_number.trim(),
      vehicle_number: form.vehicle_number.trim(),
      service: selectedServices.join(SERVICE_SEPARATOR),
      date: form.date,
      amount_total: parseFloat(form.amount_total) || 0,
      amount_paid: parseFloat(form.amount_paid) || 0,
      amount_pending: parseFloat(amountPending),
      method: form.method,
    };

    if (generatePdf) {
      const pdfWindow = window.open('', '_blank');
      try {
        if (editingId) {
          await api.put(`/receipts/manual/${editingId}`, payload);
          const res = await api.get(`/receipts/manual/${editingId}/pdf`, { responseType: 'blob' });
          const url = URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }));
          if (pdfWindow) { pdfWindow.location.href = url; } else { window.open(url, '_blank'); }
        } else {
          const res = await api.post('/receipts/manual-pdf', payload, { responseType: 'blob' });
          const url = URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }));
          if (pdfWindow) { pdfWindow.location.href = url; } else { window.open(url, '_blank'); }
        }
        toast.success(editingId ? 'Manual receipt updated & PDF opened!' : 'Manual receipt saved & PDF opened!');
        setShowModal(false);
        load(false);
      } catch {
        if (pdfWindow) pdfWindow.close();
        toast.error('Failed to generate manual receipt PDF.');
      } finally {
        setManualPdfLoading(false);
      }
    } else {
      try {
        if (editingId) {
          await api.put(`/receipts/manual/${editingId}`, payload);
        } else {
          await api.post('/receipts/manual', payload);
        }
        toast.success(editingId ? 'Manual receipt updated successfully.' : 'Manual receipt created successfully.');
        setShowModal(false);
        load(false);
      } catch {
        toast.error(editingId ? 'Failed to update manual receipt.' : 'Failed to save manual receipt.');
      } finally {
        setManualPdfLoading(false);
      }
    }
  };

  // ── Filter & search rows ────────────────────────────────────────────────
  const filtered = (data?.customers || []).filter((c) => {
    if (activeFilter !== 'all' && c.type !== activeFilter) return false;
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      c.name.toLowerCase().includes(q) ||
      (c.contact_number || '').includes(q) ||
      (c.vehicle_number || '').toLowerCase().includes(q) ||
      (c.service || '').toLowerCase().includes(q)
    );
  });

  useEffect(() => {
    setCurrentPage(1);
  }, [search, activeFilter]);

  if (loading) return (
    <div className="app-content">
      <div style={{ display: 'flex', justifyContent: 'center', padding: 80 }}>
        <div className="spinner" style={{ width: 36, height: 36, border: '3px solid #e2e8f0', borderTopColor: '#1e3a5f' }} />
      </div>
    </div>
  );

  return (
    <div className="app-content">
      {/* Summary cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 14, marginBottom: 18 }}>
        {[
          { label: 'Grand Total', value: data?.summary?.grandTotal || 0, color: '#1e3a5f' },
          { label: 'Total Collected', value: data?.summary?.grandPaid || 0, color: '#065f46' },
          { label: 'Total Pending', value: data?.summary?.grandPending || 0, color: '#92400e' },
        ].map((item) => (
          <div key={item.label} className="stat-card" style={{ borderLeft: `4px solid ${item.color}` }}>
            <div>
              <div className="stat-label">{item.label}</div>
              <div className="stat-value" style={{ color: item.color }}>
                &#8377;{parseFloat(item.value).toLocaleString('en-IN')}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Table card */}
      <div className="card">
        <div className="card-header" style={{ flexWrap: 'wrap', gap: 12, paddingBottom: 12 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <h2 className="card-title" style={{ margin: 0 }}>Receipt Register</h2>
            {refreshing && <span className="spinner" style={{ width: 14, height: 14, borderTopColor: '#1e3a5f', borderColor: '#e2e8f0' }} />}
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap', marginLeft: 'auto' }}>
            {/* Filter tabs */}
            <div style={{ display: 'flex', alignItems: 'center', background: '#f1f5f9', borderRadius: 8, padding: 3, gap: 2 }}>
              {FILTERS.map((f) => (
                <button
                  key={f.key}
                  id={`filter-${f.key}`}
                  onClick={() => setActiveFilter(f.key)}
                  style={{
                    padding: '6px 14px',
                    borderRadius: 6,
                    border: 'none',
                    cursor: 'pointer',
                    fontSize: 13,
                    fontWeight: activeFilter === f.key ? 700 : 500,
                    background: activeFilter === f.key ? '#1e3a5f' : 'transparent',
                    color: activeFilter === f.key ? '#fff' : '#64748b',
                    transition: 'all 0.15s',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {f.label}
                </button>
              ))}
            </div>

            {/* Search */}
            <input
              className="form-control"
              style={{ width: 240, height: 34, padding: '0 13px', flex: '0 0 auto' }}
              placeholder="Search customer, vehicle..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
        </div>

        <div className="card-body" style={{ padding: 0 }}>
          <div className="table-wrapper" style={{ borderRadius: 0, border: 'none', borderTop: '1px solid #e2e8f0' }}>
            <table>
              <thead>
                <tr>
                  <th style={{ width: 45 }}>#</th>
                  <th>Customer Name</th>
                  <th>Contact</th>
                  <th>Category / Service</th>
                  <th>Vehicle No.</th>
                  <th style={{ textAlign: 'right' }}>Total</th>
                  <th style={{ textAlign: 'right' }}>Paid</th>
                  <th style={{ textAlign: 'right' }}>Pending</th>
                  <th style={{ textAlign: 'center', width: 90 }}>PDF</th>
                  <th style={{ textAlign: 'center', width: 50 }}></th>
                  <th style={{ textAlign: 'center', width: 70 }}>Edit</th>
                </tr>
              </thead>
              <tbody>
                {filtered.length === 0 ? (
                  <tr>
                    <td colSpan={11} style={{ textAlign: 'center', padding: 40, color: '#94a3b8' }}>
                      No receipts found.
                    </td>
                  </tr>
                ) : filtered.slice((currentPage - 1) * ITEMS_PER_PAGE, currentPage * ITEMS_PER_PAGE).map((c, i) => (
                  <tr key={c.id}>
                    <td style={{ color: '#94a3b8', fontSize: 12 }}>{(currentPage - 1) * ITEMS_PER_PAGE + i + 1}</td>
                    <td style={{ fontWeight: 600, color: '#0f172a' }}>{c.name}</td>
                    <td style={{ color: '#475569' }}>{c.contact_number || '—'}</td>
                    <td>
                      {c.type === 'customer' ? (
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                          {(c.categories && c.categories.length ? c.categories : [c.category])
                            .filter(Boolean)
                            .map((cat) => (
                              <span key={cat} className="badge badge-info">{CATEGORY_LABELS[cat] || cat}</span>
                            ))}
                        </div>
                      ) : (
                        /* Highlighted badges for Manual Receipts — one per service */
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                          {(c.service || 'Manual Receipt').split(SERVICE_SEPARATOR).map((s) => (
                            <span key={s} style={{
                              display: 'inline-flex',
                              alignItems: 'center',
                              padding: '4px 10px',
                              borderRadius: 6,
                              fontSize: 12,
                              fontWeight: 600,
                              background: '#fffbeb',
                              color: '#b45309',
                              border: '1px solid #fde68a',
                              boxShadow: '0 1px 2px rgba(0,0,0,0.03)',
                            }}>
                              {s}
                            </span>
                          ))}
                        </div>
                      )}
                    </td>
                    <td style={{ fontSize: 13, color: '#475569', fontFamily: 'monospace', fontWeight: 700 }}>{c.vehicle_number || '—'}</td>
                    <td style={{ textAlign: 'right', fontWeight: 500 }}>&#8377;{parseFloat(c.amount_total).toLocaleString('en-IN')}</td>
                    <td style={{ textAlign: 'right', color: '#059669', fontWeight: 600 }}>&#8377;{parseFloat(c.amount_paid).toLocaleString('en-IN')}</td>
                    <td style={{ textAlign: 'right', color: parseFloat(c.amount_pending) > 0 ? '#d97706' : '#059669', fontWeight: 600 }}>
                      &#8377;{parseFloat(c.amount_pending).toLocaleString('en-IN')}
                    </td>
                    <td style={{ textAlign: 'center' }}>
                      <button
                        className="btn btn-ghost btn-sm"
                        onClick={() => c.type === 'manual' ? handleViewManualPDF(c.id) : handleViewPDF(c.id)}
                        disabled={pdfLoadingId === c.id}
                      >
                        {pdfLoadingId === c.id ? (
                          <span className="spinner" style={{ borderColor: 'rgba(0,0,0,0.2)', borderTopColor: '#1e3a5f', width: 12, height: 12 }} />
                        ) : (
                          <>
                            <svg width="13" height="13" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                              <polyline points="7 10 12 15 17 10" /><line x1="12" y1="15" x2="12" y2="3" />
                            </svg>
                            PDF
                          </>
                        )}
                      </button>
                    </td>
                    <td style={{ textAlign: 'center' }}>
                      <button
                        className="btn btn-ghost btn-sm"
                        onClick={() => c.type === 'manual' ? handleSendManualWhatsApp(c.id) : handleSendWhatsApp(c.id)}
                        disabled={whatsappLoadingId === c.id || !c.contact_number}
                        title={!c.contact_number ? 'No phone number on file' : 'Send receipt via WhatsApp'}
                        style={{ color: '#25D366' }}
                      >
                        {whatsappLoadingId === c.id ? (
                          <span className="spinner" style={{ borderColor: 'rgba(37,211,102,0.2)', borderTopColor: '#25D366', width: 12, height: 12 }} />
                        ) : (
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
                            <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/>
                          </svg>
                        )}
                      </button>
                    </td>
                    <td style={{ textAlign: 'center' }}>
                      <button
                        className="btn btn-ghost btn-sm"
                        onClick={() => openEdit(c)}
                        title={c.type === 'manual' ? `Edit receipt ${c.receipt_number || ''}` : 'Adjust receipt amount'}
                      >
                        <svg width="13" height="13" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                          <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                          <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
                        </svg>
                        Edit
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
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

      {/* Manual Receipt Modal */}
      {showModal && (
        <div className="modal-overlay" onClick={(e) => { if (e.target === e.currentTarget) closeModal(); }} style={{ zIndex: 1000 }}>
          <div className="modal" style={{ maxWidth: 560, width: '100%', maxHeight: '90vh', overflowY: 'auto' }} onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3 className="modal-title">
                {editingType === 'customer' ? 'Adjust Receipt Amount' : (editingId ? 'Edit Manual Receipt' : 'Generate Manual Receipt')}
              </h3>
              <button className="btn btn-ghost btn-sm" onClick={closeModal} disabled={manualPdfLoading} id="btn-close-manual-modal" aria-label="Close">
                <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                  <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            </div>

            <div className="modal-body">
              <form onSubmit={(e) => {
                e.preventDefault();
                if (editingType === 'customer') { handleSaveCustomerAmount(); } else { handleSaveManual(false); }
              }}>

                <div style={{ marginBottom: 18 }}>
                  <p style={{ fontWeight: 600, color: '#1e3a5f', fontSize: 13, marginBottom: 12, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Customer Details</p>
                  {editingType === 'customer' ? (
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                      <div>
                        <label className="form-label">Customer Name</label>
                        <div className="form-control" style={{ background: '#f8fafc', color: '#475569', cursor: 'default' }}>{form.name || '—'}</div>
                      </div>
                      <div>
                        <label className="form-label">Phone Number</label>
                        <div className="form-control" style={{ background: '#f8fafc', color: '#475569', cursor: 'default' }}>{form.contact_number || '—'}</div>
                      </div>
                      <div style={{ gridColumn: '1 / -1' }}>
                        <label className="form-label">Vehicle Number</label>
                        <div className="form-control" style={{ background: '#f8fafc', color: '#475569', cursor: 'default' }}>{form.vehicle_number || '—'}</div>
                      </div>
                    </div>
                  ) : (
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                      <div>
                        <label className="form-label" htmlFor="mr-name">Customer Name <span style={{ color: '#e11d48' }}>*</span></label>
                        <input id="mr-name" className="form-control" name="name" value={form.name} onChange={handleFormChange} placeholder="Full name" required />
                      </div>
                      <div>
                        <label className="form-label" htmlFor="mr-phone">Phone Number</label>
                        <input id="mr-phone" className="form-control" name="contact_number" value={form.contact_number} onChange={handleFormChange} placeholder="e.g. 9876543210" />
                      </div>
                      <div style={{ gridColumn: '1 / -1' }}>
                        <label className="form-label" htmlFor="mr-vehicle">Vehicle Number</label>
                        <input id="mr-vehicle" className="form-control" name="vehicle_number" value={form.vehicle_number} onChange={handleFormChange} placeholder="e.g. GJ05AB1234" />
                      </div>
                    </div>
                  )}
                </div>

                {editingType !== 'customer' && (
                  <div style={{ marginBottom: 18 }}>
                    <p style={{ fontWeight: 600, color: '#1e3a5f', fontSize: 13, marginBottom: 12, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Service</p>
                    <div>
                      <label className="form-label">Select Services <span style={{ color: '#e11d48' }}>*</span></label>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                        {SERVICE_OPTIONS.map((s) => {
                          const checked = form.services.includes(s);
                          return (
                            <button
                              key={s}
                              type="button"
                              onClick={() => toggleService(s)}
                              aria-pressed={checked}
                              style={{
                                padding: '8px 13px',
                                borderRadius: 8,
                                border: checked ? '1.5px solid #1e3a5f' : '1px solid #cbd5e1',
                                background: checked ? '#1e3a5f' : '#fff',
                                color: checked ? '#fff' : '#334155',
                                fontWeight: 600,
                                fontSize: 13,
                                cursor: 'pointer',
                                transition: 'all 0.15s',
                              }}
                            >
                              {checked ? '\u2713 ' : ''}{s}
                            </button>
                          );
                        })}
                      </div>
                    </div>
                    {form.services.includes('Other') && (
                      <div style={{ marginTop: 12 }}>
                        <label className="form-label" htmlFor="mr-other-service">Describe Service <span style={{ color: '#e11d48' }}>*</span></label>
                        <input id="mr-other-service" className="form-control" name="other_service" value={form.other_service} onChange={handleFormChange} placeholder="Enter custom service name..." required />
                      </div>
                    )}
                  </div>
                )}

                <div style={{ marginBottom: 20 }}>
                  <p style={{ fontWeight: 600, color: '#1e3a5f', fontSize: 13, marginBottom: 12, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Payment Details</p>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                    {editingType !== 'customer' && (
                      <>
                        <div>
                          <label className="form-label" htmlFor="mr-date">Date</label>
                          <input id="mr-date" className="form-control" type="date" name="date" value={form.date} onChange={handleFormChange} />
                        </div>
                        <div>
                          <label className="form-label" htmlFor="mr-method">Payment Method <span style={{ color: '#e11d48' }}>*</span></label>
                          <select id="mr-method" className="form-control" name="method" value={form.method} onChange={handleFormChange} required>
                            <option value="">-- Select method --</option>
                            {METHOD_OPTIONS.map((m) => (<option key={m} value={m}>{m}</option>))}
                          </select>
                        </div>
                      </>
                    )}
                    <div>
                      <label className="form-label" htmlFor="mr-total">Total Amount (&#8377;)</label>
                      <input id="mr-total" className="form-control" type="number" min="0" step="0.01" name="amount_total" value={form.amount_total} onChange={handleFormChange} placeholder="0.00" />
                    </div>
                    <div>
                      <label className="form-label" htmlFor="mr-paid">Amount Paid (&#8377;)</label>
                      <input id="mr-paid" className="form-control" type="number" min="0" step="0.01" name="amount_paid" value={form.amount_paid} onChange={handleFormChange} placeholder="0.00" />
                    </div>
                    <div style={{ gridColumn: '1 / -1' }}>
                      <label className="form-label">Amount Pending (&#8377;) — auto-calculated</label>
                      <div className="form-control" style={{
                        background: parseFloat(amountPending) > 0 ? '#fef3c7' : '#d1fae5',
                        color: parseFloat(amountPending) > 0 ? '#92400e' : '#065f46',
                        fontWeight: 700, cursor: 'default', userSelect: 'none',
                      }}>
                        &#8377;{parseFloat(amountPending).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                      </div>
                    </div>
                  </div>
                </div>

                {/* ── Action Buttons ── */}
                <div className="modal-footer" style={{ paddingTop: 16, borderTop: '1px solid #e2e8f0', marginTop: 8 }}>
                  <button type="button" className="btn btn-ghost" onClick={closeModal} disabled={manualPdfLoading}>
                    Cancel
                  </button>
                  {editingType === 'customer' ? (
                    <button
                      type="button"
                      className="btn btn-primary"
                      onClick={handleSaveCustomerAmount}
                      disabled={manualPdfLoading}
                      id="btn-update-customer-amount"
                    >
                      {manualPdfLoading ? 'Saving...' : 'Update Amount'}
                    </button>
                  ) : (
                    <>
                      <button
                        type="button"
                        className="btn btn-secondary"
                        onClick={() => handleSaveManual(false)}
                        disabled={manualPdfLoading}
                        id="btn-save-manual-receipt"
                        style={{ background: '#e2e8f0', color: '#1e293b', border: 'none', fontWeight: 600 }}
                      >
                        {manualPdfLoading ? 'Saving...' : (editingId ? 'Update Receipt' : 'Save Receipt')}
                      </button>
                      <button
                        type="button"
                        className="btn btn-primary"
                        onClick={() => handleSaveManual(true)}
                        disabled={manualPdfLoading}
                        id="btn-submit-manual-receipt"
                      >
                        {manualPdfLoading ? (
                          <><span className="spinner" style={{ borderColor: 'rgba(255,255,255,0.3)', borderTopColor: '#fff', width: 14, height: 14 }} />Generating...</>
                        ) : (
                          <>
                            <svg width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                              <polyline points="14 2 14 8 20 8" />
                              <line x1="12" y1="18" x2="12" y2="12" />
                              <line x1="9" y1="15" x2="15" y2="15" />
                            </svg>
                            Save &amp; Generate PDF
                          </>
                        )}
                      </button>
                    </>
                  )}
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
