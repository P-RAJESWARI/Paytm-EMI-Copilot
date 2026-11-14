"""PaytmPaymentGatewayAdapter: the real payment gateway, over Paytm's documented HTTP APIs.

Built and tested against documented-shape fixtures only, until staging keys exist (ADR 0007).
Every Paytm name it uses comes from paytm_api_definitions and is [Verify].
"""

import httpx

from emi_copilot.adapters.payment_gateway.checksum_signer import PaytmChecksumSigner
from emi_copilot.adapters.payment_gateway.paytm_api_definitions import (
    ADAPTER_NAME,
    BANKS_PATH,
    BODY_FIELD,
    CREATE_LINK_PATH,
    HEAD_FIELD,
    HEAD_SIGNATURE_FIELD,
    MERCHANT_ID_QUERY_PARAMETER,
    TENURES_PATH,
    TRANSACTION_STATUS_PATH,
    WEBHOOK_CHECKSUM_FIELD,
)
from emi_copilot.adapters.payment_gateway.paytm_error_translator import (
    PaytmCallKind,
    PaytmErrorTranslator,
)
from emi_copilot.adapters.payment_gateway.paytm_gateway_configuration import (
    PaytmGatewayConfiguration,
    PaytmHttpClients,
)
from emi_copilot.adapters.payment_gateway.paytm_json_codec import (
    find_raw_top_level_member_text,
    parse_json_object,
    serialise_json,
)
from emi_copilot.adapters.payment_gateway.paytm_payload_mapper import (
    read_bank_card_pairs,
    read_payment_link,
    read_payment_status,
    read_tenure_offers,
    read_webhook_event,
)
from emi_copilot.adapters.payment_gateway.paytm_request_builder import (
    JsonRequestObject,
    build_banks_request_body,
    build_create_link_request_body,
    build_envelope_text,
    build_link_head,
    build_status_head,
    build_status_request_body,
    build_subvention_head,
    build_tenures_request_body,
)
from emi_copilot.adapters.payment_gateway.paytm_response_values import (
    JsonObject,
    read_object,
    read_optional_object,
    read_result_info,
)
from emi_copilot.adapters.payment_gateway.port import PaymentGatewayPort
from emi_copilot.core.clock import Clock
from emi_copilot.core.id_generator import IdGenerator
from emi_copilot.core.resilient_http_client import ResilientHttpClient
from emi_copilot.core.upstream_errors import UpstreamCallError
from emi_copilot.domain.errors import InvalidPaymentGatewayValueError, WebhookSignatureInvalidError
from emi_copilot.domain.payments import (
    EmiOffer,
    OfferDiscoveryQuery,
    PaymentLink,
    PaymentLinkRequest,
    PaymentStatusResult,
    UnverifiedWebhookNotification,
    VerifiedWebhookEvent,
)

BANKS_API_NAME = "banks"
TENURES_API_NAME = "tenures"
CREATE_LINK_API_NAME = "create_link"
TRANSACTION_STATUS_API_NAME = "transaction_status"
JSON_REQUEST_HEADERS = {"Content-Type": "application/json"}


def _join_url(base_url: str, path: str) -> str:
    """Appends an API path to a configured base URL, with or without its trailing slash."""
    return base_url.rstrip("/") + path


def _require_unique_offer_ids(offers: list[EmiOffer]) -> None:
    """Raises when two plans share a planId, since an offer id must pick exactly one plan."""
    if len({offer.offer_id for offer in offers}) != len(offers):
        raise InvalidPaymentGatewayValueError("The gateway quoted two plans with the same id.")


# Pattern: Adapter. Wraps the Paytm HTTP APIs behind PaymentGatewayPort.
class PaytmPaymentGatewayAdapter(PaymentGatewayPort):
    """Discovers offers, creates links, checks status and verifies webhooks through Paytm.

    Reads go through send_idempotent; Create Link goes through send_non_idempotent only, so it is
    sent at most once (ADR 0005). Every request body is serialised once, signed, and sent as
    exactly those bytes.
    """

    def __init__(
        self,
        *,
        configuration: PaytmGatewayConfiguration,
        http_clients: PaytmHttpClients,
        checksum_signer: PaytmChecksumSigner,
        clock: Clock,
        id_generator: IdGenerator,
    ) -> None:
        """Keeps the configuration, one resilient client per API family, signer, clock and ids."""
        self._configuration = configuration
        self._http_clients = http_clients
        self._checksum_signer = checksum_signer
        self._clock = clock
        self._id_generator = id_generator
        self._error_translator = PaytmErrorTranslator()

    @property
    def adapter_name(self) -> str:
        """Gives "paytm", the name stored as the gateway mode of every attempt it serves."""
        return ADAPTER_NAME

    @property
    def _merchant_id(self) -> str:
        """Gives the merchant id for a request body or query; it is never logged."""
        return self._configuration.merchant_id.get_secret_value()

    def discover_offers(self, query: OfferDiscoveryQuery) -> tuple[EmiOffer, ...]:
        """Asks Banks, then Tenures for every bank and card type; returns every plan, uncapped."""
        banks_body = self._call_subvention_api(
            BANKS_PATH, BANKS_API_NAME, build_banks_request_body(self._merchant_id, query)
        )
        offers: list[EmiOffer] = []
        for bank_card_pair in read_bank_card_pairs(banks_body):
            tenures_request_body = build_tenures_request_body(
                self._merchant_id, query, bank_card_pair
            )
            tenures_body = self._call_subvention_api(
                TENURES_PATH, TENURES_API_NAME, tenures_request_body
            )
            offers.extend(read_tenure_offers(tenures_body))
        _require_unique_offer_ids(offers)
        return tuple(offers)

    def create_payment_link(self, request: PaymentLinkRequest) -> PaymentLink:
        """Sends Create Link exactly once and returns the short URL to share with the customer."""
        body_text = serialise_json(
            build_create_link_request_body(
                self._merchant_id, request, self._configuration.webhook_callback_url
            )
        )
        head = build_link_head(self._checksum_signer.generate_signature_for_text(body_text))
        http_request = self._build_post_request(
            _join_url(self._configuration.payment_link_base_url, CREATE_LINK_PATH), head, body_text
        )
        try:
            response = self._http_clients.payment_link.send_non_idempotent(http_request)
        except UpstreamCallError as error:
            raise self._error_translator.translate_upstream_error(
                error, PaytmCallKind.PAYMENT_LINK_CREATION
            ) from error
        _, document = self._read_reply_document(response, CREATE_LINK_API_NAME)
        link_body = read_object(document, BODY_FIELD)
        self._error_translator.require_link_creation_success(
            read_result_info(link_body), CREATE_LINK_API_NAME
        )
        return read_payment_link(link_body, request.order_id)

    def get_payment_status(self, order_id: str) -> PaymentStatusResult:
        """Asks the v3 status API, verifies the reply signature when present, maps the status."""
        body_text = serialise_json(build_status_request_body(self._merchant_id, order_id))
        head = build_status_head(self._checksum_signer.generate_signature_for_text(body_text))
        http_request = self._build_post_request(
            _join_url(self._configuration.transaction_status_base_url, TRANSACTION_STATUS_PATH),
            head,
            body_text,
        )
        response = self._send_idempotent(self._http_clients.transaction_status, http_request)
        reply_text, document = self._read_reply_document(response, TRANSACTION_STATUS_API_NAME)
        self._require_valid_reply_signature(reply_text, document)
        return read_payment_status(read_object(document, BODY_FIELD), order_id, self._merchant_id)

    def verify_webhook(self, notification: UnverifiedWebhookNotification) -> VerifiedWebhookEvent:
        """Verifies CHECKSUMHASH over every other field first; only then reads MID and payment."""
        received_fields = notification.received_fields
        checksum = received_fields.get(WEBHOOK_CHECKSUM_FIELD, "")
        if not checksum or not self._checksum_signer.is_signature_valid_for_fields(
            received_fields, checksum
        ):
            raise WebhookSignatureInvalidError(
                "The notification checksum is missing or does not match its fields."
            )
        return read_webhook_event(received_fields, self._merchant_id)

    def _call_subvention_api(
        self, path: str, api_name: str, request_body: JsonRequestObject
    ) -> JsonObject:
        """Signs and sends one Banks or Tenures request (retried as a read); gives its body."""
        body_text = serialise_json(request_body)
        head = build_subvention_head(
            request_id=self._id_generator.new_id(),
            request_timestamp=str(int(self._clock.now().timestamp())),
            token=self._checksum_signer.generate_signature_for_text(body_text),
        )
        http_request = self._build_post_request(
            _join_url(self._configuration.emi_subvention_base_url, path),
            head,
            body_text,
            query_parameters={MERCHANT_ID_QUERY_PARAMETER: self._merchant_id},
        )
        response = self._send_idempotent(self._http_clients.emi_subvention, http_request)
        _, document = self._read_reply_document(response, api_name)
        reply_body = read_object(document, BODY_FIELD)
        self._error_translator.require_subvention_success(read_result_info(reply_body), api_name)
        return reply_body

    def _build_post_request(
        self,
        url: str,
        head: JsonRequestObject,
        signed_body_text: str,
        query_parameters: dict[str, str] | None = None,
    ) -> httpx.Request:
        """Builds a JSON POST whose body bytes are exactly the signed body text in its envelope."""
        return httpx.Request(
            "POST",
            url,
            params=query_parameters,
            content=build_envelope_text(head, signed_body_text).encode("utf-8"),
            headers=JSON_REQUEST_HEADERS,
        )

    def _send_idempotent(
        self, http_client: ResilientHttpClient, http_request: httpx.Request
    ) -> httpx.Response:
        """Sends a read with retries and turns a failed call into a domain error."""
        try:
            return http_client.send_idempotent(http_request)
        except UpstreamCallError as error:
            raise self._error_translator.translate_upstream_error(
                error, PaytmCallKind.IDEMPOTENT_READ
            ) from error

    def _read_reply_document(
        self, response: httpx.Response, api_name: str
    ) -> tuple[str, dict[str, object]]:
        """Gives the reply text and its parsed object; an answer that is not 2xx is a refusal."""
        if not response.is_success:
            raise self._error_translator.translate_unexpected_http_status(
                response.status_code, api_name
            )
        reply_text = response.text
        return reply_text, parse_json_object(reply_text)

    def _require_valid_reply_signature(self, reply_text: str, document: JsonObject) -> None:
        """Checks head.signature, when present, over the body text exactly as received [Verify].

        A mismatch raises InvalidPaymentGatewayValueError: the reply cannot be trusted as a
        status, and reading it again is the caller's safe choice.
        """
        head = read_optional_object(document, HEAD_FIELD)
        signature = None if head is None else head.get(HEAD_SIGNATURE_FIELD)
        if signature is None:
            return
        body_text = find_raw_top_level_member_text(reply_text, BODY_FIELD)
        is_valid = (
            isinstance(signature, str)
            and body_text is not None
            and self._checksum_signer.is_signature_valid_for_text(body_text, signature)
        )
        if not is_valid:
            raise InvalidPaymentGatewayValueError("The status reply signature does not match.")
