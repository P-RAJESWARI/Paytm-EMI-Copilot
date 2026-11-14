# 0007: Test database, coverage gates and fixture labelling

Status: Accepted (owner, 2026-11-14, as a stated default).

## Decision
- Integration tests use the Docker Compose PostgreSQL service with a separate `emi_copilot_test` database. `make check` **requires Docker** and fails with a clear message if Docker is not running.
- Coverage: `domain/` and the audit path (`events/audit_subscriber.py`, `repositories/audit_event_repository.py`) at 100% line and branch; `services/` and `adapters/` at 90%; overall at 85%. The per-directory gates are extra `coverage report --include=... --fail-under=...` lines in `make check`.
- Paytm fixtures are **documented-shape fixtures [Verify]**, written from the public docs with synthetic IDs, not recorded real responses. We replace them with recordings once staging keys exist.
