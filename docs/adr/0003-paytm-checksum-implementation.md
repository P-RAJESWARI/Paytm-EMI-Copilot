# 0003: Paytm checksum implementation

Status: Accepted (owner, 2026-11-14). Answers Layer 1 question 7.

## Context
The official `paytmchecksum` package (1.7.0, July 2020) is untyped, depends on pycryptodome, picks a random salt and mutates the dict passed to it. That fails `mypy --strict` and prevents a deterministic known-answer test. Paytm publishes no test vector.

## Decision
- Port the algorithm into `adapters/payment_gateway/checksum_signer.py` using `cryptography`, with an injectable salt source. The algorithm: sha256(`payload|salt`) hex digest plus salt, then AES-128-CBC with the documented fixed IV, then base64. For a dict, the payload is the values of the sorted keys joined by `|`.
- A dev-only test dependency on `paytmchecksum` cross-checks that signatures interoperate in both directions.
- We generate our own known-answer vector from a synthetic key. **[Verify]** against a real staging response once keys exist.
