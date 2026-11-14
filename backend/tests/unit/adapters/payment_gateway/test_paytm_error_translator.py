"""PaytmErrorTranslator: every core error and documented code, for reads and for Create Link."""

import logging

import pytest

from emi_copilot.adapters.payment_gateway.paytm_error_translator import (
    PaytmCallKind,
    PaytmErrorTranslator,
)
from emi_copilot.adapters.payment_gateway.paytm_response_values import PaytmResultInfo
from emi_copilot.core.upstream_errors import (
    CircuitOpenError,
    UpstreamCallError,
    UpstreamTimeoutError,
    UpstreamUnavailableError,
)
from emi_copilot.domain.errors import (
    InvalidPaymentGatewayValueError,
    PaymentGatewayError,
    PaymentGatewayRejectionReason,
    PaymentGatewayRequestRejectedError,
    PaymentGatewayTimeoutError,
    PaymentGatewayUnavailableError,
)

DEPENDENCY = "paytm"
READ = PaytmCallKind.IDEMPOTENT_READ
CREATE = PaytmCallKind.PAYMENT_LINK_CREATION
INVALID_REQUEST = PaymentGatewayRejectionReason.INVALID_REQUEST
NOT_PERMITTED = PaymentGatewayRejectionReason.OPERATION_NOT_PERMITTED

READ_TIMEOUT = UpstreamTimeoutError(DEPENDENCY, "read timeout", is_outcome_unknown=True)
CONNECT_FAILURE = UpstreamTimeoutError(DEPENDENCY, "connect failed", is_outcome_unknown=False)
SERVER_ERROR_503 = UpstreamUnavailableError(
    DEPENDENCY, "503", is_outcome_unknown=False, status_code=503
)
SERVER_ERROR_500 = UpstreamUnavailableError(
    DEPENDENCY, "500", is_outcome_unknown=False, status_code=500
)
DROPPED_AFTER_SENDING = UpstreamUnavailableError(
    DEPENDENCY, "dropped", is_outcome_unknown=True, status_code=None
)
BROKEN_BEFORE_SENDING = UpstreamUnavailableError(
    DEPENDENCY, "broken", is_outcome_unknown=False, status_code=None
)
CIRCUIT_OPEN = CircuitOpenError(DEPENDENCY)


@pytest.fixture
def translator() -> PaytmErrorTranslator:
    """Gives the translator under test."""
    return PaytmErrorTranslator()


@pytest.mark.parametrize(
    ("upstream_error", "call_kind", "expected_error_type"),
    [
        (READ_TIMEOUT, READ, PaymentGatewayTimeoutError),
        (CONNECT_FAILURE, READ, PaymentGatewayTimeoutError),
        (SERVER_ERROR_503, READ, PaymentGatewayUnavailableError),
        (DROPPED_AFTER_SENDING, READ, PaymentGatewayUnavailableError),
        (CIRCUIT_OPEN, READ, PaymentGatewayUnavailableError),
        (READ_TIMEOUT, CREATE, PaymentGatewayTimeoutError),
        (SERVER_ERROR_503, CREATE, PaymentGatewayTimeoutError),
        (SERVER_ERROR_500, CREATE, PaymentGatewayTimeoutError),
        (DROPPED_AFTER_SENDING, CREATE, PaymentGatewayTimeoutError),
        (CONNECT_FAILURE, CREATE, PaymentGatewayUnavailableError),
        (BROKEN_BEFORE_SENDING, CREATE, PaymentGatewayUnavailableError),
        (CIRCUIT_OPEN, CREATE, PaymentGatewayUnavailableError),
    ],
    ids=[
        "read-timeout",
        "read-connect-failure",
        "read-5xx",
        "read-dropped",
        "read-circuit-open",
        "create-read-timeout-outcome-unknown",
        "create-503-outcome-unknown",
        "create-500-outcome-unknown",
        "create-dropped-after-sending-outcome-unknown",
        "create-connect-failure-not-sent",
        "create-broken-before-sending-not-sent",
        "create-circuit-open-not-sent",
    ],
)
def test_translate_upstream_error_follows_adr_0010_for_create_and_type_for_reads(
    translator: PaytmErrorTranslator,
    upstream_error: UpstreamCallError,
    call_kind: PaytmCallKind,
    expected_error_type: type[PaymentGatewayError],
) -> None:
    """Create Link: possibly-sent is Timeout (outcome unknown), never-sent is Unavailable."""
    translated_error = translator.translate_upstream_error(upstream_error, call_kind)
    assert type(translated_error) is expected_error_type
    assert DEPENDENCY not in translated_error.detail


@pytest.mark.parametrize(
    ("result_code", "expected_reason"),
    [
        ("100", NOT_PERMITTED),
        ("404", INVALID_REQUEST),
        ("5004", INVALID_REQUEST),
        ("5008", INVALID_REQUEST),
        ("5009", INVALID_REQUEST),
        ("5021", INVALID_REQUEST),
        ("5027", INVALID_REQUEST),
        ("5028", INVALID_REQUEST),
        ("5023", NOT_PERMITTED),
        ("5025", NOT_PERMITTED),
        ("9999", INVALID_REQUEST),
        ("", INVALID_REQUEST),
    ],
)
def test_require_link_creation_success_maps_each_documented_refusal_code(
    translator: PaytmErrorTranslator,
    result_code: str,
    expected_reason: PaymentGatewayRejectionReason,
) -> None:
    """Every documented Create Link failure code is a refusal with our stable reason."""
    with pytest.raises(PaymentGatewayRequestRejectedError) as raised:
        translator.require_link_creation_success(
            PaytmResultInfo("FAILED", result_code), "create_link"
        )
    assert raised.value.reason is expected_reason


@pytest.mark.parametrize("result_code", ["501", "502"])
def test_require_link_creation_success_treats_paytm_internal_errors_as_outcome_unknown(
    translator: PaytmErrorTranslator, result_code: str
) -> None:
    """Paytm's internal (501) and unknown (502) errors may hide a made link: Timeout."""
    with pytest.raises(PaymentGatewayTimeoutError):
        translator.require_link_creation_success(
            PaytmResultInfo("FAILED", result_code), "create_link"
        )


def test_require_link_creation_success_passes_on_success_and_refuses_unknown_status(
    translator: PaytmErrorTranslator,
) -> None:
    """SUCCESS passes; a status word Paytm does not document is a malformed reply."""
    translator.require_link_creation_success(PaytmResultInfo("SUCCESS", "200"), "create_link")
    with pytest.raises(InvalidPaymentGatewayValueError):
        translator.require_link_creation_success(PaytmResultInfo("OK", "200"), "create_link")


def test_require_subvention_success_passes_s_refuses_f_and_rejects_others(
    translator: PaytmErrorTranslator,
) -> None:
    """Banks and Tenures: "S" passes, "F" is INVALID_REQUEST, anything else is malformed."""
    translator.require_subvention_success(PaytmResultInfo("S", ""), "banks")
    with pytest.raises(PaymentGatewayRequestRejectedError) as raised:
        translator.require_subvention_success(PaytmResultInfo("F", "SYNTHETIC"), "tenures")
    assert raised.value.reason is INVALID_REQUEST
    with pytest.raises(InvalidPaymentGatewayValueError):
        translator.require_subvention_success(PaytmResultInfo("SUCCESS", ""), "banks")


@pytest.mark.parametrize("status_code", [400, 401, 404, 429, 302])
def test_translate_unexpected_http_status_is_a_refusal_logged_by_status_only(
    translator: PaytmErrorTranslator, status_code: int, caplog: pytest.LogCaptureFixture
) -> None:
    """An answer below 500 that is not 2xx is a refusal; only the API and status are logged."""
    with caplog.at_level(logging.WARNING):
        translated_error = translator.translate_unexpected_http_status(status_code, "banks")
    assert translated_error.reason is INVALID_REQUEST
    (record,) = caplog.records
    assert record.__dict__["http_status_code"] == status_code
    assert record.__dict__["paytm_api"] == "banks"


def test_refusals_log_the_result_code_and_never_a_vendor_message(
    translator: PaytmErrorTranslator, caplog: pytest.LogCaptureFixture
) -> None:
    """The log event carries the API and Paytm's code; the error detail is our own text."""
    with (
        caplog.at_level(logging.WARNING),
        pytest.raises(PaymentGatewayRequestRejectedError) as raised,
    ):
        translator.require_link_creation_success(PaytmResultInfo("FAILED", "5028"), "create_link")
    (record,) = caplog.records
    assert record.__dict__["paytm_result_code"] == "5028"
    assert record.__dict__["paytm_api"] == "create_link"
    assert raised.value.detail == "The gateway refused to create the payment link."
