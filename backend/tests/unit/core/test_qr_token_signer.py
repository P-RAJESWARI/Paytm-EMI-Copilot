"""QrTokenSigner: known-answer signing, tamper and wrong-key refusal, and the expiry boundary."""

import base64
import hashlib
import hmac
from datetime import UTC, datetime, timedelta

import pytest

from emi_copilot.core.qr_token_signer import (
    MAXIMUM_TOKEN_LENGTH,
    QrTokenClaims,
    QrTokenRejectedError,
    QrTokenRejectionReason,
    QrTokenSigner,
    hash_qr_token_nonce,
)
from tests.fixed_clock import FixedClock

SIGNING_KEY = b"synthetic-qr-signing-key-0123456789abcdef"  # pragma: allowlist secret
OTHER_SIGNING_KEY = b"another-synthetic-qr-signing-key-0123456789"
ISSUED_AT = datetime(2026, 11, 14, 10, 30, tzinfo=UTC)
EXPIRES_AT = datetime(2026, 11, 14, 10, 45, tzinfo=UTC)
SAMPLE_CLAIMS = QrTokenClaims(
    sale_id="01JCSALE000000000000000001", nonce="synthetic-nonce-0001", expires_at=EXPIRES_AT
)
KNOWN_PAYLOAD = (
    b'{"expiresAt":1794653100,"nonce":"synthetic-nonce-0001","saleId":"01JCSALE000000000000000001"}'
)
# Synthetic known-answer vector computed with SIGNING_KEY; not a credential.
KNOWN_PAYLOAD_PART = (
    "eyJleHBpcmVzQXQiOjE3OTQ2NTMxMDAsIm5vbmNlIjoic3ludGhldGljLW5v"  # pragma: allowlist secret
    "bmNlLTAwMDEiLCJzYWxlSWQiOiIwMUpDU0FMRTAwMDAwMDAwMDAwMDAwMDAw"  # pragma: allowlist secret
    "MSJ9"  # pragma: allowlist secret
)
KNOWN_SIGNATURE_PART = "MncAfudkMerpjBf7TQNekipGsE7RW9xfSrlMl7GvxLI"  # pragma: allowlist secret
KNOWN_TOKEN = f"{KNOWN_PAYLOAD_PART}.{KNOWN_SIGNATURE_PART}"


def encode_base64url(raw_bytes: bytes) -> str:
    """Encodes bytes as unpadded base64url, independently of the signer."""
    return base64.urlsafe_b64encode(raw_bytes).rstrip(b"=").decode("ascii")


def sign_with(signing_key: bytes, payload: bytes) -> str:
    """Builds a token by hand, the way an attacker holding a key would."""
    encoded_payload = encode_base64url(payload)
    signature = hmac.new(signing_key, encoded_payload.encode("ascii"), hashlib.sha256).digest()
    return f"{encoded_payload}.{encode_base64url(signature)}"


@pytest.fixture
def clock() -> FixedClock:
    """A clock at the moment the sample token was issued."""
    return FixedClock(ISSUED_AT)


@pytest.fixture
def signer(clock: FixedClock) -> QrTokenSigner:
    """A signer with the synthetic key on the test clock."""
    return QrTokenSigner(SIGNING_KEY, clock)


def test_sign_gives_the_known_answer_for_fixed_claims_and_key(signer: QrTokenSigner) -> None:
    """The token is base64url(compact sorted JSON) . base64url(HMAC-SHA256), recomputed by hand."""
    assert int(EXPIRES_AT.timestamp()) == 1_794_653_100
    assert signer.sign(SAMPLE_CLAIMS) == KNOWN_TOKEN
    assert sign_with(SIGNING_KEY, KNOWN_PAYLOAD) == KNOWN_TOKEN


def test_verify_gives_back_the_signed_claims(signer: QrTokenSigner) -> None:
    """A valid token round-trips to the same sale, nonce and expiry."""
    assert signer.verify(KNOWN_TOKEN) == SAMPLE_CLAIMS


def test_issue_draws_a_fresh_nonce_and_stores_only_its_hash(signer: QrTokenSigner) -> None:
    """Two tokens for one sale differ; the stored hash is the nonce's SHA-256, not the token."""
    first_token = signer.issue(SAMPLE_CLAIMS.sale_id, timedelta(minutes=15))
    second_token = signer.issue(SAMPLE_CLAIMS.sale_id, timedelta(minutes=15))
    first_claims = signer.verify(first_token.token)
    assert first_token.token != second_token.token
    assert first_token.nonce_hash == hash_qr_token_nonce(first_claims.nonce)
    assert first_token.nonce_hash != second_token.nonce_hash
    assert first_claims.sale_id == SAMPLE_CLAIMS.sale_id
    assert "token" not in repr(first_token).replace("IssuedQrToken", "")


def test_issue_rounds_the_expiry_down_to_whole_seconds(clock: FixedClock) -> None:
    """A token never lasts longer than its lifetime, and the expiry shown is the token's own."""
    clock.advance(timedelta(microseconds=999_999))
    issued_token = QrTokenSigner(SIGNING_KEY, clock).issue("sale-1", timedelta(minutes=15))
    assert issued_token.expires_at == ISSUED_AT + timedelta(minutes=15)


@pytest.mark.parametrize(
    ("elapsed", "is_expected_valid"),
    [
        (timedelta(minutes=15) - timedelta(microseconds=1), True),
        (timedelta(minutes=15), False),
        (timedelta(minutes=16), False),
    ],
)
def test_verify_at_exactly_expires_at_is_expired(
    clock: FixedClock, signer: QrTokenSigner, elapsed: timedelta, *, is_expected_valid: bool
) -> None:
    """Valid while now < expiresAt; at expiresAt itself the token is refused as EXPIRED."""
    clock.advance(elapsed)
    if is_expected_valid:
        assert signer.verify(KNOWN_TOKEN) == SAMPLE_CLAIMS
    else:
        with pytest.raises(QrTokenRejectedError) as raised_error:
            signer.verify(KNOWN_TOKEN)
        assert raised_error.value.reason is QrTokenRejectionReason.EXPIRED


def test_verify_refuses_a_token_signed_with_another_key(clock: FixedClock) -> None:
    """A token from another deployment's key is a signature mismatch."""
    other_signer = QrTokenSigner(OTHER_SIGNING_KEY, clock)
    with pytest.raises(QrTokenRejectedError) as raised_error:
        other_signer.verify(KNOWN_TOKEN)
    assert raised_error.value.reason is QrTokenRejectionReason.SIGNATURE_MISMATCH


@pytest.mark.parametrize(
    "tampered_token",
    [
        sign_with(OTHER_SIGNING_KEY, KNOWN_PAYLOAD.replace(b"1794653100", b"1894653100")),
        KNOWN_PAYLOAD_PART.replace("eyJl", "eyJm", 1) + "." + KNOWN_SIGNATURE_PART,
        KNOWN_TOKEN[:-1] + "J",
        encode_base64url(KNOWN_PAYLOAD.replace(b"0001", b"0002")) + "." + KNOWN_SIGNATURE_PART,
    ],
    ids=["resigned-longer-expiry", "edited-payload", "re-encoded-signature", "other-sale"],
)
def test_verify_refuses_a_tampered_token(signer: QrTokenSigner, tampered_token: str) -> None:
    """Any change to payload or signature, including a non-canonical re-encoding, is refused."""
    with pytest.raises(QrTokenRejectedError) as raised_error:
        signer.verify(tampered_token)
    assert raised_error.value.reason is QrTokenRejectionReason.SIGNATURE_MISMATCH


@pytest.mark.parametrize(
    "malformed_token",
    [
        "",
        "no-dot-at-all",
        "two.dots.here",
        "has space.abc",
        "a" * (MAXIMUM_TOKEN_LENGTH + 1),
    ],
)
def test_verify_refuses_a_token_that_is_not_two_base64url_parts(
    signer: QrTokenSigner, malformed_token: str
) -> None:
    """The shape is checked before any cryptography runs."""
    with pytest.raises(QrTokenRejectedError) as raised_error:
        signer.verify(malformed_token)
    assert raised_error.value.reason is QrTokenRejectionReason.MALFORMED


@pytest.mark.parametrize(
    "payload",
    [
        b"not json",
        b"\xff\xfe",
        b"[1, 2, 3]",
        b'{"expiresAt":1794653100,"nonce":"n","saleId":"s","extra":1}',
        b'{"expiresAt":true,"nonce":"n","saleId":"s"}',
        b'{"expiresAt":"1794653100","nonce":"n","saleId":"s"}',
        b'{"expiresAt":1794653100,"nonce":7,"saleId":"s"}',
        b'{"expiresAt":1794653100,"nonce":"n","saleId":""}',
        b'{"expiresAt":99999999999999999999,"nonce":"n","saleId":"s"}',
    ],
)
def test_verify_refuses_a_correctly_signed_but_malformed_payload(
    signer: QrTokenSigner, payload: bytes
) -> None:
    """Even our own signature cannot make an unexpected payload acceptable."""
    with pytest.raises(QrTokenRejectedError) as raised_error:
        signer.verify(sign_with(SIGNING_KEY, payload))
    assert raised_error.value.reason is QrTokenRejectionReason.MALFORMED


def test_verify_refuses_a_correctly_signed_payload_part_that_is_not_base64(
    signer: QrTokenSigner,
) -> None:
    """One base64url character decodes to nothing, even when its signature matches."""
    signature = hmac.new(SIGNING_KEY, b"A", hashlib.sha256).digest()
    with pytest.raises(QrTokenRejectedError) as raised_error:
        signer.verify(f"A.{encode_base64url(signature)}")
    assert raised_error.value.reason is QrTokenRejectionReason.MALFORMED


def test_rejection_message_names_the_reason_and_never_the_token(signer: QrTokenSigner) -> None:
    """Errors may be logged, so they carry no token text."""
    with pytest.raises(QrTokenRejectedError) as raised_error:
        signer.verify(KNOWN_TOKEN[:-1] + "J")
    assert str(raised_error.value) == "QR token rejected: SIGNATURE_MISMATCH"


def test_signer_refuses_a_key_shorter_than_32_bytes(clock: FixedClock) -> None:
    """A short HMAC key would make forging QR codes easier."""
    with pytest.raises(ValueError, match="at least 32 bytes"):
        QrTokenSigner(b"short", clock)


@pytest.mark.parametrize(
    "claims_fields",
    [
        {"sale_id": "", "nonce": "n", "expires_at": EXPIRES_AT},
        {"sale_id": "s", "nonce": "", "expires_at": EXPIRES_AT},
        {"sale_id": "s", "nonce": "n", "expires_at": EXPIRES_AT.replace(tzinfo=None)},
        {"sale_id": "s", "nonce": "n", "expires_at": EXPIRES_AT.replace(microsecond=5)},
    ],
)
def test_claims_need_ids_and_an_aware_whole_second_expiry(claims_fields: dict[str, object]) -> None:
    """Claims that could not survive the Unix-seconds encoding are refused."""
    with pytest.raises(ValueError, match="QR token"):
        QrTokenClaims(**claims_fields)  # type: ignore[arg-type]
