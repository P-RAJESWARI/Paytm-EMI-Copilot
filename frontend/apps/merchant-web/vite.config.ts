// Vite config for the merchant tablet app: React, Tailwind, port 5173, and /api proxied to FastAPI.
// MERCHANT_WEB_PORT and MERCHANT_WEB_API_PROXY_TARGET override the port and the proxy target, so
// the end-to-end run (`make e2e`) can use its own ports beside a running developer server.
import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

/** Port 5173 belongs to merchant-web; customer-web uses 5174. */
const MERCHANT_WEB_DEVELOPMENT_PORT = 5173;

/** Matches the Makefile defaults BACKEND_HOST=127.0.0.1 and BACKEND_PORT=8000 (`make dev`). */
const BACKEND_DEVELOPMENT_ORIGIN = 'http://127.0.0.1:8000';

// Reads the port from MERCHANT_WEB_PORT, or gives the development port when it is unset.
function readMerchantWebPort(): number {
  const configuredPort = process.env.MERCHANT_WEB_PORT;
  if (configuredPort === undefined || configuredPort === '') return MERCHANT_WEB_DEVELOPMENT_PORT;
  const port = Number(configuredPort);
  if (!Number.isInteger(port) || port <= 0) {
    throw new Error('MERCHANT_WEB_PORT must be a whole port number such as 5180');
  }
  return port;
}

// Reads the backend origin for /api from MERCHANT_WEB_API_PROXY_TARGET, or the development one.
function readApiProxyTarget(): string {
  const configuredTarget = process.env.MERCHANT_WEB_API_PROXY_TARGET;
  if (configuredTarget === undefined || configuredTarget === '') return BACKEND_DEVELOPMENT_ORIGIN;
  return configuredTarget;
}

const merchantWebPort = readMerchantWebPort();
const apiProxyTarget = readApiProxyTarget();

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: merchantWebPort,
    strictPort: true,
    proxy: { '/api': apiProxyTarget },
  },
  preview: { port: merchantWebPort, strictPort: true },
});
