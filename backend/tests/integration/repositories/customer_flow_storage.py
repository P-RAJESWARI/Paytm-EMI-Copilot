"""Stores the shop, product, sales and session that customer flow rows refer to."""

from sqlalchemy.orm import Session, sessionmaker

from emi_copilot.domain.sales import SessionCode
from emi_copilot.repositories.unit_of_work import SqlAlchemyUnitOfWork
from tests.consent_builders import build_customer_session
from tests.fixed_clock import FixedClock
from tests.merchant_builders import build_catalogue_product, build_merchant
from tests.sale_builders import build_sale

OTHER_SALE_ID = "01JCSALE000000000000000002"


def store_sales_and_session(
    session_factory: sessionmaker[Session], fixed_clock: FixedClock
) -> None:
    """Commits the sample shop and product, two sales and the sample session on the first."""
    with SqlAlchemyUnitOfWork(session_factory, fixed_clock) as unit_of_work:
        unit_of_work.merchants.add(build_merchant())
        unit_of_work.products.add(build_catalogue_product())
        unit_of_work.sales.add(build_sale())
        unit_of_work.sales.add(build_sale(id=OTHER_SALE_ID, session_code=SessionCode("4822")))
        unit_of_work.customer_sessions.add(build_customer_session())
