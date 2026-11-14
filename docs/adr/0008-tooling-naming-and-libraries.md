# 0008: Tooling, naming and extra libraries for Layer 1

Status: Accepted (owner, 2026-11-14, as stated defaults).

## Decision
- There is no git remote yet, so diff commands use `main...HEAD` until one exists. The folder name stays `Paytm-emi-copilot`.
- New commit scope `core` (logging, HTTP client, clock, ids). The checksum module is named `checksum_signer.py`.
- Extra libraries, pinned exactly and at least two weeks old: python-ulid, cryptography, openapi-spec-validator, detect-secrets, and `paytmchecksum` (dev only). Logging uses a stdlib JSON formatter (no structlog). Retry and the circuit breaker are built in-house.
- There is no separate `Paise` type. `Money.to_paise() -> int` is the boundary conversion.
- `api/dependencies.py` is the composition root. It is the only module outside `adapters/` allowed to import the gateway factory.
- Added after step 1.0 (orchestrator, conservative default, 2026-11-14): `coverage==7.17.0` is pinned directly because the Makefile calls its CLI for the per-directory gates. Starlette 1.10 warns that its TestClient prefers `httpx2`; we do **not** add `httpx2`. A single narrow `filterwarnings` ignore for that exact message is kept in `pyproject.toml`, and `httpx` stays the one HTTP client.
