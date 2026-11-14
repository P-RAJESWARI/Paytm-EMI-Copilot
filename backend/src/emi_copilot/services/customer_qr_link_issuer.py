"""CustomerQrLinkIssuer: signs a fresh customer QR token for a sale and builds its URL."""

from dataclasses import dataclass
from datetime import timedelta

from emi_copilot.core.qr_token_signer import QrTokenSigner
from emi_copilot.domain.sales import CustomerQrTokenState
from emi_copilot.services.sale_views import CustomerQrLink


@dataclass(frozen=True, slots=True)
class IssuedCustomerQr:
    """The link to show once, and the token state (nonce hash and expiry) to store on the sale."""

    link: CustomerQrLink
    qr_token_state: CustomerQrTokenState


class CustomerQrLinkIssuer:
    """Issues QR tokens that last the configured lifetime and point at the customer web app.

    The URL is `{CUSTOMER_WEB_BASE_URL}/#t=<token>`: browsers never send a fragment to a server,
    so the token never reaches an access log. Only the nonce hash is kept.
    """

    def __init__(
        self, signer: QrTokenSigner, customer_web_base_url: str, token_lifetime: timedelta
    ) -> None:
        """Keeps the signer, the customer app's base URL (no final /) and the token lifetime."""
        self._signer = signer
        self._customer_web_base_url = customer_web_base_url
        self._token_lifetime = token_lifetime

    def issue(self, sale_id: str) -> IssuedCustomerQr:
        """Signs a new token for the sale and gives its link and the state to store."""
        issued_token = self._signer.issue(sale_id, self._token_lifetime)
        return IssuedCustomerQr(
            link=CustomerQrLink(
                customer_url=f"{self._customer_web_base_url}/#t={issued_token.token}",
                expires_at=issued_token.expires_at,
            ),
            qr_token_state=CustomerQrTokenState(
                nonce_hash=issued_token.nonce_hash, expires_at=issued_token.expires_at
            ),
        )
