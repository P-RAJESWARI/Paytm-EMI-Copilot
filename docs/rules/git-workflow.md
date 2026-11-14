# git-workflow.md: Git and review workflow

Goal: every layer arrives as one clean, reviewable merge request (MR) built from small, explained commits.

## 1. Branches

| Branch | Purpose |
|---|---|
| `main` | Always green and runnable. Receives one MR per layer. |
| `layer/1-payment-gateway` | Foundation + payment gateway integration |
| `layer/2-merchant-ui` | Merchant UI and merchant backend slice |
| `layer/3-customer-ui` | Customer UI and customer backend slice |
| `layer/4-sarvam-ai` | Sarvam AI integration |
| `fix/<short-name>` | Review fixes inside a layer branch that grow too large for fixup commits |

Each layer branch starts from the latest `main` (after the previous layer's MR is merged). Never force-push a branch someone has already reviewed; add commits instead.

## 2. Commit style (Conventional Commits)

```
<type>(<scope>): <summary in the imperative, under 72 characters>

What: one or two lines on what changed.
Why: the reason, or the decision it implements.
Review: what the reviewer should look at first.
```

Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `build`, `ci`.  
Scopes: `domain`, `core`, `gateway`, `api`, `db`, `merchant-ui`, `customer-ui`, `ui-kit`, `ai`, `rules`.

Example:

```
feat(gateway): add Paytm payment gateway adapter behind PaymentGatewayPort

What: Adapter signs requests, calls Initiate/Status endpoints and maps errors to domain errors.
Why: Services must depend on a port so the mock and the real gateway are interchangeable.
Review: Error mapping in paytm_error_translator.py and that initiate calls are never retried.
```

Rules:
- **One logical change per commit.** The project builds and `make check` passes at every commit.
- Tests ship in the same commit as the code they cover (or the commit before).
- Never commit secrets, `.env`, generated build output or large binaries.
- No "WIP" or "fix stuff" commits on a layer branch that goes to review; squash locally first.

## 3. Commit order inside a layer

Prefer this sequence so the diff reads like a story:

1. `docs` / `chore`: rules, config, scaffolding
2. `feat(domain)`: pure domain code with its tests
3. `feat(db)`: models, migration, repositories with tests
4. `feat(<adapter>)`: ports, mock, real adapter with contract tests
5. `feat(api)`: services, controllers, DTOs with integration tests
6. `docs`: layer summary and handoff file

## 4. Merge request

Generate the reviewable diff and stats with (until a remote exists, use `main` in place of `origin/main` and skip `git fetch`; ADR 0008):

```
git fetch origin
git diff --stat origin/main...HEAD
git diff origin/main...HEAD > layer-N.diff
git log --oneline origin/main..HEAD
```

**MR description template** (also written to `docs/handoff/LAYER-N-HANDOFF.md`):

```
## What was built
## Why (decisions and trade-offs)
## Patterns used (with file references)
## How to run and verify (commands)
## What to review first
## Not done / follow-ups
## Open questions
```

**MR size:** aim for under about 1,500 changed lines excluding lockfiles and generated clients. If larger, split by commit groups and say so in the description.

## 5. Review checklist (reviewer agent and human)

- [ ] Layering rules from `backend.md` or `frontend.md` respected
- [ ] Names are readable; every function has its purpose comment; patterns named
- [ ] No file, class or function over the soft limits without justification
- [ ] Non-negotiable rules in `CLAUDE.md` section 2 respected
- [ ] Tests exist for new behaviour; coverage thresholds met
- [ ] Error handling uses typed errors; no swallowed exceptions
- [ ] No secrets, no personal data in logs, fixtures or comments
- [ ] OpenAPI and generated client are in sync
- [ ] Layer handoff file and status table updated

## 6. Hooks and CI

- `pre-commit`: ruff, ruff-format, mypy (changed files), ESLint, Prettier, detect-secrets.
- CI on every push: `make check`, OpenAPI sync check, and for Layers 2 and 3 the Playwright happy path.
