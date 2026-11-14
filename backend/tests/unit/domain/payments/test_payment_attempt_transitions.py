"""Tests for the transition table: how a gateway report moves a payment attempt."""

import itertools

import pytest

from emi_copilot.domain.payments import (
    GatewayPaymentStatus,
    PaymentAttemptStatus,
    find_status_after_gateway_report,
)

Attempt = PaymentAttemptStatus
Reported = GatewayPaymentStatus

EXPECTED_STATUS_CHANGES = {
    (Attempt.LINK_CREATED, Reported.PENDING): Attempt.PAYMENT_PENDING,
    (Attempt.LINK_CREATED, Reported.PAID): Attempt.PAID,
    (Attempt.LINK_CREATED, Reported.FAILED): Attempt.PAYMENT_FAILED,
    (Attempt.OUTCOME_UNKNOWN, Reported.PENDING): Attempt.PAYMENT_PENDING,
    (Attempt.OUTCOME_UNKNOWN, Reported.PAID): Attempt.PAID,
    (Attempt.OUTCOME_UNKNOWN, Reported.FAILED): Attempt.PAYMENT_FAILED,
    (Attempt.PAYMENT_PENDING, Reported.PAID): Attempt.PAID,
    (Attempt.PAYMENT_PENDING, Reported.FAILED): Attempt.PAYMENT_FAILED,
    (Attempt.PAYMENT_FAILED, Reported.PAID): Attempt.PAID,
}


@pytest.mark.parametrize(
    ("current_status", "reported_status"),
    list(itertools.product(PaymentAttemptStatus, GatewayPaymentStatus)),
)
def test_find_status_after_gateway_report_matches_the_documented_table(
    current_status: PaymentAttemptStatus, reported_status: GatewayPaymentStatus
) -> None:
    """Every one of the 28 pairs either is a listed change or leaves the status as it is."""
    expected_status = EXPECTED_STATUS_CHANGES.get((current_status, reported_status), current_status)
    assert find_status_after_gateway_report(current_status, reported_status) is expected_status


@pytest.mark.parametrize("reported_status", list(GatewayPaymentStatus))
def test_find_status_after_gateway_report_never_moves_a_paid_attempt(
    reported_status: GatewayPaymentStatus,
) -> None:
    """PAID is final: a late PENDING, a FAILED or a NOT_FOUND never downgrades it."""
    assert find_status_after_gateway_report(Attempt.PAID, reported_status) is Attempt.PAID


@pytest.mark.parametrize("current_status", list(PaymentAttemptStatus))
def test_find_status_after_gateway_report_not_found_changes_nothing(
    current_status: PaymentAttemptStatus,
) -> None:
    """A gateway that does not know the order tells us nothing new."""
    assert find_status_after_gateway_report(current_status, Reported.NOT_FOUND) is current_status


@pytest.mark.parametrize(
    "current_status", [Attempt.LINK_CREATION_IN_PROGRESS, Attempt.LINK_CREATION_FAILED]
)
@pytest.mark.parametrize("reported_status", list(GatewayPaymentStatus))
def test_find_status_after_gateway_report_ignores_attempts_without_a_handed_out_link(
    current_status: PaymentAttemptStatus, reported_status: GatewayPaymentStatus
) -> None:
    """No link was given to the customer, and the create call owns an in-progress attempt."""
    assert find_status_after_gateway_report(current_status, reported_status) is current_status
