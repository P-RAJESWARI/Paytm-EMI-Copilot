/// <reference types="vite/client" />

// The customer app's build-time settings (Vite exposes only VITE_ variables to the browser).
interface ImportMetaEnv {
  /** "fixture" answers the design sample instead of calling the backend; anything else uses HTTP. */
  readonly VITE_CUSTOMER_FLOW_API?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
