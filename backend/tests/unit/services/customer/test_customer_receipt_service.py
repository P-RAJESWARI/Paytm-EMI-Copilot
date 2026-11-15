"""CustomerReceiptService: C10 from the consent evidence and the payment's state, in plain terms."""

from dataclasses import replace

import pytest

from emi_copilot.domain.customer_sessions import CustomerLanguage
from emi_copilot.domain.errors import (
    ConsentNotGivenError,
    InvalidSaleDataError,
    PaymentLinkFailureCode,
)
from emi_copilot.domain.payments import PaymentAttemptStatus
from emi_copilot.domain.sales import SaleStatus
from emi_copilot.services.customer.consent_types import CoolingOffNoticeStatus, ReceiptStatus
from emi_copilot.services.customer.customer_receipt_service import describe_receipt_status
from emi_copilot.services.customer.customer_session_types import CustomerSessionCredentials
from tests.payment_builders import build_payment_attempt
from tests.sale_builders import SALE_ID, build_sale
from tests.unit.services.conftest import ServiceTestKit
from tests.unit.services.customer.customer_service_wiring import (
    CustomerServices,
    build_plan_a_consent_command,
    credentials_of,
    prepare_for_consent,
    sign_qr_token,
    store_design_shop,
    wire_customer_services,
)


@pytest.fixture
def services(kit: ServiceTestKit) -> CustomerServices:
    """Stores the design shop and its CHOOSING sale, then wires the customer services."""
    store_design_shop(kit)
    return wire_customer_services(kit)


@pytest.fixture
def credentials(services: CustomerServices) -> CustomerSessionCredentials:
    """Exchanges the QR and gets the customer ready to consent."""
    credentials = credentials_of(services.sessions.start(sign_qr_token(services.qr_token_signer)))
    prepare_for_consent(services, credentials)
    return credentials


def test_get_receipt_before_consent_is_refused(
    services: CustomerServices, credentials: CustomerSessionCredentials
) -> None:
    """There is no receipt until the plan is agreed."""
    with pytest.raises(ConsentNotGivenError):
        services.receipt.get_receipt(credentials)


def test_get_receipt_after_consent_is_the_hand_off_with_the_evidence(
    services: CustomerServices, credentials: CustomerSessionCredentials
) -> None:
    """READY_TO_PAY in the consent's language, reference, phone ending and placeholder note."""
    record = services.consent.give_consent(
        credentials, build_plan_a_consent_command(language=CustomerLanguage.TAMIL)
    )
    receipt = services.receipt.get_receipt(credentials)
    assert receipt.status is ReceiptStatus.READY_TO_PAY
    assert receipt.consent_record == record
    assert receipt.consent_record.evidence.language is CustomerLanguage.TAMIL
    assert receipt.cooling_off_notice_status is CoolingOffNoticeStatus.PLACEHOLDER


RECEIPT_CASES = [
    (SaleStatus.READY_TO_PAY, None, ReceiptStatus.READY_TO_PAY),
    (
        SaleStatus.READY_TO_PAY,
        PaymentAttemptStatus.LINK_CREATION_IN_PROGRESS,
        ReceiptStatus.PAYMENT_PENDING,
    ),
    (SaleStatus.READY_TO_PAY, PaymentAttemptStatus.LINK_CREATED, ReceiptStatus.PAYMENT_PENDING),
    (SaleStatus.READY_TO_PAY, PaymentAttemptStatus.OUTCOME_UNKNOWN, ReceiptStatus.PAYMENT_PENDING),
    (SaleStatus.READY_TO_PAY, PaymentAttemptStatus.PAYMENT_FAILED, ReceiptStatus.READY_TO_PAY),
    (
        SaleStatus.READY_TO_PAY,
        PaymentAttemptStatus.LINK_CREATION_FAILED,
        ReceiptStatus.READY_TO_PAY,
    ),
    (SaleStatus.PAID, PaymentAttemptStatus.PAID, ReceiptStatus.PAID),
    (
        SaleStatus.PAYMENT_NOT_COMPLETED,
        PaymentAttemptStatus.PAYMENT_FAILED,
        ReceiptStatus.PAYMENT_NOT_COMPLETED,
    ),
]
"""(sale status, latest attempt status or None, receipt status)."""


@pytest.mark.parametrize("receipt_case", RECEIPT_CASES)
def test_get_receipt_follows_the_sale_and_its_latest_payment_attempt(
    services: CustomerServices,
    kit: ServiceTestKit,
    credentials: CustomerSessionCredentials,
    receipt_case: tuple[SaleStatus, PaymentAttemptStatus | None, ReceiptStatus],
) -> None:
    """A payment the merchant started is pending; a retry after a failed one is open again."""
    sale_status, attempt_status, expected_status = receipt_case
    services.consent.give_consent(credentials, build_plan_a_consent_command())
    agreed_sale = kit.database.sales_by_id[SALE_ID]
    kit.database.sales_by_id[SALE_ID] = replace(agreed_sale, status=sale_status)
    if attempt_status is not None:
        failure_code = (
            PaymentLinkFailureCode.GATEWAY_UNAVAILABLE
            if attempt_status is PaymentAttemptStatus.LINK_CREATION_FAILED
            else None
        )
        kit.store_attempt(
            build_payment_attempt(
                1, status=attempt_status, sale_id=SALE_ID, failure_code=failure_code
            )
        )
    assert services.receipt.get_receipt(credentials).status is expected_status


@pytest.mark.parametrize("sale_status", [SaleStatus.CHOOSING, SaleStatus.EXPIRED])
def test_describe_receipt_status_of_a_sale_never_agreed_is_inconsistent_data(
    sale_status: SaleStatus,
) -> None:
    """A sale with consent evidence is always past CHOOSING; anything else is reported."""
    with pytest.raises(InvalidSaleDataError):
        describe_receipt_status(build_sale(status=sale_status), None)
