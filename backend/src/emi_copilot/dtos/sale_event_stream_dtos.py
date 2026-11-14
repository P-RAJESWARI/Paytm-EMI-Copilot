"""Wire format of GET /api/v1/sales/events: text/event-stream frames with a camelCase payload.

Frames:
- `event: sale-status` with `data: {"saleId", "status", "statusChangedAt"}`, and nothing else
  (rule 6: no customer detail, no step-by-step progress).
- `event: resync` with `data: {}` when the stream fell behind; read the counter list again.
  (A frame without data would not be dispatched by a browser EventSource.)
- `: heartbeat` comment lines while nothing happens, so proxies keep the connection open.
"""

from typing import Annotated

from pydantic import AwareDatetime, Field

from emi_copilot.domain.sales import SaleStatus
from emi_copilot.dtos.sale_dtos import EXAMPLE_SALE_ID, to_wire_moment
from emi_copilot.dtos.wire_types import CamelCaseResponseModel
from emi_copilot.events.sale_status_broadcaster import (
    SaleStatusFeedMessage,
    SaleStatusFeedMessageKind,
)

EVENT_STREAM_MEDIA_TYPE = "text/event-stream"
HEARTBEAT_FRAME = b": heartbeat\n\n"
RESYNC_FRAME = b"event: resync\ndata: {}\n\n"


class SaleStatusEventPayload(CamelCaseResponseModel):
    """The data of one sale-status event: which sale, its status now and since when."""

    sale_id: Annotated[str, Field(examples=[EXAMPLE_SALE_ID])]
    status: SaleStatus
    status_changed_at: Annotated[AwareDatetime, Field(description="When the status changed, UTC.")]


def encode_sale_status_frame(message: SaleStatusFeedMessage | None) -> bytes:
    """Encodes one feed message as an event-stream frame; None is a heartbeat comment."""
    if message is None:
        return HEARTBEAT_FRAME
    if message.kind is SaleStatusFeedMessageKind.RESYNC or message.update is None:
        return RESYNC_FRAME
    payload = SaleStatusEventPayload(
        sale_id=message.update.sale_id,
        status=message.update.status,
        status_changed_at=to_wire_moment(message.update.status_changed_at),
    )
    data_text = payload.model_dump_json(by_alias=True)
    return f"event: {SaleStatusFeedMessageKind.SALE_STATUS.value}\ndata: {data_text}\n\n".encode()
