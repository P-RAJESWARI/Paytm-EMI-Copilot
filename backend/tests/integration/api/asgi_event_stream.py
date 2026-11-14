"""Reads a streaming response straight from the ASGI application, frame by frame.

TestClient and httpx's ASGI transport both wait for the whole body, which an endless event
stream never finishes, so this drives the ASGI interface directly on the test's event loop.
The application's lifespan must already be running (an open TestClient does that).
"""

import asyncio
from dataclasses import dataclass, field

from starlette.types import ASGIApp, Message

# Long enough for a slow CI machine, short enough that a missing frame fails fast.
FRAME_TIMEOUT_IN_SECONDS = 5.0


@dataclass
class AsgiEventStream:
    """One GET request held open: its status, its headers and the frames received so far."""

    application: ASGIApp
    path: str
    headers: dict[str, str]
    status_code: int = 0
    response_headers: dict[str, str] = field(default_factory=dict)
    is_finished: bool = False
    _sent_messages: asyncio.Queue[Message] = field(default_factory=asyncio.Queue)
    _client_disconnected: asyncio.Event = field(default_factory=asyncio.Event)
    _has_sent_request: bool = False
    _buffer: bytes = b""
    _application_task: asyncio.Task[None] | None = None

    async def open(self) -> None:
        """Sends the request and waits for the response to start."""
        self._application_task = asyncio.create_task(self._run_application())
        start = await asyncio.wait_for(self._sent_messages.get(), FRAME_TIMEOUT_IN_SECONDS)
        self.status_code = start["status"]
        self.response_headers = {
            name.decode("latin-1"): value.decode("latin-1") for name, value in start["headers"]
        }

    async def read_frame(self) -> str | None:
        """Gives the next whole frame (without its blank line), or None once the body ended."""
        while b"\n\n" not in self._buffer:
            if self.is_finished:
                return None
            message = await asyncio.wait_for(self._sent_messages.get(), FRAME_TIMEOUT_IN_SECONDS)
            self._buffer += message.get("body", b"")
            self.is_finished = not message.get("more_body", False)
        frame, self._buffer = self._buffer.split(b"\n\n", 1)
        return frame.decode("utf-8")

    async def read_frame_other_than_heartbeat(self) -> str | None:
        """Skips heartbeat comments and gives the next real frame, or None at the end."""
        frame = await self.read_frame()
        while frame == ": heartbeat":
            frame = await self.read_frame()
        return frame

    async def close(self) -> None:
        """Disconnects like a closed browser tab and waits for the application to finish."""
        self._client_disconnected.set()
        if self._application_task is not None:
            await asyncio.wait_for(self._application_task, FRAME_TIMEOUT_IN_SECONDS)

    async def _run_application(self) -> None:
        """Runs the application on this one request until it finishes."""
        await self.application(self._build_scope(), self._receive, self._send)

    def _build_scope(self) -> dict[str, object]:
        """Gives the HTTP scope of a plain GET from a test client address."""
        return {
            "type": "http",
            # spec 2.3: Starlette then listens for http.disconnect while it streams.
            "asgi": {"version": "3.0", "spec_version": "2.3"},
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": self.path,
            "raw_path": self.path.encode("ascii"),
            "root_path": "",
            "query_string": b"",
            "headers": [
                (name.lower().encode("latin-1"), value.encode("latin-1"))
                for name, value in self.headers.items()
            ],
            "client": ("testclient", 50000),
            "server": ("testserver", 80),
        }

    async def _receive(self) -> Message:
        """Gives the empty request body once, then waits until the test disconnects."""
        if not self._has_sent_request:
            self._has_sent_request = True
            return {"type": "http.request", "body": b"", "more_body": False}
        await self._client_disconnected.wait()
        return {"type": "http.disconnect"}

    async def _send(self, message: Message) -> None:
        """Keeps every message the application sends, in order."""
        await self._sent_messages.put(message)
