# 0019: Frontend workspace, generated API client and end-to-end isolation

Status: Accepted (owner, 2026-11-14: Layer 2 plan, steps 2.5 to 2.7, Q19, Q22).

## Decision
- **Workspace:** pnpm 12.15 and Node 20 (pinned via `packageManager` and `.nvmrc`); `apps/merchant-web` (port 5173), `apps/customer-web` (port 5174, an empty shell for Layer 3), `packages/ui-kit`, `packages/api-client`, `packages/shared-i18n`, `e2e`. Every dependency is pinned exactly, and `minimumReleaseAge` (14 days) makes pnpm enforce the age rule for indirect dependencies.
- **Styling:** Tailwind 4 with only the design tokens (Tailwind's default colours, sizes, radii and shadows are removed). Spec sizes win over mockup sizes: 48 px targets, 56 px primary buttons, money 32/700 with tabular numerals.
- **API client:** `openapi-typescript` types plus an `openapi-fetch` client generated from `backend/openapi.json`, with `Authorization` (token from an in-memory getter) and `X-Correlation-Id` middleware. `make openapi` regenerates both; `make openapi-check` fails on drift (no CI exists yet, so it runs locally).
- **Quality gate:** `make check` runs the backend gates and then tsc, ESLint (zero warnings), Prettier and Vitest with axe.
- **End to end:** `make e2e` recreates a separate `emi_copilot_e2e` database, seeds it with a throwaway PIN and runs Playwright against a backend on 8010 and merchant-web on 5180, so the developer database and ports, and the Layer 3 worktree's, are never touched. Axe runs in Chromium there because jsdom cannot measure colour contrast.
- **Parallel Layer 3:** after commit 93f2a5b (sync point for the Layer 3 rebase), changes to `ui-kit`, `api-client` and `shared-i18n` are additive only.

## Consequences
The merchant bundle is about 153 KB gzipped (the 150 KB budget applies to the customer app). The e2e projects run in a declared order (tablet, then phone) with one worker.
