// One Vitest run for every app and package: jsdom, Testing Library cleanup and the 80% gate.
import { fileURLToPath } from 'node:url';

import react from '@vitejs/plugin-react';
import { defineConfig } from 'vitest/config';

const FRONTEND_OVERALL_COVERAGE_MINIMUM_PERCENT = 80;

/** testing.md section 5: the customer flow reducer (the step machine) is covered completely. */
const CUSTOMER_FLOW_REDUCER_FILES =
  'apps/customer-web/src/features/customer-flow/model/customerFlowReducer.ts';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@test-support': fileURLToPath(new URL('./test-support', import.meta.url)),
    },
  },
  test: {
    environment: 'jsdom',
    include: ['apps/*/src/**/*.test.{ts,tsx}', 'packages/*/src/**/*.test.{ts,tsx}'],
    setupFiles: ['./test-support/setupTests.ts'],
    css: false,
    restoreMocks: true,
    unstubGlobals: true,
    passWithNoTests: true,
    coverage: {
      provider: 'v8',
      include: ['apps/*/src/**/*.{ts,tsx}', 'packages/*/src/**/*.{ts,tsx}'],
      exclude: [
        '**/*.test.{ts,tsx}',
        '**/src/generated/**',
        '**/src/main.tsx',
        '**/src/index.ts',
        '**/*.d.ts',
      ],
      reporter: ['text-summary', 'text'],
      thresholds: {
        lines: FRONTEND_OVERALL_COVERAGE_MINIMUM_PERCENT,
        branches: FRONTEND_OVERALL_COVERAGE_MINIMUM_PERCENT,
        functions: FRONTEND_OVERALL_COVERAGE_MINIMUM_PERCENT,
        statements: FRONTEND_OVERALL_COVERAGE_MINIMUM_PERCENT,
        [CUSTOMER_FLOW_REDUCER_FILES]: {
          lines: 100,
          branches: 100,
          functions: 100,
          statements: 100,
        },
      },
    },
  },
});
