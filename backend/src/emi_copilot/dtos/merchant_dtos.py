"""Wire schemas of the merchant pairing and profile endpoints; no customer data is exposed."""

from datetime import UTC
from typing import Annotated, Final, Literal

from pydantic import AwareDatetime, Field, StringConstraints

from emi_copilot.domain.merchants import MerchantPrincipal
from emi_copilot.dtos.wire_types import CamelCaseRequestBodyModel, CamelCaseResponseModel
from emi_copilot.services.pair_device_service import DevicePairingResult, PairDeviceCommand

# Shop ids are printed upper-case (RAVI-0193); lower-case input is accepted and upper-cased.
SHOP_ID_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9-]{0,31}$"
PAIRING_PIN_PATTERN = r"^[0-9]{6}$"
BEARER_AUTHORIZATION_SCHEME: Final = "Bearer"


class PairDeviceRequest(CamelCaseRequestBodyModel):
    """The shop id and 6-digit pairing PIN typed on the counter device (M1)."""

    shop_id: Annotated[
        str,
        StringConstraints(pattern=SHOP_ID_PATTERN),
        Field(description="The shop's id, as printed for the shop.", examples=["RAVI-0193"]),
    ]
    pin: Annotated[
        str,
        StringConstraints(pattern=PAIRING_PIN_PATTERN),
        Field(
            description="The shop's 6-digit pairing PIN, as text so leading zeros survive.",
            json_schema_extra={"format": "password", "writeOnly": True},
        ),
    ]

    def to_command(self) -> PairDeviceCommand:
        """Gives the pairing command, with the shop id in its stored upper-case form."""
        return PairDeviceCommand(shop_code=self.shop_id.upper(), pin=self.pin)


class MerchantProfileResponse(CamelCaseResponseModel):
    """The signed-in shop and device, as the merchant app shows them in its header."""

    merchant_id: Annotated[str, Field(examples=["01JD5Z0Q8M6X3V2N7B4C9K1T0C"])]
    shop_id: Annotated[str, Field(examples=["RAVI-0193"])]
    shop_name: Annotated[str, Field(examples=["Ravi Electronics"])]
    device_label: Annotated[str, Field(examples=["Counter tablet 1"])]

    @classmethod
    def from_principal(cls, principal: MerchantPrincipal) -> "MerchantProfileResponse":
        """Converts the signed-in principal; the device pairing id stays internal."""
        return cls(
            merchant_id=principal.merchant_id,
            shop_id=principal.shop_code,
            shop_name=principal.shop_name,
            device_label=principal.device_label,
        )


class DevicePairingResponse(CamelCaseResponseModel):
    """A new device token, shown once: send it as `Authorization: Bearer <accessToken>`."""

    access_token: Annotated[
        str,
        Field(
            description="Opaque bearer token; only its hash is stored, so it cannot be shown again."
        ),
    ]
    token_type: Literal["Bearer"]
    expires_at: Annotated[
        AwareDatetime,
        Field(description="When the token stops working, UTC.", examples=["2026-11-15T09:30:00Z"]),
    ]
    merchant: MerchantProfileResponse

    @classmethod
    def from_result(cls, result: DevicePairingResult) -> "DevicePairingResponse":
        """Converts the pairing result; the expiry is sent in UTC, rounded down to the second."""
        return cls(
            access_token=result.access_token,
            token_type=BEARER_AUTHORIZATION_SCHEME,
            expires_at=result.principal.access_expires_at.astimezone(UTC).replace(microsecond=0),
            merchant=MerchantProfileResponse.from_principal(result.principal),
        )
