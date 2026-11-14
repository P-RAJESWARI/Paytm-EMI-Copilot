"""GET /api/v1/sales/events: the signed-in shop's live sale statuses as Server-Sent Events.

The stream carries only {saleId, status, statusChangedAt} (rule 6), a resync event when the
client fell behind, and a heartbeat comment every 15 seconds by default. It ends when the
device token expires. Fan-out is in-process, so the API runs as a single uvicorn worker (ADR at
the Layer 2 gate). The token is read once by the bearer dependency and never logged.
"""

from collections.abc import AsyncIterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask

from emi_copilot.api.merchant_authentication import CurrentMerchant
from emi_copilot.api.openapi_documentation import (
    MERCHANT_AUTHENTICATION_PROBLEM,
    MERCHANT_BEARER_NOTE,
    describe_problem_responses,
)
from emi_copilot.api.sale_dependencies import SaleStatusFeedServiceDependency
from emi_copilot.dtos.sale_event_stream_dtos import (
    EVENT_STREAM_MEDIA_TYPE,
    SaleStatusEventPayload,
    encode_sale_status_frame,
)
from emi_copilot.services.sale_status_feed_service import SaleStatusFeed

# Registered before the sale router, so /sales/events is never read as /sales/{saleId}.
sale_event_stream_router = APIRouter(tags=["sales"])

# A proxy must neither cache nor buffer the stream (X-Accel-Buffering is nginx's switch).
EVENT_STREAM_HEADERS = {"Cache-Control": "no-store", "X-Accel-Buffering": "no"}
# A readable placeholder sale id: a real id inside escaped JSON trips the secret scanner.
SALE_STATUS_STREAM_EXAMPLE = (
    'event: sale-status\ndata: {"saleId":"sale-id","status":"READY_TO_PAY",'
    '"statusChangedAt":"2026-11-15T09:36:00Z"}\n\n: heartbeat\n\nevent: resync\ndata: {}\n\n'
)


async def encode_sale_status_stream(feed: SaleStatusFeed) -> AsyncIterator[bytes]:
    """Turns the feed's messages and heartbeats into event-stream frames as they come."""
    async for message in feed.follow():
        yield encode_sale_status_frame(message)


@sale_event_stream_router.get(
    "/sales/events",
    response_class=StreamingResponse,
    summary="Follow the shop's sale statuses live",
    description=(
        "Server-Sent Events. `event: sale-status` carries one sale's new status, with exactly "
        "saleId, status and statusChangedAt as JSON in data; it is sent only after the change "
        "is committed, and only to the shop that owns the sale. `event: resync` (data {}) means "
        "messages were dropped because the client fell behind: read GET /api/v1/sales?view="
        "counter again. A `: heartbeat` comment comes every 15 seconds while nothing happens. "
        "The stream ends when the device token expires. Send the token in the Authorization "
        "header (fetch-based client), never in the URL. " + MERCHANT_BEARER_NOTE
    ),
    response_description="An endless text/event-stream until the token expires.",
    responses={
        200: {
            "model": SaleStatusEventPayload,
            "content": {EVENT_STREAM_MEDIA_TYPE: {"example": SALE_STATUS_STREAM_EXAMPLE}},
        },
        **describe_problem_responses(MERCHANT_AUTHENTICATION_PROBLEM),
    },
)
async def stream_sale_status_events(
    current_merchant: CurrentMerchant, sale_status_feed_service: SaleStatusFeedServiceDependency
) -> StreamingResponse:
    """Subscribes before answering, then streams; the subscription closes with the response."""
    feed = sale_status_feed_service.open_feed(current_merchant)
    return StreamingResponse(
        encode_sale_status_stream(feed),
        media_type=EVENT_STREAM_MEDIA_TYPE,
        headers=EVENT_STREAM_HEADERS,
        background=BackgroundTask(feed.close),
    )
