// Vite config for the merchant tablet app: React, Tailwind, port 5173, and /api proxied to FastAPI.
import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

/** Port 5173 belongs to merchant-web; customer-web uses 5174. */
const MERCHANT_WEB_DEVELOPMENT_PORT = 5173;

/** Matches the Makefile defaults BACKEND_HOST=127.0.0.1 and BACKEND_PORT=8000 (`make dev`). */
const BACKEND_DEVELOPMENT_ORIGIN = 'http://127.0.0.1:8000';

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: MERCHANT_WEB_DEVELOPMENT_PORT,
    strictPort: true,
    proxy: { '/api': BACKEND_DEVELOPMENT_ORIGIN },
  },
  preview: { port: MERCHANT_WEB_DEVELOPMENT_PORT, strictPort: true },
});
