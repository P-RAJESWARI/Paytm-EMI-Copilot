"""Translates failed Paytm calls and Paytm failure codes into typed domain errors.

Raw vendor messages never leave the adapter: only Paytm's result code is logged, and every error
carries our own English detail and, for a refusal, a stable PaymentGatewayRejectionReason.
"""

import logging
from enum import StrEnum

from emi_copilot.adapters.payment_gateway.paytm_api_definitions import (
    LINK_FAILURE_RESULT_STATUS,
    LINK_OUTCOME_UNKNOWN_RESULT_CODES,
    LINK_REJECTION_REASONS_BY_RESULT_CODE,
    LINK_SUCCESS_RESULT_STATUS,
    SUBVENTION_FAILURE_RESULT_STATUS,
    SUBVENTION_SUCCESS_RESULT_STATUS,
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

paytm_error_translator_logger = logging.getLogger(__name__)


class PaytmCallKind(StrEnum):
    """Whether a failed call may be repeated safely, which decides what its failure means."""

    IDEMPOTENT_READ = "idempotent_read"
    """Banks, Tenures and transaction status: reading twice changes nothing."""

    PAYMENT_LINK_CREATION = "payment_link_creation"
    """Create Link: sent once; a failure after sending leaves the outcome unknown (ADR 0005)."""


def _build_outcome_unknown_error() -> PaymentGatewayTimeoutError:
    """Builds the error for a create-link call that may have made a link (ADR 0010 section 3)."""
    return PaymentGatewayTimeoutError(
        "The payment link call failed after it may have reached the gateway; outcome unknown."
    )


def _build_not_sent_error() -> PaymentGatewayUnavailableError:
    """Builds the error for a call that provably never reached the gateway."""
    return PaymentGatewayUnavailableError(
        "The gateway could not be reached or its circuit is open; nothing was sent."
    )


# Pattern: Adapter (error side). One table-driven place turns transport failures and vendor
# result codes into domain errors, so services never see an HTTP status or a Paytm code.
class PaytmErrorTranslator:
    """Maps core upstream errors, unexpected HTTP answers and Paytm codes to domain errors."""

    def translate_upstream_error(
        self, error: UpstreamCallError, call_kind: PaytmCallKind
    ) -> PaymentGatewayError:
        """Turns a failed call into Timeout or Unavailable, by whether it may have taken effect.

        Reads: a timeout is a timeout, anything else unavailable. Create Link (ADR 0010 section
        3): any 5xx answer or failure after sending is outcome-unknown; a connect failure or an
        open circuit means nothing was sent.
        """
        if call_kind is PaytmCallKind.IDEMPOTENT_READ:
            if isinstance(error, UpstreamTimeoutError):
                return PaymentGatewayTimeoutError("The gateway did not answer in time.")
            return PaymentGatewayUnavailableError("The gateway could not serve the call.")
        if isinstance(error, CircuitOpenError):
            return _build_not_sent_error()
        has_answered_with_server_error = (
            isinstance(error, UpstreamUnavailableError) and error.status_code is not None
        )
        if has_answered_with_server_error or error.is_outcome_unknown:
            return _build_outcome_unknown_error()
        return _build_not_sent_error()

    def translate_unexpected_http_status(
        self, status_code: int, api_name: str
    ) -> PaymentGatewayRequestRejectedError:
        """Turns an answer below 500 that is not 2xx into a refusal; only the status is logged."""
        paytm_error_translator_logger.warning(
            "paytm answered with an unexpected http status",
            extra={"paytm_api": api_name, "http_status_code": status_code},
        )
        return PaymentGatewayRequestRejectedError(
            PaymentGatewayRejectionReason.INVALID_REQUEST,
            "The gateway refused the request at the HTTP level.",
        )

    def require_subvention_success(self, result_info: PaytmResultInfo, api_name: str) -> None:
        """Passes on "S"; raises a refusal on "F" and a malformed-reply error on anything else.

        No Banks or Tenures failure code is documented, so every "F" is INVALID_REQUEST [Verify].
        """
        if result_info.result_status == SUBVENTION_SUCCESS_RESULT_STATUS:
            return
        if result_info.result_status != SUBVENTION_FAILURE_RESULT_STATUS:
            raise InvalidPaymentGatewayValueError("The reply status is not a documented value.")
        self._log_refusal(api_name, result_info.result_code)
        raise PaymentGatewayRequestRejectedError(
            PaymentGatewayRejectionReason.INVALID_REQUEST,
            "The gateway refused the EMI offer query.",
        )

    def require_link_creation_success(self, result_info: PaytmResultInfo, api_name: str) -> None:
        """Passes on SUCCESS; on FAILED raises a refusal, or outcome-unknown for codes 501/502.

        An undocumented failure code is still a refusal, as INVALID_REQUEST, logged by code.
        """
        if result_info.result_status == LINK_SUCCESS_RESULT_STATUS:
            return
        if result_info.result_status != LINK_FAILURE_RESULT_STATUS:
            raise InvalidPaymentGatewayValueError("The reply status is not a documented value.")
        self._log_refusal(api_name, result_info.result_code)
        if result_info.result_code in LINK_OUTCOME_UNKNOWN_RESULT_CODES:
            raise _build_outcome_unknown_error()
        raise PaymentGatewayRequestRejectedError(
            LINK_REJECTION_REASONS_BY_RESULT_CODE.get(
                result_info.result_code, PaymentGatewayRejectionReason.INVALID_REQUEST
            ),
            "The gateway refused to create the payment link.",
        )

    def _log_refusal(self, api_name: str, result_code: str) -> None:
        """Logs one event with the API and Paytm's result code; never the vendor's message."""
        paytm_error_translator_logger.warning(
            "paytm reported a failure",
            extra={"paytm_api": api_name, "paytm_result_code": result_code},
        )
