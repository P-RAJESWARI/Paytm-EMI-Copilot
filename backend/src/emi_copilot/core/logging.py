"""Structured JSON logging with a correlation ID on every line and redaction of secrets."""

import json
import logging
import re
import sys
from datetime import UTC, datetime

from emi_copilot.core.request_context import get_current_correlation_id

REDACTED_VALUE = "[REDACTED]"
JSON_HANDLER_NAME = "emi_copilot_json"
VISIBLE_PHONE_DIGIT_COUNT = 2
MASKED_PHONE_PREFIX = "*" * 8
UVICORN_LOGGER_NAMES = ("uvicorn", "uvicorn.error")
# Replaced by the request-completed event, which logs the path without the query string.
UVICORN_ACCESS_LOGGER_NAME = "uvicorn.access"
# httpx logs every request's full URL at INFO, query string included, and a gateway query may
# carry a merchant identifier. The resilient client logs host and path events instead.
HTTP_CLIENT_LOGGER_NAMES = ("httpx", "httpcore")

# Key words whose values are never logged (security-and-compliance.md section 3).
SENSITIVE_KEY_WORDS = (
    r"token|secret|signature|password|passwd|otp|checksum|api[_-]?key|authorization"
    r"|cookie|credential|merchant[_-]?key"
)
SENSITIVE_FIELD_NAME_PATTERN = re.compile(rf"(?i){SENSITIVE_KEY_WORDS}")
BEARER_TOKEN_PATTERN = re.compile(r"(?i)\b(bearer|basic)\s+[A-Za-z0-9._~+/=-]+")
SENSITIVE_KEY_VALUE_PATTERN = re.compile(
    rf"(?i)(?P<key>[\"']?[A-Za-z0-9_-]*(?:{SENSITIVE_KEY_WORDS})[A-Za-z0-9_-]*[\"']?\s*[:=]\s*)"
    r"(?P<value>\"[^\"]*\"|'[^']*'|(?:(?:bearer|basic)\s+)?[^\s\"',;&}]+)"
)
# Indian mobile numbers with an optional +91, 91 or 0 prefix and optional separators.
PHONE_NUMBER_PATTERN = re.compile(r"(?<![\w+])(?:\+?91[\s-]?|0)?[6-9]\d{4}[\s-]?\d{5}(?!\w)")

# Record attributes that are not caller extras; color_message is uvicorn's ANSI copy of message.
STANDARD_LOG_RECORD_ATTRIBUTES = frozenset(
    {
        *logging.LogRecord("", 0, "", 0, "", None, None).__dict__,
        "message",
        "asctime",
        "color_message",
    }
)


def mask_phone_number(phone_number_match: re.Match[str]) -> str:
    """Replaces a matched phone number with a fixed mask that keeps only the last two digits."""
    digits = re.sub(r"\D", "", phone_number_match.group(0))
    return MASKED_PHONE_PREFIX + digits[-VISIBLE_PHONE_DIGIT_COUNT:]


def redact_sensitive_text(text: str) -> str:
    """Masks bearer tokens, secret-looking key/value pairs and phone numbers inside free text."""
    redacted_text = BEARER_TOKEN_PATTERN.sub(rf"\1 {REDACTED_VALUE}", text)
    redacted_text = SENSITIVE_KEY_VALUE_PATTERN.sub(rf"\g<key>{REDACTED_VALUE}", redacted_text)
    return PHONE_NUMBER_PATTERN.sub(mask_phone_number, redacted_text)


def extract_extra_fields(record: logging.LogRecord) -> dict[str, object]:
    """Returns the fields a caller attached with `extra=`, excluding standard record attributes."""
    return {
        field_name: field_value
        for field_name, field_value in record.__dict__.items()
        if field_name not in STANDARD_LOG_RECORD_ATTRIBUTES
    }


class SensitiveDataRedactionFilter(logging.Filter):
    """Handler filter that rewrites every record so no token, secret or full phone number leaves."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Redacts the rendered message, extra fields and exception text in place; never drops."""
        record.msg = redact_sensitive_text(record.getMessage())
        record.args = None
        for field_name, field_value in extract_extra_fields(record).items():
            if SENSITIVE_FIELD_NAME_PATTERN.search(field_name):
                setattr(record, field_name, REDACTED_VALUE)
            elif isinstance(field_value, str):
                setattr(record, field_name, redact_sensitive_text(field_value))
        if record.exc_info and not record.exc_text:
            record.exc_text = logging.Formatter().formatException(record.exc_info)
        if record.exc_text:
            record.exc_text = redact_sensitive_text(record.exc_text)
        return True


class JsonLogFormatter(logging.Formatter):
    """Formats each record as one JSON object that always carries the correlation ID."""

    def format(self, record: logging.LogRecord) -> str:
        """Renders the record as JSON; correlation_id is null outside an HTTP request."""
        log_line: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": get_current_correlation_id(),
            **extract_extra_fields(record),
        }
        if record.exc_info and not record.exc_text:
            record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            log_line["exception"] = record.exc_text
        return json.dumps(log_line, default=str, ensure_ascii=False)


def build_json_log_handler() -> logging.Handler:
    """Creates the stdout handler that redacts and formats every record as JSON."""
    handler = logging.StreamHandler(sys.stdout)
    handler.set_name(JSON_HANDLER_NAME)
    handler.addFilter(SensitiveDataRedactionFilter())
    handler.setFormatter(JsonLogFormatter())
    return handler


def configure_logging(log_level: str) -> None:
    """Installs the JSON handler on the root logger once and routes uvicorn's logs through it."""
    root_logger = logging.getLogger()
    for existing_handler in list(root_logger.handlers):
        if existing_handler.get_name() == JSON_HANDLER_NAME:
            root_logger.removeHandler(existing_handler)
    root_logger.addHandler(build_json_log_handler())
    root_logger.setLevel(log_level)
    for uvicorn_logger_name in UVICORN_LOGGER_NAMES:
        uvicorn_logger = logging.getLogger(uvicorn_logger_name)
        uvicorn_logger.handlers.clear()
        uvicorn_logger.propagate = True
    uvicorn_access_logger = logging.getLogger(UVICORN_ACCESS_LOGGER_NAME)
    uvicorn_access_logger.handlers.clear()
    uvicorn_access_logger.propagate = False
    for http_client_logger_name in HTTP_CLIENT_LOGGER_NAMES:
        logging.getLogger(http_client_logger_name).setLevel(logging.WARNING)
