"""The domain-error mapping table is complete and problem bodies follow RFC 7807."""

import json
import logging
from typing import ClassVar

import pytest

from emi_copilot.api.error_handlers import (
    PROBLEM_MAPPINGS_BY_ERROR_TYPE,
    describe_field_location,
    find_problem_mapping,
    handle_domain_error,
)
from emi_copilot.domain import errors
from emi_copilot.dtos.problem_details_dto import build_problem_type_url


def list_every_domain_error_class() -> list[type[errors.DomainError]]:
    """Lists DomainError and every subclass, however deep, defined in domain/errors.py."""
    found_classes: list[type[errors.DomainError]] = [errors.DomainError]
    for error_class in found_classes:
        found_classes.extend(error_class.__subclasses__())
    return [
        error_class
        for error_class in found_classes
        if error_class.__module__ == errors.DomainError.__module__
    ]


def test_every_domain_error_class_has_an_explicit_problem_mapping() -> None:
    """A new domain error fails this test until someone decides its HTTP status."""
    assert set(list_every_domain_error_class()) == set(PROBLEM_MAPPINGS_BY_ERROR_TYPE)


@pytest.mark.parametrize(
    ("error_class", "expected_status"),
    [
        (errors.OfferNotFoundError, 404),
        (errors.PaymentAttemptNotFoundError, 404),
        (errors.IdempotencyKeyReusedError, 422),
        (errors.PaymentLinkOutcomeUnknownError, 409),
        (errors.PaymentLinkCreationFailedError, 409),
        (errors.PaymentLinkCreationInProgressError, 409),
        (errors.WebhookSignatureInvalidError, 401),
        (errors.PaymentGatewayTimeoutError, 504),
        (errors.PaymentGatewayUnavailableError, 502),
        (errors.PaymentGatewayRequestRejectedError, 502),
        (errors.InvalidPaymentGatewayValueError, 502),
        (errors.PaymentGatewayError, 502),
        (errors.InvalidMoneyAmountError, 422),
        (errors.InvalidPairingCredentialsError, 401),
        (errors.MerchantAuthenticationRequiredError, 401),
        (errors.PairingTemporarilyLockedError, 429),
        (errors.RequestRateLimitedError, 429),
        (errors.RetryLaterError, 429),
        (errors.ProductNotFoundError, 404),
        (errors.InvalidMerchantDataError, 422),
        (errors.SaleNotFoundError, 404),
        (errors.IllegalSaleTransitionError, 409),
        (errors.SessionCodesExhaustedError, 409),
        (errors.ChosenPlanNoLongerOfferedError, 409),
        (errors.PaymentLinkAlreadyActiveError, 409),
        (errors.InvalidReportingPeriodError, 422),
        (errors.InvalidReportDataError, 422),
        (errors.InvalidSaleDataError, 422),
        (errors.InvalidComfortInputError, 422),
        (errors.InvalidMonthlyBudgetError, 422),
        (errors.DomainError, 422),
    ],
)
def test_problem_mapping_gives_the_documented_status(
    error_class: type[errors.DomainError], expected_status: int
) -> None:
    """Each row of the mapping table in error_handlers.py holds."""
    assert PROBLEM_MAPPINGS_BY_ERROR_TYPE[error_class].status == expected_status


def test_find_problem_mapping_for_unlisted_subclass_uses_nearest_ancestor() -> None:
    """A subclass defined elsewhere inherits its parent's answer rather than failing."""

    class LocalGatewayTimeoutError(errors.PaymentGatewayTimeoutError):
        """A subclass the table does not list."""

        code: ClassVar[str] = "LOCAL_TIMEOUT"

    assert find_problem_mapping(LocalGatewayTimeoutError("late")).status == 504


def test_handle_domain_error_renders_problem_json_with_kebab_type_and_detail() -> None:
    """The body carries type, title, status, detail and code, and no fieldErrors."""
    response = handle_domain_error(None, errors.OfferNotFoundError("Not quoted."))  # type: ignore[arg-type]
    assert response.status_code == 404
    assert response.media_type == "application/problem+json"
    assert json.loads(bytes(response.body)) == {
        "type": "https://emicopilot.example/problems/offer-not-found",
        "title": "Offer not found",
        "status": 404,
        "detail": "Not quoted.",
        "code": "OFFER_NOT_FOUND",
        "correlationId": None,
    }


def test_build_problem_type_url_turns_code_into_kebab_case() -> None:
    """Codes become lowercase, hyphenated path segments."""
    assert build_problem_type_url("PAYMENT_LINK_OUTCOME_UNKNOWN") == (
        "https://emicopilot.example/problems/payment-link-outcome-unknown"
    )


@pytest.mark.parametrize(
    ("location", "expected_field"),
    [
        (("body", "offerId"), "offerId"),
        (("query", "priceInPaise"), "priceInPaise"),
        (("header", "Idempotency-Key"), "Idempotency-Key"),
        (("body", "offer", 0, "tenureInMonths"), "offer.0.tenureInMonths"),
        (("body",), "body"),
    ],
)
def test_describe_field_location_names_fields_as_on_the_wire(
    location: tuple[object, ...], expected_field: str
) -> None:
    """The source part of the location is dropped and nested parts are dotted."""
    assert describe_field_location(location) == expected_field


@pytest.mark.parametrize(
    ("error", "expected_level"),
    [
        (errors.WebhookSignatureInvalidError("Forged."), logging.WARNING),
        (errors.OfferNotFoundError("Not quoted."), logging.INFO),
    ],
)
def test_handle_domain_error_logs_refused_credentials_as_a_warning(
    caplog: pytest.LogCaptureFixture, error: errors.DomainError, expected_level: int
) -> None:
    """A 401 is a security event; other refusals are ordinary information."""
    with caplog.at_level(logging.INFO, logger="emi_copilot.api.error_handlers"):
        handle_domain_error(None, error)  # type: ignore[arg-type]
    assert [record.levelno for record in caplog.records] == [expected_level]


@pytest.mark.parametrize(
    ("error", "expected_headers"),
    [
        (errors.PairingTemporarilyLockedError(900, "Locked."), {"retry-after": "900"}),
        (errors.RequestRateLimitedError(42, "Slow down."), {"retry-after": "42"}),
        (errors.MerchantAuthenticationRequiredError("Pair again."), {"www-authenticate": "Bearer"}),
    ],
)
def test_handle_domain_error_adds_retry_after_or_bearer_challenge(
    error: errors.DomainError, expected_headers: dict[str, str]
) -> None:
    """A 429 says when to retry; a merchant 401 names the bearer scheme (RFC 6750)."""
    response = handle_domain_error(None, error)  # type: ignore[arg-type]
    for header_name, header_value in expected_headers.items():
        assert response.headers[header_name] == header_value


@pytest.mark.parametrize(
    "error",
    [
        errors.InvalidPairingCredentialsError("Wrong."),
        errors.OfferNotFoundError("Not quoted."),
    ],
)
def test_handle_domain_error_without_special_headers_adds_neither(
    error: errors.DomainError,
) -> None:
    """A wrong PIN is not a bearer challenge, and ordinary refusals carry no Retry-After."""
    response = handle_domain_error(None, error)  # type: ignore[arg-type]
    assert "retry-after" not in response.headers
    assert "www-authenticate" not in response.headers
