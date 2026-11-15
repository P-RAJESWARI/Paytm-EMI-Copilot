"""ConsentEvidence value object: every fact one consent proves, before it joins the hash chain."""

import re
from dataclasses import dataclass
from datetime import datetime

from emi_copilot.domain.consent.consent_plan_snapshot import ConsentPlanSnapshot
from emi_copilot.domain.consent.consent_reference import ConsentReference
from emi_copilot.domain.customer_sessions.customer_language import CustomerLanguage
from emi_copilot.domain.errors import InvalidConsentDataError
from emi_copilot.domain.payments.field_validation import (
    require_non_empty_text,
    require_sha256_hex,
    require_timezone_aware_moment,
)

_TWO_DIGITS_PATTERN = re.compile(r"[0-9]{2}")


# Pattern: Value Object. Every field here is evidence, so every field is covered by the record
# hash (ConsentRecordHasher); nothing personal beyond the phone's last two digits and its hash.
@dataclass(frozen=True, slots=True)
class ConsentEvidence:
    """Who agreed to what, when, in which language, and under which cooling-off wording.

    phone_hash is a keyed hash of the number the code was sent to, computed outside the domain;
    the number itself is never stored. cooling_off_wording_version names the cooling-off text
    shown, which is a placeholder until the lender confirms the period.
    """

    consent_id: str
    sale_id: str
    customer_session_id: str
    consent_reference: ConsentReference
    plan_snapshot: ConsentPlanSnapshot
    phone_last_two_digits: str
    phone_hash: str
    language: CustomerLanguage
    cooling_off_wording_version: str
    consented_at: datetime

    def __post_init__(self) -> None:
        """Rejects blank ids, wrong value types, a malformed phone digest and a naive moment."""
        for text, description in (
            (self.consent_id, "consent id"),
            (self.sale_id, "sale id"),
            (self.customer_session_id, "customer session id"),
            (self.cooling_off_wording_version, "cooling-off wording version"),
        ):
            require_non_empty_text(text, description, InvalidConsentDataError)
        for value, value_type in (
            (self.consent_reference, ConsentReference),
            (self.plan_snapshot, ConsentPlanSnapshot),
            (self.language, CustomerLanguage),
        ):
            if not isinstance(value, value_type):
                raise InvalidConsentDataError(f"Consent evidence needs a {value_type.__name__}.")
        if (
            not isinstance(self.phone_last_two_digits, str)
            or _TWO_DIGITS_PATTERN.fullmatch(self.phone_last_two_digits) is None
        ):
            raise InvalidConsentDataError("Only the phone's last two digits are kept.")
        require_sha256_hex(self.phone_hash, "phone hash", InvalidConsentDataError)
        require_timezone_aware_moment(self.consented_at, "consent moment", InvalidConsentDataError)
