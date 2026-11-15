"""CustomerSessionService: a single-use QR exchange, one answer for every refusal, revocation."""

from dataclasses import replace
from datetime import timedelta

import pytest

from emi_copilot.core.opaque_token import hash_opaque_token
from emi_copilot.core.qr_token_signer import QrTokenSigner, hash_qr_token_nonce
from emi_copilot.domain.customer_sessions import ComfortCheckStatus, CustomerLanguage
from emi_copilot.domain.errors import (
    CustomerQrTokenInvalidError,
    CustomerSessionNotFoundError,
    CustomerSessionTokenInvalidError,
    InvalidSaleDataError,
    ProductNotFoundError,
)
from emi_copilot.domain.money import Money
from emi_copilot.domain.payments import AuditEventType
from emi_copilot.domain.sales import SaleStatus
from emi_copilot.services.customer.customer_session_types import CustomerSessionCredentials
from tests.consent_builders import build_first_consent_record
from tests.fixed_clock import FixedClock
from tests.merchant_builders import MERCHANT_ID
from tests.payment_builders import CREATED_AT
from tests.sale_builders import CHOOSING_LIFETIME, PRODUCT_ID, SALE_ID, build_qr_token_state
from tests.unit.services.conftest import ServiceTestKit
from tests.unit.services.customer.customer_service_wiring import (
    SESSION_LIFETIME,
    CustomerServices,
    credentials_of,
    sign_qr_token,
    store_design_shop,
    wire_customer_services,
)

SECOND_NONCE = "synthetic-qr-nonce-0002"
FORGING_KEY = b"synthetic-key-that-is-not-the-shops-key"  # pragma: allowlist secret


@pytest.fixture
def services(kit: ServiceTestKit) -> CustomerServices:
    """Stores the design shop and its CHOOSING sale, then wires the customer services."""
    store_design_shop(kit)
    return wire_customer_services(kit)


def reissue_qr_token(kit: ServiceTestKit, nonce: str) -> None:
    """Stands in for the merchant's "new QR": the sale now holds another, unexchanged token."""
    sale = kit.database.sales_by_id[SALE_ID]
    kit.database.sales_by_id[SALE_ID] = sale.issue_qr_token(
        build_qr_token_state(nonce_hash=hash_qr_token_nonce(nonce))
    )


def test_start_exchanges_the_qr_for_a_session_that_shows_c1(
    services: CustomerServices, kit: ServiceTestKit
) -> None:
    """C1 gets the shop, the item and its price; the token is returned once, its hash stored."""
    started_session = services.sessions.start(sign_qr_token(services.qr_token_signer))
    assert started_session.session_code == "4821"
    assert started_session.shop_name == "Ravi Electronics"
    assert started_session.product_name == "Example phone, 128 GB"
    assert started_session.price == Money.from_rupees(22000)
    assert started_session.expires_at == CREATED_AT + SESSION_LIFETIME
    stored_session = kit.database.customer_sessions_by_id[started_session.customer_session_id]
    assert stored_session.token_hash == hash_opaque_token(started_session.session_token)
    assert stored_session.sale_id == SALE_ID
    assert "synthetic-session-token" not in repr(started_session)


def test_start_marks_the_qr_exchanged_and_audits_the_new_session(
    services: CustomerServices, kit: ServiceTestKit
) -> None:
    """The sale stays CHOOSING with the exchange moment set; the start is audited by id only."""
    started_session = services.sessions.start(sign_qr_token(services.qr_token_signer))
    stored_sale = kit.database.sales_by_id[SALE_ID]
    assert stored_sale.qr_token.exchanged_at == CREATED_AT
    assert stored_sale.status is SaleStatus.CHOOSING
    assert kit.audit_event_types() == [AuditEventType.CUSTOMER_SESSION_STARTED]
    assert kit.last_audit_event().subject_id == started_session.customer_session_id


def test_start_with_the_same_qr_twice_is_refused_as_an_invalid_qr(
    services: CustomerServices, kit: ServiceTestKit
) -> None:
    """The QR is single-use (ADR 0022 decision 4): a re-scan asks the shop for a new QR."""
    qr_token = sign_qr_token(services.qr_token_signer)
    services.sessions.start(qr_token)
    with pytest.raises(CustomerQrTokenInvalidError):
        services.sessions.start(qr_token)
    assert len(kit.database.customer_sessions_by_id) == 1


@pytest.mark.parametrize(
    "qr_token",
    [
        "not-a-token",
        sign_qr_token(QrTokenSigner(FORGING_KEY, FixedClock(CREATED_AT))),
    ],
    ids=["malformed", "forged"],
)
def test_start_with_a_malformed_or_forged_token_is_refused(
    services: CustomerServices, kit: ServiceTestKit, qr_token: str
) -> None:
    """A token we did not sign opens nothing and changes nothing."""
    with pytest.raises(CustomerQrTokenInvalidError):
        services.sessions.start(qr_token)
    assert kit.database.customer_sessions_by_id == {}


def test_start_with_a_replaced_token_or_an_unknown_sale_gives_the_same_refusal(
    services: CustomerServices,
) -> None:
    """A token voided by a new QR and a token for no stored sale both get the same calm 401."""
    with pytest.raises(CustomerQrTokenInvalidError) as replaced_token_error:
        services.sessions.start(sign_qr_token(services.qr_token_signer, nonce=SECOND_NONCE))
    with pytest.raises(CustomerQrTokenInvalidError) as unknown_sale_error:
        services.sessions.start(
            sign_qr_token(services.qr_token_signer, sale_id="01JCSALE000000000000000999")
        )
    assert replaced_token_error.value.detail == unknown_sale_error.value.detail


def test_start_on_an_overdue_sale_keeps_its_expiry_and_refuses(
    services: CustomerServices, kit: ServiceTestKit
) -> None:
    """A sale past its hour is stored EXPIRED, and its QR answers like any invalid one."""
    qr_token = sign_qr_token(services.qr_token_signer, lifetime=CHOOSING_LIFETIME * 2)
    kit.clock.advance(CHOOSING_LIFETIME)
    with pytest.raises(CustomerQrTokenInvalidError):
        services.sessions.start(qr_token)
    assert kit.database.sales_by_id[SALE_ID].status is SaleStatus.EXPIRED
    assert kit.database.customer_sessions_by_id == {}


def test_start_on_a_sale_the_customer_already_agreed_to_is_refused(
    services: CustomerServices, kit: ServiceTestKit
) -> None:
    """Only a CHOOSING sale can be opened from its QR."""
    sale = kit.database.sales_by_id[SALE_ID]
    kit.database.sales_by_id[SALE_ID] = replace(
        sale,
        status=SaleStatus.READY_TO_PAY,
        chosen_plan=build_first_consent_record().evidence.plan_snapshot.chosen_plan,
    )
    with pytest.raises(CustomerQrTokenInvalidError):
        services.sessions.start(sign_qr_token(services.qr_token_signer))


def test_start_with_a_new_qr_revokes_the_earlier_session(
    services: CustomerServices, kit: ServiceTestKit
) -> None:
    """The merchant's new QR opens a new session, and the earlier phone's token stops working."""
    first_session = services.sessions.start(sign_qr_token(services.qr_token_signer))
    reissue_qr_token(kit, SECOND_NONCE)
    second_session = services.sessions.start(
        sign_qr_token(services.qr_token_signer, nonce=SECOND_NONCE)
    )
    stored_first = kit.database.customer_sessions_by_id[first_session.customer_session_id]
    assert stored_first.revoked_at == CREATED_AT
    with pytest.raises(CustomerSessionTokenInvalidError):
        services.sessions.resolve(credentials_of(first_session))
    assert services.sessions.resolve(credentials_of(second_session)).id == (
        second_session.customer_session_id
    )


def test_resolve_with_an_unknown_token_is_401_and_another_id_is_404(
    services: CustomerServices,
) -> None:
    """Probing gets one answer each: a bad token 401, a good token on another id 404."""
    started_session = services.sessions.start(sign_qr_token(services.qr_token_signer))
    with pytest.raises(CustomerSessionTokenInvalidError):
        services.sessions.resolve(
            CustomerSessionCredentials(started_session.customer_session_id, "wrong-token")
        )
    with pytest.raises(CustomerSessionNotFoundError):
        services.sessions.resolve(
            CustomerSessionCredentials("01JCSESSION000000000000999", started_session.session_token)
        )


def test_resolve_at_the_session_expiry_moment_is_refused(
    services: CustomerServices, kit: ServiceTestKit
) -> None:
    """A session lasts 30 minutes; at its expiry the phone asks the shop for a new QR."""
    started_session = services.sessions.start(sign_qr_token(services.qr_token_signer))
    kit.clock.advance(SESSION_LIFETIME)
    with pytest.raises(CustomerSessionTokenInvalidError):
        services.sessions.resolve(credentials_of(started_session))


def test_get_summary_gives_c1_facts_and_only_the_customers_own_progress(
    services: CustomerServices, kit: ServiceTestKit
) -> None:
    """Nothing chosen yet: no budget, comfort not asked, no language, no consent."""
    started_session = services.sessions.start(sign_qr_token(services.qr_token_signer))
    summary = services.sessions.get_summary(credentials_of(started_session))
    assert summary.customer_session_id == started_session.customer_session_id
    assert (summary.session_code, summary.shop_name, summary.product_name) == (
        "4821",
        "Ravi Electronics",
        "Example phone, 128 GB",
    )
    assert summary.price == Money.from_rupees(22000)
    assert summary.expires_at == started_session.expires_at
    assert summary.has_confirmed_budget is False
    assert summary.comfort_check_status is ComfortCheckStatus.NOT_ASKED
    assert summary.language is None
    assert summary.has_consented is False
    kit.database.consent_records.append(build_first_consent_record())
    services.choices.choose_language(credentials_of(started_session), CustomerLanguage.TAMIL)
    later_summary = services.sessions.get_summary(credentials_of(started_session))
    assert later_summary.has_consented is True
    assert later_summary.language is CustomerLanguage.TAMIL


def test_start_without_the_sale_product_or_shop_raises_typed_errors(
    services: CustomerServices, kit: ServiceTestKit
) -> None:
    """Stored data that lost its product or shop is reported, never guessed."""
    del kit.database.products_by_id[PRODUCT_ID]
    with pytest.raises(ProductNotFoundError):
        services.sessions.start(sign_qr_token(services.qr_token_signer))
    del kit.database.merchants_by_id[MERCHANT_ID]
    with pytest.raises(InvalidSaleDataError):
        services.sessions.start(sign_qr_token(services.qr_token_signer))


def test_session_whose_sale_vanished_is_refused_as_invalid(
    services: CustomerServices, kit: ServiceTestKit
) -> None:
    """A session never outlives its sale; without one the token opens nothing."""
    started_session = services.sessions.start(sign_qr_token(services.qr_token_signer))
    del kit.database.sales_by_id[SALE_ID]
    with pytest.raises(CustomerSessionTokenInvalidError):
        services.sessions.get_summary(credentials_of(started_session))


def test_session_lifetime_is_the_configured_one(
    services: CustomerServices, kit: ServiceTestKit
) -> None:
    """The session expires exactly its lifetime after the exchange."""
    kit.clock.advance(timedelta(minutes=2))
    started_session = services.sessions.start(sign_qr_token(services.qr_token_signer))
    assert started_session.expires_at == kit.clock.now() + SESSION_LIFETIME
