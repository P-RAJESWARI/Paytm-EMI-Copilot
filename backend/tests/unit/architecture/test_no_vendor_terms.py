"""No vendor vocabulary in domain/ or the gateway port; vendor names belong to its adapter only.

The scan covers every identifier, string (docstrings included) and comment. Identifiers are split
at underscores and camelCase humps first, so a term hidden inside a longer name is still found.
"""

import io
import re
import tokenize
from pathlib import Path

import pytest

from tests.unit.architecture.source_files import (
    PAYMENT_GATEWAY_PORT_FILE,
    describe_source_file,
    list_domain_modules,
)

# The vendor's brand, its signature and API-host words, and its response field names.
VENDOR_TERM_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"paytm",
        r"checksum",
        r"theia",
        r"txn",
        r"\bmid\b",
        r"CHECKSUMHASH",
        r"resultInfo",
    )
)
SCANNED_TOKEN_TYPES = frozenset(
    {tokenize.NAME, tokenize.STRING, tokenize.FSTRING_MIDDLE, tokenize.COMMENT}
)
CAMEL_CASE_HUMP = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")


def split_into_words(token_text: str) -> str:
    """Separates snake_case and camelCase parts with spaces, so word-boundary terms can match."""
    return CAMEL_CASE_HUMP.sub(" ", token_text).replace("_", " ")


def find_vendor_terms(source_text: str) -> list[str]:
    """Lists each identifier, string or comment of the source that contains a vendor term."""
    offending_tokens: list[str] = []
    for token in tokenize.generate_tokens(io.StringIO(source_text).readline):
        if token.type not in SCANNED_TOKEN_TYPES:
            continue
        searchable_texts = (token.string, split_into_words(token.string))
        if any(
            pattern.search(text) for pattern in VENDOR_TERM_PATTERNS for text in searchable_texts
        ):
            offending_tokens.append(token.string)
    return offending_tokens


def list_scanned_files() -> list[Path]:
    """Lists the files that must stay free of vendor terms: all of domain/ and the port."""
    return [*list_domain_modules(), PAYMENT_GATEWAY_PORT_FILE]


@pytest.mark.parametrize("source_file", list_scanned_files(), ids=describe_source_file)
def test_source_file_contains_no_vendor_terms(source_file: Path) -> None:
    """Domain code and the port speak our language, so the Mock and real adapter can swap."""
    assert find_vendor_terms(source_file.read_text(encoding="utf-8")) == []


@pytest.mark.parametrize(
    "offending_source",
    [
        "VENDOR = 'Paytm'\n",
        "def sign_with_checksum() -> None: ...\n",
        "url = '/theia/api/v1'\n",
        "txn_amount = 1\n",
        "merchant_mid = 'x'\n",
        "mid = 'x'\n",
        "merchantMid = 'x'\n",
        "field = 'CHECKSUMHASH'\n",
        "status = body['resultInfo']\n",
        "# a comment naming PAYTM\n",
        "value = f'{order}TxnId'\n",
    ],
)
def test_find_vendor_terms_detects_every_vendor_term_form(offending_source: str) -> None:
    """The scanner finds vendor terms in names, strings, f-strings and comments, in any case."""
    assert find_vendor_terms(offending_source) != []


@pytest.mark.parametrize(
    "clean_source",
    ["midnight = 1\n", "amid_the_noise = 'pyramid'\n", "gateway_transaction_id = None\n"],
)
def test_find_vendor_terms_ignores_words_that_only_contain_mid(clean_source: str) -> None:
    """Ordinary words that merely contain "mid" are not mistaken for the merchant id term."""
    assert find_vendor_terms(clean_source) == []
