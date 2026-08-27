import axios from 'axios';

// Auth is session-based: the backend issues a server-side 30-minute session
// cookie (HttpOnly) and a readable `csrftoken` cookie. No JWTs are stored or
// sent — we only forward cookies (withCredentials) and the CSRF token header.

const baseURL = (import.meta.env.VITE_API_URL || '/api').replace(/\/$/, '');

function getCookie(name) {
  const escaped = name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const match = document.cookie.match(new RegExp('(?:^|;\\s*)' + escaped + '=([^;]*)'));
  return match ? decodeURIComponent(match[1]) : null;
}

const api = axios.create({
  baseURL,
  headers: { 'Content-Type': 'application/json' },
  withCredentials: true,
});

api.interceptors.request.use((config) => {
  const method = (config.method || 'get').toLowerCase();
  // CSRF is only enforced for unsafe methods (POST/PUT/PATCH/DELETE).
  if (method !== 'get' && method !== 'head' && method !== 'options') {
    const csrfToken = getCookie('csrftoken');
    if (csrfToken) {
      config.headers['X-CSRFToken'] = csrfToken;
    }
  }
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    const url = err.config?.url || '';
    // Don't hijack the login page (bad credentials) or the session-restore
    // call (AuthContext handles that 401 silently).
    const isAuthCall = url.includes('/auth/login') || url.includes('/auth/me');
    if (err.response?.status === 401 && !isAuthCall) {
      window.location.href = '/login';
    }
    return Promise.reject(err);
  },
);

export default api;
