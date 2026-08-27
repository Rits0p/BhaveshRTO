import { useEffect, useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { AuthProvider, useAuth } from './context/AuthContext';
import { LayoutContext } from './context/LayoutContext';
import Navbar from './components/Navbar';
import Login from './pages/Login';
import Signup from './pages/Signup';
import ForgotPassword from './pages/ForgotPassword';
import ResetPassword from './pages/ResetPassword';
import VerifyEmail from './pages/VerifyEmail';
import ChangePassword from './pages/ChangePassword';
import Dashboard from './pages/Dashboard';
import Customers from './pages/Customers';
import CategoryPage from './pages/CategoryPage';
import Receipts from './pages/Receipts';
import Remarks from './pages/Remarks';
import AddCustomer from './pages/AddCustomer';

// Protected route — redirects to /login if not authenticated
function ProtectedRoute({ children }) {
  const { isAuthenticated, initialized } = useAuth();
  const location = useLocation();

  if (!initialized) {
    return null;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }
  return children;
}

// Category page titles/subtitles shared with the top bar
const CATEGORY_HEADERS = {
  insurance: { title: 'Insurance', subtitle: 'Vehicle insurance records and renewal reminders' },
  permit: { title: 'Permit', subtitle: 'Vehicle permit records' },
  fitness: { title: 'Fitness', subtitle: 'Vehicle fitness certificate records' },
  puc: { title: 'PUC', subtitle: 'Pollution Under Control certificate records' },
  tax: { title: 'Tax', subtitle: 'Road tax records' },
  license: { title: 'License', subtitle: 'Driving license records and renewal reminders' },
};

function greeting() {
  const hour = new Date().getHours();
  if (hour < 12) return 'Good morning';
  if (hour < 17) return 'Good afternoon';
  return 'Good evening';
}

// Types out the greeting character-by-character, then reveals the waving hand
// once typing completes so the two animations run in sequence.
function TypingGreeting({ text }) {
  const [typed, setTyped] = useState('');
  const [done, setDone] = useState(false);

  useEffect(() => {
    let i = 0;
    setTyped('');
    setDone(false);
    const id = setInterval(() => {
      i += 1;
      setTyped(text.slice(0, i));
      if (i >= text.length) {
        clearInterval(id);
        setDone(true);
      }
    }, 65);
    return () => clearInterval(id);
  }, [text]);

  return (
    <span className="greeting">
      <span>
        {typed}
        <span className={`greeting-caret${done ? ' greeting-caret--done' : ''}`} aria-hidden="true">|</span>
      </span>
      <span className={`greeting-wave${done ? ' greeting-wave--show' : ''}`} aria-hidden="true">👋</span>
    </span>
  );
}

// Resolve the page title/subtitle shown in the shared top bar from the route
function getPageHeader(pathname, adminName) {
  const first = pathname.split('/').filter(Boolean)[0];
  if (first && CATEGORY_HEADERS[first]) return CATEGORY_HEADERS[first];

  if (pathname.startsWith('/dashboard')) {
    return {
      title: <TypingGreeting text={`${greeting()}, ${(adminName || 'Admin').split(' ')[0]}`} />,
      subtitle: `Here's an overview of your CRM today — ${new Date().toLocaleDateString('en-IN', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}`,
    };
  }
  if (pathname.startsWith('/customers/new')) {
    return { title: 'Add Customer', subtitle: 'Create a customer record and manage all RTO services in one place.' };
  }
  if (/^\/customers\/[^/]+\/edit$/.test(pathname)) {
    return { title: 'Edit Customer', subtitle: 'Update customer details and manage services.' };
  }
  if (pathname.startsWith('/customers')) {
    return { title: 'All Customers', subtitle: 'Manage all customer records across categories' };
  }
  if (pathname.startsWith('/receipts')) {
    return { title: 'Payment Receipts', subtitle: 'Bhavesh RTO Payment Receipt — collected vs. pending overview' };
  }
  if (pathname.startsWith('/remarks')) {
    return { title: 'Remarks', subtitle: 'Notes attached to customer records' };
  }
  if (pathname.startsWith('/auth/change-password')) {
    return { title: 'Change Password', subtitle: 'Update the password for your admin account' };
  }
  return { title: 'Dashboard', subtitle: '' };
}

// Layout with sidebar and top bar; the top bar holds the hamburger, the
// current page title, and the page's action buttons in one row.
function AppLayout({ children }) {
  const [collapsed, setCollapsed] = useState(true);
  const [headerActions, setHeaderActions] = useState(null);
  const location = useLocation();
  const { admin } = useAuth();
  const header = getPageHeader(location.pathname, admin?.name);

  return (
    <LayoutContext.Provider value={{ setHeaderActions }}>
      <div className="app-layout">
        <Navbar collapsed={collapsed} onToggle={() => setCollapsed((c) => !c)} />
        <main className="app-main">
          <header className="topbar">
            <div className="topbar-title" key={location.pathname}>
              <h1>{header.title}</h1>
              <p>{header.subtitle}</p>
            </div>
            <div className="topbar-actions">{headerActions}</div>
          </header>
          {children}
        </main>
      </div>
    </LayoutContext.Provider>
  );
}

function AppRoutes() {
  return (
    <Routes>
      {/* Public routes */}
      <Route path="/login" element={<Login />} />
      <Route path="/signup" element={<Signup />} />
      <Route path="/forgot-password" element={<ForgotPassword />} />
      <Route path="/auth/reset-password" element={<ResetPassword />} />
      <Route path="/auth/verify-email" element={<VerifyEmail />} />

      {/* Protected routes */}
      <Route path="/auth/change-password" element={
        <ProtectedRoute>
          <AppLayout><ChangePassword /></AppLayout>
        </ProtectedRoute>
      } />
      <Route path="/dashboard" element={
        <ProtectedRoute>
          <AppLayout><Dashboard /></AppLayout>
        </ProtectedRoute>
      } />
      <Route path="/customers" element={
        <ProtectedRoute>
          <AppLayout><Customers /></AppLayout>
        </ProtectedRoute>
      } />
      <Route path="/customers/new" element={
        <ProtectedRoute>
          <AppLayout><AddCustomer /></AppLayout>
        </ProtectedRoute>
      } />
      <Route path="/customers/:customerId/edit" element={
        <ProtectedRoute>
          <AppLayout><AddCustomer /></AppLayout>
        </ProtectedRoute>
      } />
      <Route path="/insurance" element={
        <ProtectedRoute>
          <AppLayout><CategoryPage category="insurance" /></AppLayout>
        </ProtectedRoute>
      } />
      <Route path="/fitness" element={
        <ProtectedRoute>
          <AppLayout><CategoryPage category="fitness" /></AppLayout>
        </ProtectedRoute>
      } />
      <Route path="/puc" element={
        <ProtectedRoute>
          <AppLayout><CategoryPage category="puc" /></AppLayout>
        </ProtectedRoute>
      } />
      <Route path="/tax" element={
        <ProtectedRoute>
          <AppLayout><CategoryPage category="tax" /></AppLayout>
        </ProtectedRoute>
      } />
      <Route path="/permit" element={
        <ProtectedRoute>
          <AppLayout><CategoryPage category="permit" /></AppLayout>
        </ProtectedRoute>
      } />
      <Route path="/license" element={
        <ProtectedRoute>
          <AppLayout><CategoryPage category="license" /></AppLayout>
        </ProtectedRoute>
      } />
      <Route path="/receipts" element={
        <ProtectedRoute>
          <AppLayout><Receipts /></AppLayout>
        </ProtectedRoute>
      } />
      <Route path="/remarks" element={
        <ProtectedRoute>
          <AppLayout><Remarks /></AppLayout>
        </ProtectedRoute>
      } />

      {/* Default redirect */}
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Toaster
          position="top-right"
          toastOptions={{
            duration: 3500,
            style: {
              background: '#1e293b',
              color: '#fff',
              fontSize: '14px',
              borderRadius: '10px',
              padding: '12px 18px',
            },
            success: { iconTheme: { primary: '#10b981', secondary: '#fff' } },
            error: { iconTheme: { primary: '#ef4444', secondary: '#fff' } },
          }}
        />
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  );
}
