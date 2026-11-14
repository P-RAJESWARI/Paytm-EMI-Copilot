"""UnexpectedErrorMiddleware answers a generic 500 problem, unless the response had started."""

from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.testclient import TestClient

from emi_copilot.api.unexpected_error_middleware import UnexpectedErrorMiddleware


class LateFailureError(Exception):
    """Stands in for a failure after the response headers were already sent."""


def build_failing_application() -> FastAPI:
    """Builds an application with one route that fails before and one that fails mid-stream."""
    application = FastAPI()
    application.add_middleware(UnexpectedErrorMiddleware)

    @application.get("/fails-before-responding")
    def fail_before_responding() -> None:
        """Fails before any response is sent."""
        raise LateFailureError

    @application.get("/fails-while-streaming")
    def fail_while_streaming() -> StreamingResponse:
        """Starts a streamed response that fails after its first chunk."""

        def generate_chunks() -> Iterator[bytes]:
            """Yields one chunk, then fails."""
            yield b"first chunk"
            raise LateFailureError

        return StreamingResponse(generate_chunks())

    return application


def test_failure_before_responding_answers_generic_500_problem() -> None:
    """The body is the generic problem, with no exception text."""
    response = TestClient(build_failing_application()).get("/fails-before-responding")
    assert response.status_code == 500
    assert response.headers["content-type"] == "application/problem+json"
    assert response.json()["code"] == "INTERNAL_SERVER_ERROR"


def test_failure_after_the_response_started_is_re_raised_not_masked() -> None:
    """A second response cannot be sent once headers are out, so the error propagates."""
    with pytest.raises(LateFailureError):
        TestClient(build_failing_application()).get("/fails-while-streaming")
