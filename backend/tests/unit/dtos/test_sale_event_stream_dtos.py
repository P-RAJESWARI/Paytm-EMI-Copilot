"""The event-stream frames of GET /api/v1/sales/events: exact bytes, three fields only."""

import json
from datetime import UTC, datetime

from emi_copilot.domain.sales import SaleStatus
from emi_copilot.dtos.sale_event_stream_dtos import (
    HEARTBEAT_FRAME,
    RESYNC_FRAME,
    encode_sale_status_frame,
)
from emi_copilot.events.sale_status_broadcaster import (
    RESYNC_MESSAGE,
    SaleStatusFeedMessage,
    SaleStatusFeedMessageKind,
    SaleStatusUpdate,
)


def test_sale_status_frame_carries_exactly_id_status_and_time_in_utc_seconds() -> None:
    """The data line is camelCase JSON with the moment in UTC, rounded down to the second."""
    frame = encode_sale_status_frame(
        SaleStatusFeedMessage(
            SaleStatusFeedMessageKind.SALE_STATUS,
            SaleStatusUpdate(
                "01JD5Z0Q8M6X3V2N7B4C9K1T0F",
                SaleStatus.READY_TO_PAY,
                datetime(2026, 11, 15, 9, 36, 0, 987654, tzinfo=UTC),
            ),
        )
    )
    event_line, data_line, end = frame.decode().split("\n", 2)
    assert event_line == "event: sale-status"
    assert json.loads(data_line.removeprefix("data: ")) == {
        "saleId": "01JD5Z0Q8M6X3V2N7B4C9K1T0F",
        "status": "READY_TO_PAY",
        "statusChangedAt": "2026-11-15T09:36:00Z",
    }
    assert end == "\n"


def test_resync_and_heartbeat_frames_are_fixed_bytes() -> None:
    """A resync has empty JSON data so EventSource dispatches it; a heartbeat is a comment."""
    assert (
        encode_sale_status_frame(RESYNC_MESSAGE) == RESYNC_FRAME == b"event: resync\ndata: {}\n\n"
    )
    assert encode_sale_status_frame(None) == HEARTBEAT_FRAME == b": heartbeat\n\n"
