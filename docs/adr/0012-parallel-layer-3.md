# 0012: Run Layer 3 in parallel with Layer 2

Status: accepted

## Context
Time is short for the event. Layer 3's pure domain code and the customer UI do not need Layer 2's backend.
Layer 1 is merged; Layer 2 is in progress at step 2.4.

## Decision
- Develop Layer 3 in a separate git worktree on branch `layer/3-customer-ui`, created from `main`.
- Phase 3A (customer API contract, comfort engine, ranking and alternatives) starts now from `main`.
- Phase 3B (customer UI against a fixture API) starts after Layer 2 step 2.5 is committed, by rebasing onto that commit.
- Phase 3C (customer sessions, consent and receipt, integration, tests) starts after Layer 2 is merged, by rebasing
  with `git rebase --onto origin/main <step-2.5-commit> layer/3-customer-ui`.
- Layer 3 merges only after Layer 2. No Alembic migrations in Layer 3 before the Layer 2 merge.
- Layer 3 routers are not mounted in the app until Phase 3C, to avoid conflicts in the composition root.
- ADR numbering: this ADR is 0012; the Layer 2 session uses 0013-0019; the Layer 3 session starts at 0020.
- Only the Layer 2 session edits the status table in CLAUDE.md; Layer 3 writes `docs/handoff/LAYER-3-WIP.md` until its own gate.

## Consequences
About 1.5 to 2.5 hours saved (estimate, not measured). Rebase work at two sync points, with small conflicts expected in
shared files. The fixture API and the real API may drift; controlled by the Phase 3A contract and a regenerated client.
The reviewer must watch for edits to Layer 2's files in Layer 3's diff.
