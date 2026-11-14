# 0016: Live sale status over server-sent events

Status: Accepted (owner, 2026-11-14: Layer 2 plan, step 2.3).

## Decision
- `GET /api/v1/sales/events` is an `async` `text/event-stream` endpoint. Events: `sale-status` with `{saleId, status, statusChangedAt}` only, `resync` after an overflow, and a heartbeat comment every 15 s. The stream ends when the merchant token expires.
- The browser reads it with `fetch` and the `Authorization` header (`useLiveSaleStatus`), never `EventSource` with a token in the URL. After three failed connections it falls back to polling the counter list every 5 s.
- `SaleStatusBroadcaster` (Pattern: Observer) subscribes to `SaleStarted` and `SaleStatusChanged` but delivers only through the unit of work's `call_after_commit`, so a rolled-back change is never announced.
- Fan-out is in-process: bounded per-stream `asyncio.Queue`s, filled from worker threads with `call_soon_threadsafe`; on overflow the backlog is replaced by one `resync`.

## Consequences
The API must run with a **single uvicorn worker** (as `make demo` and `make e2e` do). Several workers or hosts would need a shared broker (for example PostgreSQL LISTEN/NOTIFY or Redis) behind the same broadcaster.
