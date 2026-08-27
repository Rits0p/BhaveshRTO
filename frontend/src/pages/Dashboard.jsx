import { useEffect, useState } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell, LabelList
} from 'recharts';
import api from '../services/api';

function StatCard({ icon, label, value, color, bgColor }) {
  return (
    <div className="stat-card">
      <div className="stat-icon" style={{ background: bgColor }}>
        {icon}
      </div>
      <div>
        <div className="stat-label">{label}</div>
        <div className="stat-value" style={{ color }}>{value}</div>
      </div>
    </div>
  );
}

const CountTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 8, padding: '10px 16px', boxShadow: '0 4px 16px rgba(0,0,0,0.1)' }}>
        <p style={{ fontSize: 12, color: '#64748b', marginBottom: 4 }}>{label}</p>
        <p style={{ fontSize: 16, fontWeight: 700, color: '#1e3a5f' }}>{payload[0].value.toLocaleString('en-IN')} customers</p>
      </div>
    );
  }
  return null;
};

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div style={{ background: '#fff', border: '1px solid #e2e8f0', borderRadius: 8, padding: '10px 16px', boxShadow: '0 4px 16px rgba(0,0,0,0.1)' }}>
        <p style={{ fontSize: 12, color: '#64748b', marginBottom: 4 }}>{label}</p>
        <p style={{ fontSize: 16, fontWeight: 700, color: '#1e3a5f' }}>₹{payload[0].value.toLocaleString('en-IN')}</p>
      </div>
    );
  }
  return null;
};

const MONTHS = [
  { value: '1', label: 'January' },
  { value: '2', label: 'February' },
  { value: '3', label: 'March' },
  { value: '4', label: 'April' },
  { value: '5', label: 'May' },
  { value: '6', label: 'June' },
  { value: '7', label: 'July' },
  { value: '8', label: 'August' },
  { value: '9', label: 'September' },
  { value: '10', label: 'October' },
  { value: '11', label: 'November' },
  { value: '12', label: 'December' },
];

// Chart palettes mix bright and soft shades, cycling per bar.
const COLLECTION_COLORS = ['#2563eb', '#93c5fd', '#0ea5e9', '#bfdbfe', '#1d4ed8', '#dbeafe'];
const CUSTOMER_COLORS = ['#059669', '#6ee7b7', '#16a34a', '#a7f3d0', '#10b981', '#d1fae5'];

// Category breakdown cards (keys match the backend categoryCounts object)
const CATEGORY_CARDS = [
  {
    key: 'insurance', label: 'Insurance', color: '#1e3a5f', bg: '#dbeafe', iconColor: '#1e40af',
    icon: <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />,
  },
  {
    key: 'permit', label: 'Permit', color: '#0f766e', bg: '#ccfbf1', iconColor: '#0f766e',
    icon: <path d="M2 5h20M2 10h20M7 14h10M7 19h10" />,
  },
  {
    key: 'fitness', label: 'Fitness', color: '#be185d', bg: '#fce7f3', iconColor: '#be185d',
    icon: <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />,
  },
  {
    key: 'puc', label: 'PUC', color: '#7c3aed', bg: '#ede9fe', iconColor: '#7c3aed',
    icon: <path d="M22 12h-4l-3 9L9 3l-3 9H2" />,
  },
  {
    key: 'tax', label: 'Tax', color: '#b45309', bg: '#fef3c7', iconColor: '#b45309',
    icon: <path d="M6 2v20M6 2l9 8-9 8" />,
  },
  {
    key: 'license', label: 'License', color: '#0369a1', bg: '#e0f2fe', iconColor: '#0369a1',
    icon: <path d="M2 7h20M2 7l2-4h16l2 4M4 7v14h16V7M7 13h.01M7 17h.01M11 13h6M11 17h6" />,
  },
  {
    key: 'manual', label: 'Manual', color: '#7f1d1d', bg: '#fee2e2', iconColor: '#b91c1c',
    icon: <path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2M9 5a2 2 0 0 0 2 2h2a2 2 0 0 0 2-2M9 5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2M9 12h6M9 16h6" />,
  },
];

export default function Dashboard() {
  const [summary, setSummary] = useState(null);
  const [monthly, setMonthly] = useState([]);
  const [monthlyCustomers, setMonthlyCustomers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeCat, setActiveCat] = useState(null);
  const [year, setYear] = useState(new Date().getFullYear().toString());
  const [month, setMonth] = useState('');

  useEffect(() => {
    const params = {};
    if (year) params.year = year;
    if (month) params.month = month;
    Promise.all([
      api.get('/dashboard/summary', { params }),
      api.get('/dashboard/monthly-collection', { params }),
      api.get('/dashboard/monthly-customers', { params }),
    ]).then(([sumRes, monthRes, custRes]) => {
      setSummary(sumRes.data.data);
      setMonthly(monthRes.data.data);
      setMonthlyCustomers(custRes.data.data);
    }).finally(() => setLoading(false));
  }, [year, month]);

  if (loading) return (
    <div className="app-content">
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 300 }}>
        <div className="spinner" style={{ width: 36, height: 36, border: '3px solid #e2e8f0', borderTopColor: '#1e3a5f' }} />
      </div>
    </div>
  );

  return (
    <div className="app-content">

      {/* Summary Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 14, marginBottom: 20 }}>
        <StatCard
          label="Total Customers"
          value={summary?.totalCustomers ?? 0}
          color="#1e3a5f"
          bgColor="#dbeafe"
          icon={
            <svg width="22" height="22" fill="none" stroke="#1e40af" strokeWidth="2" viewBox="0 0 24 24">
              <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" />
              <path d="M23 21v-2a4 4 0 0 0-3-3.87" /><path d="M16 3.13a4 4 0 0 1 0 7.75" />
            </svg>
          }
        />
        <StatCard
          label="Total Collection"
          value={`₹${parseFloat(summary?.totalCollection || 0).toLocaleString('en-IN')}`}
          color="#065f46"
          bgColor="#d1fae5"
          icon={
            <svg width="22" height="22" fill="none" stroke="#059669" strokeWidth="2" viewBox="0 0 24 24">
              <line x1="12" y1="1" x2="12" y2="23" /><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
            </svg>
          }
        />
        <StatCard
          label="Pending Collection"
          value={`₹${parseFloat(summary?.pendingCollection || 0).toLocaleString('en-IN')}`}
          color="#92400e"
          bgColor="#fef3c7"
          icon={
            <svg width="22" height="22" fill="none" stroke="#d97706" strokeWidth="2" viewBox="0 0 24 24">
              <circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
          }
        />
      </div>

      {/* Customers by Category */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-header" style={{ paddingBottom: 12, flexWrap: 'wrap', gap: 12 }}>
          <h2 className="card-title" style={{ margin: 0 }}>Customers by Category</h2>
          {/* Year / Month filter — scopes collection figures & the chart only */}
          <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap', marginLeft: 'auto' }}>
            <span style={{ fontSize: 12, color: '#64748b', fontWeight: 600, whiteSpace: 'nowrap' }}>Filter:</span>
            <select
              className="form-control"
              style={{ width: 120, height: 34, padding: '0 8px' }}
              value={year}
              onChange={(e) => { setYear(e.target.value); setMonth(''); }}
            >
              <option value="">All Years</option>
              {(summary?.years?.length ? summary.years : [new Date().getFullYear()]).map((y) => (
                <option key={y} value={y}>{y}</option>
              ))}
            </select>
            <select
              className="form-control"
              style={{ width: 120, height: 34, padding: '0 8px' }}
              value={month}
              onChange={(e) => setMonth(e.target.value)}
              disabled={!year}
            >
              <option value="">All Months</option>
              {MONTHS.map((m) => <option key={m.value} value={m.value}>{m.label}</option>)}
            </select>
            {(year || month) && (
              <button className="btn btn-ghost btn-sm" style={{ height: 34 }} onClick={() => { setYear(''); setMonth(''); }}>Clear</button>
            )}
            <span style={{ fontSize: 12, color: '#94a3b8', whiteSpace: 'nowrap' }}>
              {year
                ? (month ? `${MONTHS.find((m) => m.value === month)?.label} ${year}` : year)
                : 'All time'}
            </span>
          </div>
        </div>
        <div className="card-body">
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 14 }}>
            {CATEGORY_CARDS.map((cat) => (
              <button
                key={cat.key}
                type="button"
                className="stat-card clickable"
                style={{ borderLeft: `4px solid ${cat.color}`, background: cat.bg, cursor: 'pointer' }}
                onClick={() => setActiveCat(cat.key)}
                title={`View ${cat.label} amounts`}
              >
                <div className="stat-icon" style={{ background: '#fff' }}>
                  <svg width="18" height="18" fill="none" stroke={cat.iconColor} strokeWidth="2" viewBox="0 0 24 24">
                    {cat.icon}
                  </svg>
                </div>
                <div>
                  <div className="stat-label">{cat.label}</div>
                  <div className="stat-value" style={{ color: cat.color }}>
                    {summary?.categoryCounts?.[cat.key] ?? 0}
                  </div>
                </div>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Charts Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 20, marginTop: 20 }}>
        {/* Monthly Chart */}
        <div className="card">
          <div className="card-header" style={{ paddingBottom: 12 }}>
            <h2 className="card-title">Monthly Collection</h2>
            <span style={{ fontSize: 12, color: '#64748b' }}>
              {month
                ? `Daily — ${MONTHS.find((m) => m.value === month)?.label} ${year}`
                : year ? year : 'All years'}
            </span>
          </div>
          <div className="card-body">
            {monthly.length === 0 ? (
              <div className="empty-state" style={{ padding: '40px 0' }}>
                <p>No payment data yet. Add customers and record payments.</p>
              </div>
            ) : (
              <>
                <ResponsiveContainer width="100%" height={260}>
                  <BarChart data={monthly} margin={{ top: 16, right: 16, bottom: 4, left: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                    <XAxis dataKey="month" tick={{ fontSize: 12, fill: '#64748b' }} />
                    <YAxis tick={{ fontSize: 12, fill: '#64748b' }} tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}k`} />
                    <Tooltip content={<CustomTooltip />} />
                    <Bar dataKey="total" radius={[6, 6, 0, 0]} maxBarSize={52} fill="#2563eb">
                      <LabelList dataKey="total" position="top" style={{ fontSize: 10, fill: '#64748b' }} formatter={(v) => v > 0 ? (v >= 1000 ? (v / 1000).toFixed(1) + 'k' : v) : ''} />
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
                <div style={{ marginTop: 12, textAlign: 'center', fontSize: 14, fontWeight: 'bold', color: '#1e3a5f' }}>
                  Total Collection: ₹{monthly.reduce((sum, item) => sum + (parseFloat(item.total) || 0), 0).toLocaleString('en-IN')}
                </div>
              </>
            )}
          </div>
        </div>

        {/* Monthly Customers Chart */}
        <div className="card">
          <div className="card-header" style={{ paddingBottom: 12 }}>
            <h2 className="card-title">Monthly Customers</h2>
            <span style={{ fontSize: 12, color: '#64748b' }}>
              {month
                ? `Daily — ${MONTHS.find((m) => m.value === month)?.label} ${year}`
                : year ? year : 'All years'}
            </span>
          </div>
          <div className="card-body">
            {monthlyCustomers.length === 0 ? (
              <div className="empty-state" style={{ padding: '40px 0' }}>
                <p>No customers added yet.</p>
              </div>
            ) : (
              <>
                <ResponsiveContainer width="100%" height={260}>
                  <BarChart data={monthlyCustomers} margin={{ top: 16, right: 16, bottom: 4, left: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
                    <XAxis dataKey="month" tick={{ fontSize: 12, fill: '#64748b' }} />
                    <YAxis tick={{ fontSize: 12, fill: '#64748b' }} allowDecimals={false} />
                    <Tooltip content={<CountTooltip />} />
                    <Bar dataKey="count" radius={[6, 6, 0, 0]} maxBarSize={52} fill="#10b981">
                      <LabelList dataKey="count" position="top" style={{ fontSize: 10, fill: '#64748b' }} formatter={(v) => v > 0 ? v : ''} />
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
                <div style={{ marginTop: 12, textAlign: 'center', fontSize: 14, fontWeight: 'bold', color: '#1e3a5f' }}>
                  Total Customers: {monthlyCustomers.reduce((sum, item) => sum + (parseInt(item.count) || 0), 0).toLocaleString('en-IN')}
                </div>
              </>
            )}
          </div>
        </div>
      </div >

      {/* Category detail modal */}
      {
        (() => {
          const cat = CATEGORY_CARDS.find((c) => c.key === activeCat);
          if (!cat) return null;
          const info = summary?.categoryTotals?.[cat.key] || {};
          const total = parseFloat(info.total || 0);
          const paid = parseFloat(info.paid || 0);
          const pending = parseFloat(info.pending || 0);
          return (
            <div className="modal-overlay" onClick={(e) => { if (e.target === e.currentTarget) setActiveCat(null); }} style={{ zIndex: 1000 }}>
              <div className="modal" style={{ maxWidth: 420, width: '100%' }} onClick={(e) => e.stopPropagation()}>
                <div className="modal-header">
                  <h3 className="modal-title" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span className="stat-icon" style={{ background: cat.bg }}>
                      <svg width="16" height="16" fill="none" stroke={cat.iconColor} strokeWidth="2" viewBox="0 0 24 24">{cat.icon}</svg>
                    </span>
                    {cat.label} Summary
                  </h3>
                  <button className="btn btn-ghost btn-sm" onClick={() => setActiveCat(null)} aria-label="Close">
                    <svg width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                      <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
                    </svg>
                  </button>
                </div>
                <div className="modal-body">
                  <div style={{ marginBottom: 12 }}>
                    <div className="form-label">Total {cat.label} Customers</div>
                    <div style={{ fontSize: 24, fontWeight: 700, color: cat.color }}>{info.count ?? 0}</div>
                  </div>
                  {[
                    { label: 'Total Amount', value: total, color: '#1e3a5f', bg: '#dbeafe' },
                    { label: 'Amount Paid', value: paid, color: '#065f46', bg: '#d1fae5' },
                    { label: 'Pending Amount', value: pending, color: '#92400e', bg: '#fef3c7' },
                  ].map((row) => (
                    <div key={row.label} style={{
                      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                      padding: '12px 14px', borderRadius: 10, background: row.bg, marginBottom: 8,
                    }}>
                      <span style={{ fontSize: 13, fontWeight: 600, color: row.color }}>{row.label}</span>
                      <span style={{ fontSize: 16, fontWeight: 700, color: row.color }}>&#8377;{row.value.toLocaleString('en-IN')}</span>
                    </div>
                  ))}
                </div>
                <div className="modal-footer" style={{ paddingTop: 16, borderTop: '1px solid #e2e8f0' }}>
                  <button className="btn btn-primary" onClick={() => setActiveCat(null)}>Close</button>
                </div>
              </div>
            </div>
          );
        })()
      }
    </div >
  );
}
