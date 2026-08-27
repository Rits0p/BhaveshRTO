import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import toast from 'react-hot-toast';
import Pagination from '../components/Pagination';

// Quick presets for the days-wise expiry filter
const DAY_PRESETS = [7, 15, 30, 45, 60, 90];

// Category config — title, columns, badge style
const CATEGORY_CONFIG = {
  insurance: {
    title: 'Insurance',
    subtitle: 'Vehicle insurance records and renewal reminders',
    color: '#1e40af',
    bg: '#dbeafe',
    columns: [
      { key: 'name', label: 'Customer Name' },
      { key: 'contact_number', label: 'Contact' },
      { key: 'vehicle_number', label: 'Vehicle No.' },
      { key: 'start_date', label: 'Start Date', isDate: true },
      { key: 'end_date', label: 'Expiry Date', isDate: true },
      { key: 'amount_total', label: 'Total', isMoney: true },
      { key: 'amount_paid', label: 'Paid', isMoney: true },
    ],
  },
  permit: {
    title: 'Permit',
    subtitle: 'Vehicle permit records',
    color: '#065f46',
    bg: '#d1fae5',
    columns: [
      { key: 'name', label: 'Customer Name' },
      { key: 'contact_number', label: 'Contact' },
      { key: 'vehicle_number', label: 'Vehicle No.' },
      { key: 'start_date', label: 'Start Date', isDate: true },
      { key: 'end_date', label: 'Expiry Date', isDate: true },
      { key: 'amount_total', label: 'Total', isMoney: true },
      { key: 'amount_paid', label: 'Paid', isMoney: true },
    ],
  },
  fitness: {
    title: 'Fitness',
    subtitle: 'Vehicle fitness certificate records',
    color: '#92400e',
    bg: '#fef3c7',
    columns: [
      { key: 'name', label: 'Customer Name' },
      { key: 'contact_number', label: 'Contact' },
      { key: 'start_date', label: 'Fitness Start Date', isDate: true },
      { key: 'end_date', label: 'Fitness End Date', isDate: true },
    ],
  },
  puc: {
    title: 'PUC',
    subtitle: 'Pollution Under Control certificate records',
    color: '#0e7490',
    bg: '#cffafe',
    columns: [
      { key: 'name', label: 'Customer Name' },
      { key: 'contact_number', label: 'Contact' },
      { key: 'start_date', label: 'PUC Start Date', isDate: true },
      { key: 'end_date', label: 'PUC End Date', isDate: true },
    ],
  },
  tax: {
    title: 'Tax',
    subtitle: 'Road tax records',
    color: '#7c3aed',
    bg: '#ede9fe',
    columns: [
      { key: 'name', label: 'Customer Name' },
      { key: 'contact_number', label: 'Contact' },
      { key: 'vehicle_number', label: 'Vehicle No.' },
      { key: 'start_date', label: 'Tax Start Date', isDate: true },
      { key: 'end_date', label: 'Tax Expiry Date', isDate: true },
    ],
  },
  license: {
    title: 'License',
    subtitle: 'Driving license records and renewal reminders',
    color: '#6d28d9',
    bg: '#ede9fe',
    columns: [
      { key: 'name', label: 'Customer Name' },
      { key: 'contact_number', label: 'Contact' },
      { key: 'start_date', label: 'Issue Date', isDate: true },
      { key: 'end_date', label: 'Expiry Date', isDate: true },
    ],
  },
};

function getDaysUntilExpiry(dateStr) {
  if (!dateStr) return null;
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const parts = typeof dateStr === 'string'
    ? dateStr.split('T')[0].split('-').map(Number)
    : [dateStr.getFullYear(), dateStr.getMonth() + 1, dateStr.getDate()];

  const expiry = new Date(parts[0], parts[1] - 1, parts[2]);
  expiry.setHours(0, 0, 0, 0);

  const diffMs = expiry.getTime() - today.getTime();
  return Math.round(diffMs / (1000 * 60 * 60 * 24));
}

function isExpiringSoon(dateStr, days = 30) {
  const diffDays = getDaysUntilExpiry(dateStr);
  return diffDays !== null && diffDays >= 0 && diffDays <= days;
}

export default function CategoryPage({ category }) {
  const config = CATEGORY_CONFIG[category];
  const [customers, setCustomers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [sendingId, setSendingId] = useState(null);
  const [filter, setFilter] = useState('all');
  const [daysFilter, setDaysFilter] = useState(null);
  const [customDays, setCustomDays] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const ITEMS_PER_PAGE = 10;
  const navigate = useNavigate();

  const load = useCallback(async (useLoader = false) => {
    if (useLoader) {
      setLoading(true);
    } else {
      setRefreshing(true);
    }

    try {
      const res = await api.get('/customers', {
        params: { category, page_size: 10000, _refresh: Date.now() },
      });
      setCustomers(res.data.data);
    } catch {
      toast.error('Failed to load records');
    } finally {
      if (useLoader) {
        setLoading(false);
      } else {
        setRefreshing(false);
      }
    }
  }, [category]);

  useEffect(() => {
    load(true);
    const refreshWhenVisible = () => {
      if (document.visibilityState === 'visible') load();
    };
    document.addEventListener('visibilitychange', refreshWhenVisible);
    const refreshTimer = window.setInterval(load, 5000);
    return () => {
      document.removeEventListener('visibilitychange', refreshWhenVisible);
      window.clearInterval(refreshTimer);
    };
  }, [load]);

  useEffect(() => {
    setCurrentPage(1);
  }, [filter, daysFilter, customDays]);

  const handleSend = async (customer) => {
    setSendingId(customer.id);
    try {
      // Log the reminder attempt in the backend's MessageLog (audit trail)
      const res = await api.post(`/customers/${customer.id}/send-reminder`);

      // Normalize the phone number to international format.
      // If the stored number is 10 digits (Indian mobile), prepend country code 91.
      let phone = (customer.contact_number || '').replace(/[\s\-().+]/g, '');
      if (/^\d{10}$/.test(phone)) {
        phone = `91${phone}`;
      }

      // Build the message text from the backend's logged message_body (same
      // text the backend used), falling back to a generic message if the
      // response shape is unexpected.
      const messageBody =
        res.data?.data?.message_body ||
        `Hello ${customer.name}, please renew your ${category} before it expires. Contact us for assistance.`;

      // Open WhatsApp Web / WhatsApp App with the message pre-filled.
      // The user just needs to tap "Send" inside WhatsApp.
      const waUrl = `https://wa.me/${phone}?text=${encodeURIComponent(messageBody)}`;
      window.open(waUrl, '_blank', 'noopener,noreferrer');

      toast.success(`WhatsApp opened for ${customer.name} — tap Send in WhatsApp!`);
    } catch (err) {
      toast.error(err.response?.data?.message || 'Failed to open WhatsApp');
    } finally {
      setSendingId(null);
    }
  };

  const handleDelete = async (customer) => {
    if (!window.confirm(`Delete customer "${customer.name}"? This cannot be undone.`)) return;
    try {
      await api.delete(`/customers/${customer.id}`);
      toast.success('Customer deleted');
      load();
    } catch (error) {
      toast.error(error.response?.data?.message || 'Delete failed');
    }
  };

  const expiredList = customers.filter((c) => {
    const days = getDaysUntilExpiry(c.end_date);
    return days !== null && days < 0;
  });
  const expiredCount = expiredList.length;

  // Customers expiring within 1 month (not yet expired)
  const expiringList = customers.filter((c) => isExpiringSoon(c.end_date));
  const expiringCount = expiringList.length;

  // Active: no expiry date, or expiry more than 1 month away
  const activeList = customers.filter((c) => {
    const days = getDaysUntilExpiry(c.end_date);
    return days === null || days > 30;
  });
  const activeCount = activeList.length;

  const filteredCustomers =
    daysFilter !== null
      ? customers.filter((c) => {
        const days = getDaysUntilExpiry(c.end_date);
        return days !== null && days >= 0 && days <= daysFilter;
      })
      : filter === 'expired' ? expiredList
        : filter === 'expiring' ? expiringList
          : filter === 'active' ? activeList
            : customers;

  const FILTER_LABELS = { all: config.title, active: 'Active', expiring: 'Expiring', expired: 'Expired' };
  const activeFilterLabel = daysFilter !== null
    ? `Expiring in ${daysFilter} day${daysFilter === 1 ? '' : 's'}`
    : FILTER_LABELS[filter];

  const selectDays = (value) => {
    if (value === null || value === '') {
      setDaysFilter(null);
      setCustomDays('');
    } else {
      setDaysFilter(Number(value));
      setCustomDays(String(value));
      setFilter('all');
    }
  };

  const cards = [
    {
      key: 'all',
      label: `Total ${config.title} Customers`,
      value: customers.length,
      color: config.color,
      bg: config.bg,
      icon: (
        <svg width="22" height="22" fill="none" stroke={config.color} strokeWidth="2" viewBox="0 0 24 24">
          <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
          <circle cx="9" cy="7" r="4" />
          <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
          <path d="M16 3.13a4 4 0 0 1 0 7.75" />
        </svg>
      ),
    },
    {
      key: 'active',
      label: 'Active',
      value: activeCount,
      color: '#16a34a',
      bg: '#dcfce7',
      icon: (
        <svg width="22" height="22" fill="none" stroke="#16a34a" strokeWidth="2" viewBox="0 0 24 24">
          <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
          <polyline points="22 4 12 14.01 9 11.01" />
        </svg>
      ),
    },
    {
      key: 'expiring',
      label: 'Expiring in 1 Month',
      value: expiringCount,
      color: '#d97706',
      bg: '#fef3c7',
      icon: (
        <svg width="22" height="22" fill="none" stroke="#d97706" strokeWidth="2" viewBox="0 0 24 24">
          <circle cx="12" cy="12" r="10" />
          <polyline points="12 6 12 12 16 14" />
        </svg>
      ),
    },
    {
      key: 'expired',
      label: 'Expired',
      value: expiredCount,
      color: '#dc2626',
      bg: '#fee2e2',
      icon: (
        <svg width="22" height="22" fill="none" stroke="#dc2626" strokeWidth="2" viewBox="0 0 24 24">
          <circle cx="12" cy="12" r="10" />
          <line x1="15" y1="9" x2="9" y2="15" />
          <line x1="9" y1="9" x2="15" y2="15" />
        </svg>
      ),
    },
  ];

  return (
    <div className="app-content">
      {/* Days-wise expiry filter */}
      <div className="card" style={{ marginBottom: 16 }}>
        <div className="card-body" style={{ padding: '12px 20px', display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center' }}>
          <span style={{ fontSize: 13, color: '#64748b', fontWeight: 600 }}>Expiry within:</span>
          <select
            className="form-control"
            style={{ maxWidth: 170 }}
            value={daysFilter === null ? '' : String(daysFilter)}
            onChange={(e) => selectDays(e.target.value)}
          >
            <option value="">All days</option>
            {DAY_PRESETS.map((d) => (
              <option key={d} value={d}>Next {d} days</option>
            ))}
            {daysFilter !== null && !DAY_PRESETS.includes(daysFilter) && (
              <option value={daysFilter}>{daysFilter} days (custom)</option>
            )}
          </select>
          <input
            type="number"
            min="0"
            className="form-control"
            style={{ maxWidth: 150 }}
            placeholder="Custom days…"
            value={customDays}
            onChange={(e) => {
              const v = e.target.value;
              setCustomDays(v);
              if (v !== '' && Number(v) >= 0) {
                selectDays(v);
              } else {
                setDaysFilter(null);
              }
            }}
          />
          {daysFilter !== null && (
            <button className="btn btn-ghost btn-sm" onClick={() => selectDays('')}>Clear</button>
          )}
          <span style={{ fontSize: 13, color: '#94a3b8' }}>
            {daysFilter !== null ? `${filteredCustomers.length} expiring in ${daysFilter} day${daysFilter === 1 ? '' : 's'}` : `${customers.length} record${customers.length !== 1 ? 's' : ''}`}
          </span>
        </div>
      </div>

      {/* Summary stat cards — click to filter the table */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))',
        gap: 12,
        marginBottom: 16,
      }}>
        {cards.map((card) => (
          <button
            key={card.key}
            type="button"
            className={`stat-card clickable ${filter === card.key ? 'active' : ''}`}
            style={{ borderLeft: `4px solid ${card.color}` }}
            onClick={() => { setFilter(card.key); setDaysFilter(null); setCustomDays(''); }}
            title={`Show ${card.label}`}
          >
            <div className="stat-icon" style={{ background: card.bg }}>
              {card.icon}
            </div>
            <div>
              <div className="stat-label">{card.label}</div>
              <div className="stat-value" style={{ color: card.color }}>
                {loading ? '—' : card.value}
              </div>
            </div>
          </button>
        ))}
      </div>

      <div className="card">
        {loading ? (
          <div style={{ padding: 60, textAlign: 'center' }}>
            <div className="spinner" style={{ width: 32, height: 32, border: '3px solid #e2e8f0', borderTopColor: '#1e3a5f', margin: '0 auto' }} />
          </div>
        ) : customers.length === 0 ? (
          <div className="empty-state">
            <h3>No {config.title} records</h3>
            <p>Add customers from the "All Customers" section and assign the {config.title} category.</p>
          </div>
        ) : filteredCustomers.length === 0 ? (
          <div className="empty-state">
            <h3>No {activeFilterLabel} customers</h3>
            <p>Nothing matches the "{activeFilterLabel}" filter.</p>
            <button className="btn btn-primary" onClick={() => { setFilter('all'); setDaysFilter(null); setCustomDays(''); }}>Show all customers</button>
          </div>
        ) : (
          <div className="table-wrapper" style={{ opacity: refreshing ? 0.9 : 1, transition: 'opacity 0.2s ease' }}>
            <table>
              <thead>
                <tr>
                  <th>#</th>
                  {config.columns.map((col) => (
                    <th key={col.key}>{col.label}</th>
                  ))}
                  <th>Status</th>
                  <th>Send Reminder</th>
                  <th>Edit</th>
                  <th>Delete</th>
                </tr>
              </thead>
              <tbody>
                {filteredCustomers.slice((currentPage - 1) * ITEMS_PER_PAGE, currentPage * ITEMS_PER_PAGE).map((c, idx) => {
                  const daysUntilExpiry = getDaysUntilExpiry(c.end_date);
                  const expiring = isExpiringSoon(c.end_date);
                  const expired = daysUntilExpiry !== null && daysUntilExpiry < 0;
                  return (
                    <tr key={c.id} className={expiring ? 'expiring' : ''}>
                      <td style={{ color: '#94a3b8', fontSize: 12 }}>{(currentPage - 1) * ITEMS_PER_PAGE + idx + 1}</td>
                      {config.columns.map((col) => (
                        <td key={col.key}>
                          {col.isDate
                            ? c[col.key]
                              ? new Date(c[col.key]).toLocaleDateString('en-IN')
                              : '—'
                            : col.isMoney
                              ? `₹${parseFloat(c[col.key] || 0).toLocaleString('en-IN')}`
                              : c[col.key] || '—'}
                        </td>
                      ))}
                      <td>
                        {expiring ? (
                          <span className="badge badge-warning">
                            ⚠️ {daysUntilExpiry === 0 ? 'Expires today' : daysUntilExpiry === 1 ? 'Expires in 1 day' : `Expires in ${daysUntilExpiry} days`}
                          </span>
                        ) : expired ? (
                          <span className="badge badge-danger">
                            Expired {Math.abs(daysUntilExpiry)} {Math.abs(daysUntilExpiry) === 1 ? 'day' : 'days'} ago
                          </span>
                        ) : (
                          <span className="badge badge-success">✓ Active</span>
                        )}
                      </td>
                      <td>
                        <button
                          className={`btn btn-sm ${expiring ? 'btn-accent' : 'btn-ghost'}`}
                          onClick={() => handleSend(c)}
                          disabled={sendingId === c.id}
                          title={`Send WhatsApp reminder to ${c.name}`}
                        >
                          {sendingId === c.id ? (
                            <span className="spinner" style={{ borderColor: 'rgba(0,0,0,0.2)', borderTopColor: 'currentColor' }} />
                          ) : (
                            <>
                              <svg width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                                <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07A19.5 19.5 0 0 1 4.69 12 19.79 19.79 0 0 1 1.61 3.49 2 2 0 0 1 3.6 1.28h3a2 2 0 0 1 2 1.72c.127.96.361 1.903.7 2.81a2 2 0 0 1-.45 2.11L7.91 9c1.06 1.88 2.6 3.45 4.5 4.56l1.88-1.88a2 2 0 0 1 2.11-.45c.907.339 1.85.573 2.81.7a2 2 0 0 1 1.72 2z" />
                              </svg>
                              Send
                            </>
                          )}
                        </button>
                      </td>
                      <td>
                        <button className="btn btn-ghost btn-sm" onClick={() => navigate(`/customers/${c.id}/edit`)}>Edit</button>
                      </td>
                      <td>
                        <button className="btn btn-danger-ghost btn-sm" onClick={() => handleDelete(c)} title="Delete">
                          <svg width="13" height="13" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                            <polyline points="3 6 5 6 21 6" />
                            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                            <line x1="10" y1="11" x2="10" y2="17" />
                            <line x1="14" y1="11" x2="14" y2="17" />
                          </svg>
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
        {!loading && filteredCustomers.length > 0 && (
          <Pagination
            currentPage={currentPage}
            totalItems={filteredCustomers.length}
            pageSize={ITEMS_PER_PAGE}
            onPageChange={setCurrentPage}
          />
        )}
      </div>
    </div>
  );
}
