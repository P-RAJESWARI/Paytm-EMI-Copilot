"""PaytmChecksumSigner: known-answer vectors and two-way interoperability with paytmchecksum."""

import base64
import string

import paytmchecksum
import pytest
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from pydantic import SecretStr

from emi_copilot.adapters.payment_gateway.checksum_signer import (
    PaytmChecksumSigner,
    SecureRandomSaltSource,
    build_signed_text_for_fields,
)
from emi_copilot.adapters.payment_gateway.paytm_api_definitions import (
    CHECKSUM_INITIALISATION_VECTOR,
)
from tests.contract.payment_gateway.paytm_fake_server import SYNTHETIC_MERCHANT_KEY

FIXED_SALT = "AbC1"
SIGNED_TEXT = '{"mid":"SYNTHETICMID00000001","orderId":"ORDER-SAMPLE-0001"}'
SIGNED_FIELDS = {
    "MID": "SYNTHETICMID00000001",
    "ORDERID": "ORDER-SAMPLE-0001",
    "STATUS": "TXN_SUCCESS",
    "TXNAMOUNT": "22000.00",
    "BANKNAME": "null",
}
# Computed once by the official paytmchecksum 1.7.0 with its salt generator patched to "AbC1",
# the synthetic key 0123456789abcdef, and the text and fields above.
KNOWN_TEXT_SIGNATURE = (
    "Cj0Vi7dJQgNQ3UMZQcSr5LPu6WipQpMpdCjIucbUatqGofnASV+fRXdyku0w56Jz"  # pragma: allowlist secret
    "M2kFw/+PTmyGnRpKQlaTS9ZWHGwEbAjXz30YIOaoWBM="  # pragma: allowlist secret
)
KNOWN_FIELDS_SIGNATURE = (
    "Yg5+8XRiBFpNqmrHFOFnwW53MvhwyZYb5/aA4Fv1iI9XaPPDLLuSByEa38P7DAww"  # pragma: allowlist secret
    "yuxt/gAMFmf3Ee58fEaYn53XstGsn5SY0cmwzv+RhnM="  # pragma: allowlist secret
)
OTHER_SYNTHETIC_KEY = "fedcba9876543210"  # pragma: allowlist secret


class FixedSaltSource:
    """Salt source that always gives the same salt, for known-answer vectors."""

    def __init__(self, salt: str = FIXED_SALT) -> None:
        """Keeps the salt to hand out."""
        self._salt = salt

    def new_salt(self) -> str:
        """Returns the fixed salt."""
        return self._salt


@pytest.fixture
def signer() -> PaytmChecksumSigner:
    """Gives a signer on the synthetic key with the fixed salt."""
    return PaytmChecksumSigner(SecretStr(SYNTHETIC_MERCHANT_KEY), FixedSaltSource())


def test_checksum_signer_text_signature_matches_official_known_answer(
    signer: PaytmChecksumSigner,
) -> None:
    """With the same key and salt, our text signature is byte-for-byte the official one."""
    assert signer.generate_signature_for_text(SIGNED_TEXT) == KNOWN_TEXT_SIGNATURE


def test_checksum_signer_fields_signature_matches_official_known_answer(
    signer: PaytmChecksumSigner,
) -> None:
    """Fields sign as sorted values joined by "|", with "null" as empty text, like the official."""
    assert signer.generate_signature_for_fields(SIGNED_FIELDS) == KNOWN_FIELDS_SIGNATURE


def test_checksum_signer_verifies_the_known_answer_vectors(signer: PaytmChecksumSigner) -> None:
    """Both known vectors verify against the text and fields they were made from."""
    assert signer.is_signature_valid_for_text(SIGNED_TEXT, KNOWN_TEXT_SIGNATURE)
    assert signer.is_signature_valid_for_fields(SIGNED_FIELDS, KNOWN_FIELDS_SIGNATURE)


def test_checksum_signer_text_signature_verifies_with_the_official_library() -> None:
    """Ours to theirs, text form, with a random salt."""
    our_signature = PaytmChecksumSigner(
        SecretStr(SYNTHETIC_MERCHANT_KEY)
    ).generate_signature_for_text(SIGNED_TEXT)
    assert paytmchecksum.verifySignature(SIGNED_TEXT, SYNTHETIC_MERCHANT_KEY, our_signature)


def test_checksum_signer_fields_signature_verifies_with_the_official_library() -> None:
    """Ours to theirs, dict form, with a random salt."""
    our_signature = PaytmChecksumSigner(
        SecretStr(SYNTHETIC_MERCHANT_KEY)
    ).generate_signature_for_fields(SIGNED_FIELDS)
    assert paytmchecksum.verifySignature(dict(SIGNED_FIELDS), SYNTHETIC_MERCHANT_KEY, our_signature)


def test_checksum_signer_verifies_official_text_and_fields_signatures(
    signer: PaytmChecksumSigner,
) -> None:
    """Theirs to ours, both forms, with the official library's own random salt."""
    official_text_signature = paytmchecksum.generateSignature(SIGNED_TEXT, SYNTHETIC_MERCHANT_KEY)
    official_fields_signature = paytmchecksum.generateSignature(
        dict(SIGNED_FIELDS), SYNTHETIC_MERCHANT_KEY
    )
    assert signer.is_signature_valid_for_text(SIGNED_TEXT, official_text_signature)
    assert signer.is_signature_valid_for_fields(SIGNED_FIELDS, official_fields_signature)


def test_checksum_signer_fields_verification_ignores_checksumhash_and_keeps_input(
    signer: PaytmChecksumSigner,
) -> None:
    """CHECKSUMHASH is left out of the signed text, and the caller's mapping is not changed."""
    received_fields = {**SIGNED_FIELDS, "CHECKSUMHASH": KNOWN_FIELDS_SIGNATURE}
    copy_before = dict(received_fields)
    assert signer.is_signature_valid_for_fields(received_fields, KNOWN_FIELDS_SIGNATURE)
    assert received_fields == copy_before


@pytest.mark.parametrize(
    ("changed_field", "changed_value"),
    [("TXNAMOUNT", "22000.01"), ("STATUS", "TXN_FAILURE"), ("BANKNAME", "Demo Bank A")],
)
def test_checksum_signer_fields_with_a_changed_value_fail_verification(
    signer: PaytmChecksumSigner, changed_field: str, changed_value: str
) -> None:
    """Changing any one signed value after signing makes the signature invalid."""
    tampered_fields = {**SIGNED_FIELDS, changed_field: changed_value}
    assert not signer.is_signature_valid_for_fields(tampered_fields, KNOWN_FIELDS_SIGNATURE)


def test_checksum_signer_tampered_text_and_wrong_key_fail_verification(
    signer: PaytmChecksumSigner,
) -> None:
    """One changed character of the text, or another key, makes the signature invalid."""
    other_key_signer = PaytmChecksumSigner(SecretStr(OTHER_SYNTHETIC_KEY))
    assert not signer.is_signature_valid_for_text(SIGNED_TEXT + " ", KNOWN_TEXT_SIGNATURE)
    assert not other_key_signer.is_signature_valid_for_text(SIGNED_TEXT, KNOWN_TEXT_SIGNATURE)


@pytest.mark.parametrize(
    "malformed_signature",
    [
        "",
        "not base64 at all!",
        "QUJD",
        base64.b64encode(b"x" * 15).decode("ascii"),
        base64.b64encode(b"\x00" * 32).decode("ascii"),
        KNOWN_TEXT_SIGNATURE[:-4],
        "ü" * 8,
    ],
    ids=["empty", "not-base64", "short", "not-block-sized", "bad-padding", "cut", "non-ascii"],
)
def test_checksum_signer_malformed_signature_is_invalid_without_raising(
    signer: PaytmChecksumSigner, malformed_signature: str
) -> None:
    """Bad base64, length, padding or text answers False and never leaks an exception."""
    assert not signer.is_signature_valid_for_text(SIGNED_TEXT, malformed_signature)


def test_checksum_signer_decrypting_to_non_ascii_text_is_invalid() -> None:
    """A well-padded block that decrypts to bytes that are not ASCII is refused as invalid."""
    padded_non_ascii_bytes = b"\xff" * 12 + b"\x04" * 4
    encryptor = Cipher(
        algorithms.AES(SYNTHETIC_MERCHANT_KEY.encode("utf-8")),
        modes.CBC(CHECKSUM_INITIALISATION_VECTOR),
    ).encryptor()
    ciphertext = encryptor.update(padded_non_ascii_bytes) + encryptor.finalize()
    signer = PaytmChecksumSigner(SecretStr(SYNTHETIC_MERCHANT_KEY))
    assert not signer.is_signature_valid_for_text(
        SIGNED_TEXT, base64.b64encode(ciphertext).decode("ascii")
    )


def test_build_signed_text_for_fields_sorts_keys_and_blanks_null_in_any_case() -> None:
    """The signed text is the values in key order; "null", "NULL" and "Null" sign as empty."""
    assert build_signed_text_for_fields({"B": "2", "A": "1", "C": "NULL", "D": "Null"}) == "1|2||"


@pytest.mark.parametrize("unusable_key", ["", "short-key", SYNTHETIC_MERCHANT_KEY + "0"])
def test_checksum_signer_with_a_key_aes_cannot_use_raises_without_echoing_it(
    unusable_key: str,
) -> None:
    """Only 16, 24 or 32 byte keys are accepted, and the error never contains the key."""
    with pytest.raises(ValueError, match="16, 24 or 32 bytes") as raised:
        PaytmChecksumSigner(SecretStr(unusable_key))
    assert str(raised.value) == "The merchant key must be 16, 24 or 32 bytes long."


@pytest.mark.parametrize("unusable_salt", ["abc", "abcde", "ab-1", "ab c"])
def test_checksum_signer_with_an_unusable_salt_raises(unusable_salt: str) -> None:
    """A salt source that breaks the four-character [A-Za-z0-9] rule is refused."""
    signer = PaytmChecksumSigner(SecretStr(SYNTHETIC_MERCHANT_KEY), FixedSaltSource(unusable_salt))
    with pytest.raises(ValueError, match="four characters"):
        signer.generate_signature_for_text(SIGNED_TEXT)


def test_checksum_signer_repr_never_shows_the_merchant_key(signer: PaytmChecksumSigner) -> None:
    """Printing or logging the signer cannot reveal the key."""
    assert SYNTHETIC_MERCHANT_KEY not in repr(signer)
    assert SYNTHETIC_MERCHANT_KEY not in str(signer)


def test_secure_random_salt_source_gives_four_alphanumeric_characters() -> None:
    """The default salt is four characters from [A-Za-z0-9], and salts vary between calls."""
    salt_source = SecureRandomSaltSource()
    salts = {salt_source.new_salt() for _ in range(50)}
    allowed_characters = set(string.ascii_letters + string.digits)
    assert all(len(salt) == 4 and set(salt) <= allowed_characters for salt in salts)
    assert len(salts) > 1
