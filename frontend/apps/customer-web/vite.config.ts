// Vite config for the customer phone app (Layer 3): React, Tailwind, port 5174, /api proxied to FastAPI.
import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

/** Port 5174 belongs to customer-web; merchant-web uses 5173. */
const CUSTOMER_WEB_DEVELOPMENT_PORT = 5174;

/** Matches the Makefile defaults BACKEND_HOST=127.0.0.1 and BACKEND_PORT=8000 (`make dev`). */
const BACKEND_DEVELOPMENT_ORIGIN = 'http://127.0.0.1:8000';

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: CUSTOMER_WEB_DEVELOPMENT_PORT,
    strictPort: true,
    proxy: { '/api': BACKEND_DEVELOPMENT_ORIGIN },
  },
  preview: { port: CUSTOMER_WEB_DEVELOPMENT_PORT, strictPort: true },
});
