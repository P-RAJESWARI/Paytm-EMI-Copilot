# frontend.md: Frontend coding rules

Applies to everything under `frontend/`. Default stack: React 18, TypeScript (strict), Vite, Tailwind driven by design tokens, TanStack Query, react-i18next, pnpm workspaces. `[DEFAULT]`

## 1. Workspace layout

```
frontend/
  package.json  pnpm-workspace.yaml  tsconfig.base.json
  apps/
    merchant-web/               tablet-first PWA, authenticated (Layer 2)
      src/
        app/                    router, providers, app shell
        features/<feature>/     one folder per feature (see section 2)
        pages/                  thin route components that compose features
        i18n/                   merchant strings (English, Tamil)
    customer-web/               phone-first PWA opened from a QR, no install (Layer 3)
      src/ (same shape)
  packages/
    ui-kit/                     tokens.css, shared presentational components
    api-client/                 typed client generated from the backend OpenAPI schema
    shared-i18n/                strings used by both apps (money, bands, common labels)
```

Two apps, not one, so the customer bundle stays small on weak networks and the merchant app can be authenticated without touching the public customer flow.

## 2. Feature folder structure

```
features/<feature-name>/
  components/     presentational components (props in, JSX out)
  containers/     components that fetch data or hold feature state, then render components
  hooks/          useXyz hooks (data fetching, flow logic)
  model/          TypeScript types, constants, pure helper functions
  api/            thin wrappers over packages/api-client for this feature
  index.ts        the feature's public exports (nothing else is imported from outside)
```

Rules: a feature never imports another feature's internals; shared code moves to `packages/`.

## 3. Component rules

- **Presentational vs container:** presentational components have no data fetching and no routing; they render from props. Containers connect them to hooks.
- One component per file, named exactly like the file (`PlanComparisonCard.tsx`). Function components only.
- Soft limit 150 lines per component; extract subcomponents or hooks beyond that.
- **No business logic in the UI.** The UI never computes EMI, extra cost, comfort ratio or bands. It displays what the API returns. Display formatting only (Indian digit grouping, labels).
- Props are typed with an explicit `interface`; no `any`; no non-null assertions to silence the compiler.
- Each component and custom hook has a one or two line comment above it stating its purpose.

## 4. Naming

- Components `PascalCase`, hooks `useCamelCase`, functions and variables `camelCase`, constants `UPPER_SNAKE_CASE`, types and interfaces `PascalCase`.
- Event handlers: `handleSelectPlan`, `handleConfirmBudget`. Props that take handlers: `onSelectPlan`.
- Booleans read as questions: `isOtpExpired`, `hasConsentedToComfortCheck`.
- Money props carry the unit: `monthlyInstallmentInPaise`, `extraInTotalInPaise`.
- No abbreviations (`btn`, `msg`, `idx`) in new code.

## 5. State management

| Kind of state | Tool |
|---|---|
| Server data (sales, plans, reports) | TanStack Query; query keys defined in each feature's `api/` |
| Customer flow position and answers | A single typed reducer (or state machine) in `features/customer-flow/model/`; steps are an explicit union type |
| Form fields | react-hook-form with schema validation |
| Language | react-i18next; chosen language persisted per device |
| Everything else | Local `useState`; do not add a global store without an ADR |

Live sale status on the merchant side uses Server-Sent Events wrapped in one hook (`useLiveSaleStatus`), with polling as the fallback.

## 6. Styling and design tokens

- Tokens live in `packages/ui-kit/tokens.css` as CSS variables and are mapped into Tailwind's theme. Values come from `docs/design/DESIGN_SPEC.md`; never hard-code hex values in components.
- Text-safe band colours (green text `#0A6E50` on `#E3F7F0`, orange `#8A5300` on `#FEF3DC`, red `#B4232A` on `#FDE8E8`) are tokens, not ad hoc classes. Cyan buttons carry navy labels, never white.
- Comfort bands always render icon **and** word, never colour alone.
- Fonts: Inter (English) and Noto Sans Tamil in one stack; tabular numerals for money.
- Touch targets at least 48 px, primary actions 56 px. Customer screens at least 16 px body text.
- Do not use Paytm logos or copied assets.

## 7. Internationalisation

- All visible text goes through `t('key')`. No literal strings in JSX except non-visible attributes.
- Keys are semantic (`plan.extraInTotal.label`), not sentences.
- English and Tamil must exist for every customer-facing key. Tamil strings are drafts until a native speaker reviews them; mark them `// draft: needs native review` in the translation file.
- Language toggle on every customer screen.

## 8. Accessibility (blocking, not optional)

- Real `button`, `a`, `input` and `label` elements; never `onClick` on a `div`.
- `aria-label` on icon-only buttons; decorative SVG `aria-hidden`.
- Text contrast at least 4.5:1; colours that must differ also differ in lightness and carry an icon or word.
- Every screen reachable and operable by keyboard; visible focus ring.
- Run `axe` in component tests for each screen.

## 9. Data and API access

- Use only `packages/api-client` (generated from the backend OpenAPI schema with `make openapi`). Never hand-write request types that the schema already provides.
- Handle all four states in every data screen: loading (skeleton), empty, error (calm wording), success.
- Never put tokens or merchant secrets in `localStorage`; the customer QR token lives only in memory and the URL fragment is removed after reading.

## 10. Performance

Customer app budget: initial JS under 150 KB gzipped `[Inferred target]`; route-level code splitting; no heavy animation; images only where the design shows them.

## 11. Quality gates (`make check`)

`tsc --noEmit`, ESLint (no warnings allowed), Prettier check, Vitest with coverage thresholds from `testing.md`, axe checks, and the Playwright happy path on CI for Layers 2 and 3.
