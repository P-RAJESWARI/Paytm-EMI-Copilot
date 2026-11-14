"""A fake Paytm for httpx.MockTransport: routes by method and path to documented-shape fixtures.

It checks every request's signature with the OFFICIAL paytmchecksum library (an independent
implementation), signs status replies and webhook fields with the synthetic key, and remembers
which orders were linked and paid, so the contract suite can drive the real adapter end to end.
"""

import json
from collections.abc import Callable
from decimal import Decimal
from pathlib import Path
from typing import Any

import httpx
import paytmchecksum

FIXTURE_DIRECTORY = Path(__file__).parent.parent / "fixtures" / "paytm"
SYNTHETIC_MERCHANT_ID = "SYNTHETICMID00000001"
SYNTHETIC_MERCHANT_KEY = "0123456789abcdef"  # pragma: allowlist secret
BANKS_ROUTE = ("POST", "/theia/api/v1/emiSubvention/banks")
TENURES_ROUTE = ("POST", "/theia/api/v1/emiSubvention/tenures")
CREATE_LINK_ROUTE = ("POST", "/link/create")
STATUS_ROUTE = ("POST", "/v3/order/status")
SUCCESSFUL_TENURES_PAIR = ("DEMOA", "CREDIT_CARD")
BODY_MEMBER_MARKER = ',"body":'

# A scripted answer replaces the fixture route once: a reply, or an httpx error class to raise.
ScriptedAnswer = httpx.Response | type[httpx.RequestError]


def read_fixture_text(fixture_name: str) -> str:
    """Reads one fixture file exactly as written."""
    return (FIXTURE_DIRECTORY / fixture_name).read_text(encoding="utf-8")


def load_fixture(fixture_name: str) -> dict[str, Any]:
    """Parses one fixture with every fractional number as Decimal, never float."""
    loaded: dict[str, Any] = json.loads(read_fixture_text(fixture_name), parse_float=Decimal)
    return loaded


def split_signed_body_text(request: httpx.Request) -> tuple[dict[str, Any], str]:
    """Gives the sent head and the exact body text, which the adapter always writes last."""
    request_text = request.content.decode("utf-8")
    marker_position = request_text.rindex(BODY_MEMBER_MARKER)
    body_text = request_text[marker_position + len(BODY_MEMBER_MARKER) : -1]
    envelope = json.loads(request_text, parse_float=Decimal)
    assert json.loads(body_text, parse_float=Decimal) == envelope["body"]
    head: dict[str, Any] = envelope["head"]
    return head, body_text


def sign_status_reply(body: dict[str, Any]) -> str:
    """Writes a status reply whose head signs the pretty-printed body text with the official lib."""
    body_text = json.dumps(body, indent=2)
    signature: str = paytmchecksum.generateSignature(body_text, SYNTHETIC_MERCHANT_KEY)
    return '{"head": {"signature": "' + signature + '"},\n "body": ' + body_text + "}"


class FakePaytmServer:
    """Answers the four Paytm APIs from fixtures; scripted answers take precedence, in order."""

    def __init__(self) -> None:
        """Starts with no requests, no linked orders and no scripted answers."""
        self.received_requests: list[httpx.Request] = []
        self.linked_amount_by_order_id: dict[str, Decimal] = {}
        self.paid_order_ids: set[str] = set()
        self.scripted_answers: dict[tuple[str, str], list[ScriptedAnswer]] = {}
        self._routes: dict[tuple[str, str], Callable[[dict[str, Any]], httpx.Response]] = {
            BANKS_ROUTE: lambda _body: self._fixture_reply("banks_success.json"),
            TENURES_ROUTE: self._answer_tenures,
            CREATE_LINK_ROUTE: self._answer_create_link,
            STATUS_ROUTE: self._answer_status,
        }

    def script(self, route: tuple[str, str], *answers: ScriptedAnswer) -> None:
        """Queues answers for a route; each is used once before the fixture route resumes."""
        self.scripted_answers.setdefault(route, []).extend(answers)

    def requests_to(self, route: tuple[str, str]) -> list[httpx.Request]:
        """Lists the received requests for one route, in order."""
        return [request for request in self.received_requests if self._route_of(request) == route]

    def mark_order_paid(self, order_id: str) -> None:
        """Makes the status API report a linked order as paid at its link amount."""
        self.paid_order_ids.add(order_id)

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        """Records the request, checks its signature, then answers as scripted or from fixtures."""
        self.received_requests.append(request)
        route = self._route_of(request)
        head, body_text = split_signed_body_text(request)
        signature = head.get("token") or head.get("signature")
        assert paytmchecksum.verifySignature(body_text, SYNTHETIC_MERCHANT_KEY, signature)
        scripted_answers = self.scripted_answers.get(route)
        if scripted_answers:
            scripted_answer = scripted_answers.pop(0)
            if isinstance(scripted_answer, httpx.Response):
                return scripted_answer
            raise scripted_answer("synthetic transport failure", request=request)
        return self._routes[route](json.loads(body_text, parse_float=Decimal))

    def build_signed_webhook_fields(
        self, order_id: str, status_value: str, transaction_id: str, amount_text: str | None
    ) -> dict[str, str]:
        """Builds the documented webhook fields for an order, signed with the official library."""
        webhook_fields: dict[str, str] = load_fixture("webhook_form_fields.json")
        webhook_fields.update(ORDERID=order_id, STATUS=status_value, TXNID=transaction_id)
        if amount_text is not None:
            webhook_fields["TXNAMOUNT"] = amount_text
        checksum = paytmchecksum.generateSignature(dict(webhook_fields), SYNTHETIC_MERCHANT_KEY)
        return {**webhook_fields, "CHECKSUMHASH": checksum}

    def _route_of(self, request: httpx.Request) -> tuple[str, str]:
        """Gives the method and path a request was sent to."""
        return request.method, request.url.path

    def _fixture_reply(self, fixture_name: str) -> httpx.Response:
        """Answers 200 with one fixture's exact bytes."""
        return httpx.Response(200, content=read_fixture_text(fixture_name).encode("utf-8"))

    def _answer_tenures(self, request_body: dict[str, Any]) -> httpx.Response:
        """Answers the one bank and card type with plans; any other pair is a refusal."""
        requested_pair = (request_body["filters"]["bankCode"], request_body["filters"]["cardType"])
        if requested_pair == SUCCESSFUL_TENURES_PAIR:
            return self._fixture_reply("tenures_success.json")
        return self._fixture_reply("tenures_failure.json")

    def _answer_create_link(self, request_body: dict[str, Any]) -> httpx.Response:
        """Remembers the linked order and its amount, then answers with the success fixture."""
        self.linked_amount_by_order_id[request_body["linkOrderId"]] = request_body["amount"]
        return self._fixture_reply("create_link_success.json")

    def _answer_status(self, request_body: dict[str, Any]) -> httpx.Response:
        """Answers NO_RECORD_FOUND, PENDING or TXN_SUCCESS for the order, with a signed head."""
        order_id: str = request_body["orderId"]
        if order_id in self.paid_order_ids:
            body = load_fixture("status_txn_success.json")["body"]
            body["txnAmount"] = f"{self.linked_amount_by_order_id[order_id]:.2f}"
        elif order_id in self.linked_amount_by_order_id:
            body = load_fixture("status_pending.json")["body"]
        else:
            body = load_fixture("status_no_record_found.json")["body"]
        body["orderId"] = order_id
        return httpx.Response(200, content=sign_status_reply(body).encode("utf-8"))
