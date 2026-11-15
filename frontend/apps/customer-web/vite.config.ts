// Vite config for the customer phone app (Layer 3): React, Tailwind, port 5174, /api proxied to FastAPI.
// CUSTOMER_WEB_PORT and CUSTOMER_WEB_API_PROXY_TARGET override the port and the proxy target, so a
// second backend (Layer 3 uses 8001) or the end-to-end run can sit beside a developer server.
import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

/** Port 5174 belongs to customer-web; merchant-web uses 5173. */
const CUSTOMER_WEB_DEVELOPMENT_PORT = 5174;

/** The Layer 3 backend port (PARALLEL_LAYER_3.md section 2, rule 5). */
const BACKEND_DEVELOPMENT_ORIGIN = 'http://127.0.0.1:8001';

// Reads the port from CUSTOMER_WEB_PORT, or gives the development port when it is unset.
function readCustomerWebPort(): number {
  const configuredPort = process.env.CUSTOMER_WEB_PORT;
  if (configuredPort === undefined || configuredPort === '') return CUSTOMER_WEB_DEVELOPMENT_PORT;
  const port = Number(configuredPort);
  if (!Number.isInteger(port) || port <= 0) {
    throw new Error('CUSTOMER_WEB_PORT must be a whole port number such as 5184');
  }
  return port;
}

// Reads the backend origin for /api from CUSTOMER_WEB_API_PROXY_TARGET, or the development one.
function readApiProxyTarget(): string {
  const configuredTarget = process.env.CUSTOMER_WEB_API_PROXY_TARGET;
  if (configuredTarget === undefined || configuredTarget === '') return BACKEND_DEVELOPMENT_ORIGIN;
  return configuredTarget;
}

const customerWebPort = readCustomerWebPort();
const apiProxyTarget = readApiProxyTarget();

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: customerWebPort,
    strictPort: true,
    proxy: { '/api': apiProxyTarget },
  },
  preview: { port: customerWebPort, strictPort: true },
});
