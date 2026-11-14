# 0008: Tooling, naming and extra libraries for Layer 1

Status: Accepted (owner, 2026-11-14, as stated defaults).

## Decision
- There is no git remote yet, so diff commands use `main...HEAD` until one exists. The folder name stays `Paytm-emi-copilot`.
- New commit scope `core` (logging, HTTP client, clock, ids). The checksum module is named `checksum_signer.py`.
- Extra libraries, pinned exactly and at least two weeks old: python-ulid, cryptography, openapi-spec-validator, detect-secrets, and `paytmchecksum` (dev only). Logging uses a stdlib JSON formatter (no structlog). Retry and the circuit breaker are built in-house.
- There is no separate `Paise` type. `Money.to_paise() -> int` is the boundary conversion.
- `api/dependencies.py` is the composition root. It is the only module outside `adapters/` allowed to import the gateway factory.
