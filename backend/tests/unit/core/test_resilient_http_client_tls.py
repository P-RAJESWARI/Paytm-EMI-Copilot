"""Resilient HTTP client construction: verified TLS and explicit timeouts on every phase."""

import ssl

import httpx
import pytest

from emi_copilot.core.resilient_http_client import (
    UpstreamTimeouts,
    build_upstream_http_client,
    create_verified_tls_context,
)

UPSTREAM_TIMEOUTS = UpstreamTimeouts(
    connect_timeout_in_seconds=3.0,
    read_timeout_in_seconds=10.0,
    write_timeout_in_seconds=10.0,
    pool_timeout_in_seconds=3.0,
)


def test_create_verified_tls_context_requires_certificates_host_names_and_tls_1_2() -> None:
    """The TLS context verifies the server's certificate and name and refuses old protocols."""
    tls_context = create_verified_tls_context()
    assert tls_context.verify_mode is ssl.CERT_REQUIRED
    assert tls_context.check_hostname is True
    assert tls_context.minimum_version >= ssl.TLSVersion.TLSv1_2


def test_build_upstream_http_client_verifies_certificates_and_sets_every_timeout() -> None:
    """The constructed client never disables verification and has all four explicit timeouts."""
    with build_upstream_http_client(UPSTREAM_TIMEOUTS) as http_client:
        transport = http_client._transport
        assert isinstance(transport, httpx.HTTPTransport)
        tls_context = transport._pool._ssl_context
        assert tls_context is not None
        assert tls_context.verify_mode is ssl.CERT_REQUIRED
        assert tls_context.check_hostname is True
        assert http_client.timeout == httpx.Timeout(connect=3.0, read=10.0, write=10.0, pool=3.0)


def test_upstream_timeouts_with_non_positive_value_raises_value_error() -> None:
    """A zero timeout would mean no deadline for that phase, so it is refused."""
    with pytest.raises(ValueError, match="must be positive"):
        UpstreamTimeouts(
            connect_timeout_in_seconds=3.0,
            read_timeout_in_seconds=0.0,
            write_timeout_in_seconds=10.0,
            pool_timeout_in_seconds=3.0,
        )
