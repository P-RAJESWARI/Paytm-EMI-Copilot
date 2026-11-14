"""Tests for JSON log formatting, correlation IDs and redaction of sensitive data."""

import io
import json
import logging
import sys
from collections.abc import Iterator

import httpx
import pytest

from emi_copilot.core.logging import (
    HTTP_CLIENT_LOGGER_NAMES,
    JSON_HANDLER_NAME,
    UVICORN_ACCESS_LOGGER_NAME,
    UVICORN_LOGGER_NAMES,
    JsonLogFormatter,
    SensitiveDataRedactionFilter,
    configure_logging,
    redact_sensitive_text,
)
from emi_copilot.core.request_context import correlation_id_context

SYNTHETIC_CORRELATION_ID = "01JD0000000000000000000000"
SYNTHETIC_BEARER_VALUE = "synthetic-bearer-value-for-tests"
SYNTHETIC_PHONE_NUMBER = "9876543210"


@pytest.fixture
def log_output_stream() -> Iterator[io.StringIO]:
    """Attaches a redacting JSON handler to a dedicated test logger and yields its output."""
    output_stream = io.StringIO()
    handler = logging.StreamHandler(output_stream)
    handler.addFilter(SensitiveDataRedactionFilter())
    handler.setFormatter(JsonLogFormatter())
    test_logger = logging.getLogger("emi_copilot.tests.logging")
    test_logger.addHandler(handler)
    test_logger.setLevel(logging.DEBUG)
    yield output_stream
    test_logger.removeHandler(handler)


def read_single_log_line(output_stream: io.StringIO) -> dict[str, object]:
    """Parses the one JSON log line written to the stream."""
    log_lines = output_stream.getvalue().splitlines()
    assert len(log_lines) == 1
    parsed_line: dict[str, object] = json.loads(log_lines[0])
    return parsed_line


def test_json_log_formatter_inside_request_emits_json_with_correlation_id(
    log_output_stream: io.StringIO,
) -> None:
    """Every log line written during a request carries that request's correlation ID."""
    context_token = correlation_id_context.set(SYNTHETIC_CORRELATION_ID)
    try:
        logging.getLogger("emi_copilot.tests.logging").info("offer discovery started")
    finally:
        correlation_id_context.reset(context_token)
    log_line = read_single_log_line(log_output_stream)
    assert log_line["correlation_id"] == SYNTHETIC_CORRELATION_ID
    assert log_line["message"] == "offer discovery started"
    assert log_line["level"] == "INFO"
    assert log_line["logger"] == "emi_copilot.tests.logging"
    assert str(log_line["timestamp"]).endswith("Z")


def test_json_log_formatter_outside_request_emits_null_correlation_id(
    log_output_stream: io.StringIO,
) -> None:
    """Startup lines have no request, so the correlation ID key is present but null."""
    logging.getLogger("emi_copilot.tests.logging").info("application started")
    log_line = read_single_log_line(log_output_stream)
    assert "correlation_id" in log_line
    assert log_line["correlation_id"] is None


def test_json_log_formatter_includes_extra_fields(log_output_stream: io.StringIO) -> None:
    """Structured event fields passed with extra= appear as top-level JSON keys."""
    logging.getLogger("emi_copilot.tests.logging").info(
        "payment status checked", extra={"http_status_code": 200}
    )
    assert read_single_log_line(log_output_stream)["http_status_code"] == 200


def test_redaction_filter_masks_bearer_token_in_message(log_output_stream: io.StringIO) -> None:
    """A bearer token in a message is replaced and the raw token never reaches the output."""
    logging.getLogger("emi_copilot.tests.logging").info(
        "incoming header Authorization: Bearer %s", SYNTHETIC_BEARER_VALUE
    )
    assert SYNTHETIC_BEARER_VALUE not in log_output_stream.getvalue()
    assert "[REDACTED]" in str(read_single_log_line(log_output_stream)["message"])


def test_redaction_filter_masks_phone_number_keeping_last_two_digits(
    log_output_stream: io.StringIO,
) -> None:
    """Phone numbers keep only their last two digits for display (security rules section 2)."""
    logging.getLogger("emi_copilot.tests.logging").info(
        "otp requested for %s", SYNTHETIC_PHONE_NUMBER
    )
    output = log_output_stream.getvalue()
    assert SYNTHETIC_PHONE_NUMBER not in output
    assert read_single_log_line(log_output_stream)["message"] == "otp requested for ********10"


def test_redaction_filter_redacts_sensitive_extra_fields(log_output_stream: io.StringIO) -> None:
    """Extra fields named like secrets are blanked and phone numbers inside others are masked."""
    logging.getLogger("emi_copilot.tests.logging").info(
        "webhook received",
        extra={"checksum_hash": "synthetic-checksum-value", "customer_contact": "+91 98765 43210"},
    )
    output = log_output_stream.getvalue()
    log_line = read_single_log_line(log_output_stream)
    assert "synthetic-checksum-value" not in output
    assert log_line["checksum_hash"] == "[REDACTED]"
    assert log_line["customer_contact"] == "********10"


def test_redaction_filter_redacts_secrets_inside_exception_text(
    log_output_stream: io.StringIO,
) -> None:
    """A secret inside an exception message is redacted in the logged traceback."""
    try:
        raise ValueError("merchant_key=synthetic-merchant-key-value rejected")  # noqa: TRY301
    except ValueError:
        logging.getLogger("emi_copilot.tests.logging").exception("gateway call failed")
    output = log_output_stream.getvalue()
    assert "synthetic-merchant-key-value" not in output
    assert "ValueError" in str(read_single_log_line(log_output_stream)["exception"])


@pytest.mark.parametrize(
    ("raw_text", "expected_redacted_text"),
    [
        ("Authorization: Basic c3ludGhldGljOnBhc3M=", "Authorization: [REDACTED]"),
        ('{"sessionToken": "synthetic token value"}', '{"sessionToken": [REDACTED]}'),
        ("signature=synthetic-signature&orderId=ORDER-1", "signature=[REDACTED]&orderId=ORDER-1"),
        ("call +919876543210 now", "call ********10 now"),
        ("call 09876543210 now", "call ********10 now"),
        ("price_in_paise=2200000 order 01JD0000000000000000000000", None),
    ],
)
def test_redact_sensitive_text_masks_only_sensitive_values(
    raw_text: str, expected_redacted_text: str | None
) -> None:
    """Secrets, tokens and phone numbers are masked; amounts and IDs stay readable."""
    assert redact_sensitive_text(raw_text) == (expected_redacted_text or raw_text)


def test_configure_logging_called_twice_installs_exactly_one_json_handler() -> None:
    """Building the application repeatedly (as tests do) never duplicates log lines."""
    configure_logging("INFO")
    configure_logging("DEBUG")
    root_logger = logging.getLogger()
    json_handlers = [
        handler for handler in root_logger.handlers if handler.get_name() == JSON_HANDLER_NAME
    ]
    assert len(json_handlers) == 1
    assert root_logger.level == logging.DEBUG


def test_configure_logging_routes_uvicorn_loggers_through_the_root_handler() -> None:
    """Uvicorn's server handlers are removed so its lines are JSON and redacted too."""
    logging.getLogger("uvicorn.error").addHandler(logging.NullHandler())
    configure_logging("INFO")
    for uvicorn_logger_name in UVICORN_LOGGER_NAMES:
        uvicorn_logger = logging.getLogger(uvicorn_logger_name)
        assert uvicorn_logger.handlers == []
        assert uvicorn_logger.propagate is True


def test_configure_logging_silences_uvicorn_access_log_in_favour_of_request_event() -> None:
    """Uvicorn's access line logs the query string; the request-completed event replaces it."""
    logging.getLogger(UVICORN_ACCESS_LOGGER_NAME).addHandler(logging.NullHandler())
    configure_logging("INFO")
    uvicorn_access_logger = logging.getLogger(UVICORN_ACCESS_LOGGER_NAME)
    assert uvicorn_access_logger.handlers == []
    assert uvicorn_access_logger.propagate is False


def test_configure_logging_keeps_http_client_request_lines_with_query_strings_out(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The httpx INFO request line holds the full URL and query, so it is never emitted."""
    configure_logging("DEBUG")
    http_client = httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200)))
    with caplog.at_level(logging.DEBUG), http_client:
        http_client.get("https://gateway.example.test/path?merchantRef=SYNTHETIC-REF-0001")
    assert "SYNTHETIC-REF-0001" not in caplog.text
    for http_client_logger_name in HTTP_CLIENT_LOGGER_NAMES:
        assert logging.getLogger(http_client_logger_name).level == logging.WARNING


def test_json_log_formatter_without_redaction_filter_still_renders_exception() -> None:
    """The formatter renders the traceback itself when no filter prepared it."""
    try:
        raise RuntimeError("formatter only")  # noqa: TRY301
    except RuntimeError:
        record = logging.LogRecord(
            "emi_copilot.tests", logging.ERROR, __file__, 1, "failed", None, sys.exc_info()
        )
    rendered_line = json.loads(JsonLogFormatter().format(record))
    assert "RuntimeError: formatter only" in rendered_line["exception"]
