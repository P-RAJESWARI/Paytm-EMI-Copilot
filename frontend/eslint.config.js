// ESLint flat config for every app and package; `pnpm lint` fails on any warning (frontend.md section 11).
import javascript from '@eslint/js';
import jsxAccessibility from 'eslint-plugin-jsx-a11y';
import reactHooks from 'eslint-plugin-react-hooks';
import globals from 'globals';
import typescriptEslint from 'typescript-eslint';

export default typescriptEslint.config(
  {
    ignores: [
      '**/node_modules/**',
      '**/dist/**',
      '**/coverage/**',
      '**/src/generated/**',
      'e2e/test-results/**',
      'e2e/playwright-report/**',
    ],
  },
  javascript.configs.recommended,
  ...typescriptEslint.configs.strictTypeChecked,
  ...typescriptEslint.configs.stylisticTypeChecked,
  jsxAccessibility.flatConfigs.strict,
  reactHooks.configs.flat.recommended,
  {
    languageOptions: {
      globals: { ...globals.browser },
      parserOptions: {
        projectService: { allowDefaultProject: ['*.js'] },
        tsconfigRootDir: import.meta.dirname,
      },
    },
    rules: {
      '@typescript-eslint/no-non-null-assertion': 'error',
      '@typescript-eslint/no-explicit-any': 'error',
      '@typescript-eslint/consistent-type-imports': 'error',
      '@typescript-eslint/restrict-template-expressions': ['error', { allowNumber: true }],
      'no-console': 'error',
      // The WAI-ARIA tabs pattern makes the tab panel focusable so keyboard users can reach it.
      'jsx-a11y/no-noninteractive-tabindex': ['error', { tags: [], roles: ['tabpanel'] }],
    },
  },
  {
    files: ['**/*.js'],
    extends: [typescriptEslint.configs.disableTypeChecked],
    languageOptions: { globals: { ...globals.node } },
  },
);
