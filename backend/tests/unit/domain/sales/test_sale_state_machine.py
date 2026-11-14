"""SaleStateMachine: strict commands, tolerant payment reports, PAID final, every pair checked."""

import itertools

import pytest
from hypothesis import given
from hypothesis import strategies as st

from emi_copilot.domain.errors import IllegalSaleTransitionError
from emi_copilot.domain.sales import (
    PaymentOutcomeEffect,
    SaleCommand,
    SalePaymentOutcome,
    SaleStateMachine,
    SaleStatus,
)

Status = SaleStatus
EXPECTED_COMMAND_MOVES = {
    (Status.CHOOSING, SaleCommand.AGREE_TO_PLAN): Status.READY_TO_PAY,
    (Status.CHOOSING, SaleCommand.ISSUE_QR_CODE): Status.CHOOSING,
    (Status.CHOOSING, SaleCommand.EXPIRE): Status.EXPIRED,
    (Status.PAYMENT_NOT_COMPLETED, SaleCommand.RETRY_PAYMENT): Status.READY_TO_PAY,
}
EXPECTED_PAYMENT_MOVES = {
    (Status.READY_TO_PAY, SalePaymentOutcome.PAID): Status.PAID,
    (Status.READY_TO_PAY, SalePaymentOutcome.NOT_COMPLETED): Status.PAYMENT_NOT_COMPLETED,
    (Status.PAYMENT_NOT_COMPLETED, SalePaymentOutcome.PAID): Status.PAID,
}
STATE_MACHINE = SaleStateMachine()


def test_sale_status_has_exactly_the_five_merchant_visible_values() -> None:
    """Rule 6: the merchant sees these five statuses and nothing that reveals customer steps."""
    assert [status.value for status in SaleStatus] == [
        "CHOOSING",
        "READY_TO_PAY",
        "PAID",
        "PAYMENT_NOT_COMPLETED",
        "EXPIRED",
    ]


@given(st.sampled_from(SaleStatus), st.sampled_from(SaleCommand))
def test_status_after_command_allows_only_the_documented_moves(
    current_status: SaleStatus, command: SaleCommand
) -> None:
    """Every listed (status, command) pair moves as documented; every other pair raises."""
    expected_status = EXPECTED_COMMAND_MOVES.get((current_status, command))
    if expected_status is None:
        with pytest.raises(IllegalSaleTransitionError) as raised_error:
            STATE_MACHINE.status_after_command(current_status, command)
        assert raised_error.value.code == "SALE_STATE_CONFLICT"
    else:
        assert STATE_MACHINE.status_after_command(current_status, command) is expected_status


@given(st.sampled_from(SaleStatus), st.sampled_from(SalePaymentOutcome))
def test_decide_payment_outcome_never_raises_and_moves_only_as_documented(
    current_status: SaleStatus, outcome: SalePaymentOutcome
) -> None:
    """A report either moves the sale as listed or leaves its status exactly as it was."""
    decision = STATE_MACHINE.decide_payment_outcome(current_status, outcome)
    expected_status = EXPECTED_PAYMENT_MOVES.get((current_status, outcome), current_status)
    assert decision.status is expected_status
    assert (decision.effect is PaymentOutcomeEffect.STATUS_CHANGED) == (
        (current_status, outcome) in EXPECTED_PAYMENT_MOVES
    )


@pytest.mark.parametrize(
    ("command", "outcome"), list(itertools.product(SaleCommand, SalePaymentOutcome))
)
def test_paid_is_final_for_every_command_and_report(
    command: SaleCommand, outcome: SalePaymentOutcome
) -> None:
    """No command moves a paid sale, and a repeated or late report is no change, not an error."""
    with pytest.raises(IllegalSaleTransitionError):
        STATE_MACHINE.status_after_command(Status.PAID, command)
    decision = STATE_MACHINE.decide_payment_outcome(Status.PAID, outcome)
    assert (decision.status, decision.effect) == (Status.PAID, PaymentOutcomeEffect.NO_CHANGE)


@pytest.mark.parametrize(
    ("current_status", "outcome"),
    list(itertools.product([Status.CHOOSING, Status.EXPIRED], SalePaymentOutcome)),
)
def test_payment_report_on_a_sale_not_awaiting_payment_is_ignored(
    current_status: SaleStatus, outcome: SalePaymentOutcome
) -> None:
    """No plan was agreed, so the report is ignored (and audited by the subscriber)."""
    decision = STATE_MACHINE.decide_payment_outcome(current_status, outcome)
    assert decision.status is current_status
    assert decision.effect is PaymentOutcomeEffect.IGNORED_NOT_AWAITING_PAYMENT


def test_repeated_not_completed_report_is_no_change() -> None:
    """A second failure report about a payment that already did not go through changes nothing."""
    decision = STATE_MACHINE.decide_payment_outcome(
        Status.PAYMENT_NOT_COMPLETED, SalePaymentOutcome.NOT_COMPLETED
    )
    assert (decision.status, decision.effect) == (
        Status.PAYMENT_NOT_COMPLETED,
        PaymentOutcomeEffect.NO_CHANGE,
    )
