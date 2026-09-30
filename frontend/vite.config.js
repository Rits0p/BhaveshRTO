import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

// `process.env` is NOT populated from `.env` files while this config is being
// evaluated, so VITE_BACKEND_PORT has to be read via `loadEnv`. Reading it off
// `process.env` silently fell through to the hardcoded default and proxied
// `/api` at a port where nothing was listening, which surfaced in the SPA as
// an opaque "Login failed" toast on every login attempt.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const backendPort = env.VITE_BACKEND_PORT || '8000';

  return {
    plugins: [react(), tailwindcss()],
    server: {
      port: 5173,
      proxy: {
        '/api': {
          target: `http://localhost:${backendPort}`,
          changeOrigin: true,
        },
      },
    },
  };
});
