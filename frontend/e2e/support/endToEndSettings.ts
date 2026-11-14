// Ports, the e2e database URL and the demo shop's sign-in details, read from the environment that
// `make e2e` sets. Defaults keep clear of the developer servers (8000, 5173) and Layer 3 (8001, 5174).

/** The demo shop the seed creates (backend/scripts/seed_demo_data.py). */
export const DEMO_SHOP_ID = 'RAVI-0193';

const DEFAULT_BACKEND_PORT = 8010;
const DEFAULT_MERCHANT_WEB_PORT = 5180;

// Reads a whole port number from the environment, or gives the default when the variable is unset.
function readPortFromEnvironment(variableName: string, defaultPort: number): number {
  const configuredPort = process.env[variableName];
  if (configuredPort === undefined || configuredPort === '') return defaultPort;
  const port = Number(configuredPort);
  if (!Number.isInteger(port) || port <= 0) {
    throw new Error(`${variableName} must be a whole port number`);
  }
  return port;
}

// Reads a variable that only `make e2e` can provide, and explains how to run when it is missing.
function readRequiredVariable(variableName: string): string {
  const value = process.env[variableName];
  if (value === undefined || value === '') {
    throw new Error(
      `${variableName} is not set. Run the end-to-end tests with \`make e2e\`, which prepares ` +
        'the e2e database and sets it (see frontend/e2e/README.md).',
    );
  }
  return value;
}

export const BACKEND_PORT = readPortFromEnvironment('E2E_BACKEND_PORT', DEFAULT_BACKEND_PORT);
export const MERCHANT_WEB_PORT = readPortFromEnvironment(
  'E2E_MERCHANT_WEB_PORT',
  DEFAULT_MERCHANT_WEB_PORT,
);
// Loopback addresses, not "localhost": that name may resolve to ::1 first, and HTTP proxy settings
// commonly exempt 127.0.0.1 but not "localhost".
export const BACKEND_ORIGIN = `http://127.0.0.1:${BACKEND_PORT}`;
export const MERCHANT_WEB_ORIGIN = `http://127.0.0.1:${MERCHANT_WEB_PORT}`;

// Gives the e2e database URL that `make e2e` created, migrated and seeded.
export function readEndToEndDatabaseUrl(): string {
  return readRequiredVariable('E2E_DATABASE_URL');
}

// Gives the throwaway pairing PIN that `make e2e` seeded into the e2e database.
export function readDemoShopPin(): string {
  return readRequiredVariable('E2E_MERCHANT_PIN');
}
