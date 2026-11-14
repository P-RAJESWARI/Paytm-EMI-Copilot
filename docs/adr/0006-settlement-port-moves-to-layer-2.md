# 0006: Settlement port moves to Layer 2

Status: Accepted (owner, 2026-11-14). Answers Layer 1 question 11.

## Decision
IMPLEMENTATION_PLAN.md step 1.5 listed a `SettlementPort` with a labelled Mock. No domain types for it exist yet, and its only consumer (M5 "Money due from brands") needs merchant scoping, which arrives in Layer 2. The port and its Mock move to Layer 2, next to the reports slice.
