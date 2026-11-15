"""Speech, synthesis, teach-back and audited explanations over HTTP with the labelled Mocks."""

from collections.abc import Iterator
from contextlib import contextmanager

import httpx
import pytest
from sqlalchemy.orm import Session, sessionmaker

from emi_copilot.adapters.payment_gateway.mock_adapter import MockPaymentGatewayAdapter
from emi_copilot.config.ai_settings import AiProviderMode, AiSettings, MockAiTextBehaviour
from emi_copilot.config.settings import ApplicationSettings
from tests.fixed_clock import FixedClock
from tests.integration.api.api_harness import open_api_harness
from tests.integration.api.customer.customer_api_helpers import (
    CARDLESS_OFFER_ID,
    NO_COST_OFFER_ID,
    CustomerFlowHarness,
    CustomerSessionClient,
    as_response,
    store_ravi_electronics,
)
from tests.integration.api.customer.test_customer_session_endpoints import assert_problem

pytestmark = pytest.mark.integration

WEBM_CONTENT_TYPE = "audio/webm;codecs=opus"
SHORT_RECORDING = b"\x1a\x45\xdf\xa3 synthetic recording bytes"


@contextmanager
def open_flow_with_ai(
    session_factory: sessionmaker[Session],
    fixed_clock: FixedClock,
    mock_gateway: MockPaymentGatewayAdapter,
    ai_settings: AiSettings,
) -> Iterator[CustomerFlowHarness]:
    """Runs the application with the given AI settings and the design shop paired."""
    settings = ApplicationSettings(ai_settings=ai_settings)
    with open_api_harness(session_factory, fixed_clock, mock_gateway, settings) as harness:
        yield CustomerFlowHarness(api=harness, merchant_headers=store_ravi_electronics(harness))


def transcribe(
    session: CustomerSessionClient,
    recording: bytes = SHORT_RECORDING,
    content_type: str = WEBM_CONTENT_TYPE,
) -> httpx.Response:
    """Uploads a raw recording for the C2 budget."""
    return as_response(
        session.client.post(
            session.base_path + "/speech/transcriptions",
            params={"purpose": "BUDGET"},
            content=recording,
            headers={**session.headers, "Content-Type": content_type},
        )
    )


def synthesise(session: CustomerSessionClient, explanation_id: str) -> httpx.Response:
    """Asks to hear a shown explanation."""
    return as_response(
        session.client.post(
            session.base_path + "/speech/synthesis",
            json={"explanationId": explanation_id},
            headers=session.headers,
        )
    )


def teach_back(
    session: CustomerSessionClient, answer_text: str, offer_id: str = NO_COST_OFFER_ID
) -> httpx.Response:
    """Sends the customer's own words about a plan."""
    return as_response(
        session.client.post(
            session.base_path + "/teach-back",
            json={"offerId": offer_id, "answerText": answer_text},
            headers=session.headers,
        )
    )


def test_transcription_with_mock_speech_gives_the_amount_and_never_sets_the_budget(
    customer_flow: CustomerFlowHarness,
) -> None:
    """The Mock hears ₹3,000; the customer must still confirm it, so no budget is stored."""
    session = customer_flow.open_customer_session()
    assert session.started_body["isVoiceAvailable"] is True
    response = transcribe(session)
    assert response.status_code == 200, response.text
    assert response.json() == {
        "transcript": "₹3,000 a month",
        "recognisedAmountInPaise": 300_000,
        "isLikelyMisheard": False,
    }
    assert session.get_summary().json()["hasConfirmedBudget"] is False


def test_transcription_of_a_recording_over_the_limit_answers_422(
    customer_flow: CustomerFlowHarness,
) -> None:
    """One byte over the default 512 KiB is refused before any speech call."""
    session = customer_flow.open_customer_session()
    assert_problem(transcribe(session, bytes(524_289)), 422, "AUDIO_TOO_LARGE")


def test_transcription_of_text_or_an_empty_body_answers_422(
    customer_flow: CustomerFlowHarness,
) -> None:
    """Only a non-empty recording of an accepted audio type is transcribed."""
    session = customer_flow.open_customer_session()
    assert_problem(transcribe(session, content_type="text/plain"), 422, "AUDIO_FORMAT_UNSUPPORTED")
    assert_problem(transcribe(session, b""), 422, "AUDIO_FORMAT_UNSUPPORTED")


def test_speech_switched_off_hides_the_microphone_and_answers_a_calm_502(
    session_factory: sessionmaker[Session],
    fixed_clock: FixedClock,
    mock_gateway: MockPaymentGatewayAdapter,
) -> None:
    """With speech off the session says so, and a stray upload is SPEECH_UNAVAILABLE."""
    ai_settings = AiSettings(speech_provider_mode=AiProviderMode.OFF)
    with open_flow_with_ai(session_factory, fixed_clock, mock_gateway, ai_settings) as flow:
        session = flow.open_customer_session()
        assert session.get_summary().json()["isVoiceAvailable"] is False
        assert_problem(transcribe(session), 502, "SPEECH_UNAVAILABLE")


def test_synthesis_of_an_unknown_explanation_answers_404(
    customer_flow: CustomerFlowHarness,
) -> None:
    """The client cannot have arbitrary text spoken: only a shown explanation's id works."""
    session = customer_flow.open_customer_session()
    assert_problem(synthesise(session, "01JDNOTSHOWN000000000000000"), 404, "EXPLANATION_NOT_FOUND")


def test_synthesis_after_an_explanation_returns_uncached_audio_for_that_session_only(
    customer_flow: CustomerFlowHarness,
) -> None:
    """The shown text is spoken (the Mock's silent WAV); another session's id is not found."""
    session = customer_flow.open_customer_session()
    explanation_id = session.explain().json()["explanationId"]
    response = synthesise(session, explanation_id)
    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "audio/wav"
    assert response.headers["cache-control"] == "no-store"
    assert response.content.startswith(b"RIFF")
    other_session = customer_flow.open_customer_session()
    assert_problem(synthesise(other_session, explanation_id), 404, "EXPLANATION_NOT_FOUND")


@pytest.mark.parametrize(
    ("behaviour", "expected_source"),
    [
        (MockAiTextBehaviour.UNAVAILABLE, "TEMPLATE"),
        (MockAiTextBehaviour.WRONG_NUMBER, "TEMPLATE"),
        (MockAiTextBehaviour.CORRECT, "AI_AUDITED"),
    ],
)
def test_explanation_is_audited_ai_text_or_the_template_never_an_error(
    session_factory: sessionmaker[Session],
    fixed_clock: FixedClock,
    mock_gateway: MockPaymentGatewayAdapter,
    behaviour: MockAiTextBehaviour,
    expected_source: str,
) -> None:
    """AI unavailable or wrong still answers 200; a repeat gives the same text and id."""
    ai_settings = AiSettings(mock_ai_text_behaviour=behaviour)
    with open_flow_with_ai(session_factory, fixed_clock, mock_gateway, ai_settings) as flow:
        session = flow.open_customer_session()
        first = session.explain(CARDLESS_OFFER_ID)
        assert first.status_code == 200, first.text
        body = first.json()
        assert body["source"] == expected_source
        assert "₹2,050" in body["text"]
        assert body["highlightedAmounts"] == [
            {"kind": "MONTHLY_INSTALLMENT", "amountInPaise": 205_000},
            {"kind": "EXTRA_IN_TOTAL", "amountInPaise": 260_000},
        ]
        assert session.explain(CARDLESS_OFFER_ID).json() == body


def test_teach_back_close_enough_restates_the_plan_with_engine_figures(
    customer_flow: CustomerFlowHarness,
) -> None:
    """₹3,667 for 6 months matches plan A; the card restates its terms."""
    session = customer_flow.open_customer_session()
    response = teach_back(session, "3,667 every month for 6 months, nothing extra")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["result"] == "CLOSE_ENOUGH"
    assert body["heardText"] == "About ₹3,667 every month"
    assert body["highlightedAmounts"] == [
        {"kind": "MONTHLY_INSTALLMENT", "amountInPaise": 366_667},
        {"kind": "EXTRA_IN_TOTAL", "amountInPaise": 0},
    ]


def test_teach_back_wrong_terms_try_again_and_another_items_offer_is_not_found(
    customer_flow: CustomerFlowHarness,
) -> None:
    """₹2,000 for 3 months is TRY_AGAIN (advisory); an unknown offer answers 404."""
    session = customer_flow.open_customer_session()
    response = teach_back(session, "2,000 a month for 3 months")
    assert response.status_code == 200, response.text
    assert response.json()["result"] == "TRY_AGAIN"
    assert_problem(
        teach_back(session, "3,667", "offer-for-another-product"), 404, "OFFER_NOT_FOUND"
    )
