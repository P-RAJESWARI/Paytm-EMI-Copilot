"""MerchantPrincipal: who a valid bearer token signs in, as every merchant endpoint sees it."""

from dataclasses import dataclass
from datetime import datetime


# Pattern: Value Object. The authenticated caller; services scope every query by its merchant id.
@dataclass(frozen=True, slots=True)
class MerchantPrincipal:
    """The signed-in shop and device: ids, the shop's code and name, and the token's expiry."""

    merchant_id: str
    shop_code: str
    shop_name: str
    device_pairing_id: str
    device_label: str
    access_expires_at: datetime
