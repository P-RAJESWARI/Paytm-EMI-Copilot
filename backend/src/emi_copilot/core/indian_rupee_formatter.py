"""Formats integer paise as whole rupees for text the backend itself writes (sent text artifacts).

backend.md section 5 keeps display formatting in the frontend. The weekly message (ADR 0018) and
the C7 template explanation, which Layer 4's AI text will wrap, are the exceptions: their numbers
are rendered here, in this one formatter (injected into them), and nowhere else in the backend.
"""

from decimal import ROUND_HALF_UP, Decimal

RUPEE_SYMBOL = "₹"
_PAISE_PER_RUPEE = 100
_INDIAN_LAST_GROUP_SIZE = 3
_INDIAN_LEADING_GROUP_SIZE = 2


def group_digits_the_indian_way(whole_number: int) -> str:
    """Groups digits as in India: the last three, then pairs (184000 gives "1,84,000")."""
    if isinstance(whole_number, bool) or not isinstance(whole_number, int):
        raise TypeError("Only a whole number can be grouped.")
    if whole_number < 0:
        raise ValueError("Only a non-negative whole number can be grouped.")
    digits = str(whole_number)
    last_group = digits[-_INDIAN_LAST_GROUP_SIZE:]
    leading_digits = digits[:-_INDIAN_LAST_GROUP_SIZE]
    leading_groups: list[str] = []
    while leading_digits:
        leading_groups.insert(0, leading_digits[-_INDIAN_LEADING_GROUP_SIZE:])
        leading_digits = leading_digits[:-_INDIAN_LEADING_GROUP_SIZE]
    return ",".join([*leading_groups, last_group])


def format_paise_as_whole_rupees(amount_in_paise: int) -> str:
    """Gives "₹3,667" for 366667 paise: whole rupees, paise rounded half-up, Indian grouping."""
    if isinstance(amount_in_paise, bool) or not isinstance(amount_in_paise, int):
        raise TypeError("An amount in paise must be an int.")
    whole_rupees = (Decimal(amount_in_paise) / _PAISE_PER_RUPEE).quantize(
        Decimal(1), rounding=ROUND_HALF_UP
    )
    return RUPEE_SYMBOL + group_digits_the_indian_way(int(whole_rupees))
