"""CustomerLanguage: the language the customer chose on C1, carried into the receipt."""

from enum import StrEnum


class CustomerLanguage(StrEnum):
    """English or Tamil, by the language tag also used in Accept-Language; stored by value."""

    ENGLISH = "en"
    TAMIL = "ta"
