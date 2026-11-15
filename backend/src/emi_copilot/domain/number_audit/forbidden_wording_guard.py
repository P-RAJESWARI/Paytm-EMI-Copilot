"""ForbiddenWordingGuard: finds words AI text must never use on a customer or merchant screen."""

import re
import unicodedata

# Why each group is forbidden (CLAUDE.md section 2, security-and-compliance.md sections 6 to 8):
# - credit-decision words: the comfort check is advice and the lender decides credit (rule 5);
# - rate words: screens say "extra you pay", never an interest rate (rule 7);
# - "best" and urgency words: no plan is pushed and nobody is hurried (rule 7);
# - band words: bands are shown by the deterministic engine only, and the AI never sees the band
#   or ratio (plan Q3), so a band word in AI text is invented.
# English phrases match whole words, ignoring case.
FORBIDDEN_ENGLISH_PHRASES = (
    "approved", "approve", "approval", "declined", "decline", "rejected", "reject",
    "eligible", "eligibility", "interest rate", "rate of interest", "best for you", "best plan",
    "recommended", "hurry", "act now", "limited time", "last chance", "today only",
    "comfortable", "stretching", "risky",
)  # fmt: skip
# Tamil text has no reliable word boundaries in regular expressions, so these match anywhere.
# The band labels are the customer app's Tamil labels (shared-i18n sharedTranslations.ts).
# draft: needs native review (every Tamil phrase)
FORBIDDEN_TAMIL_PHRASES = (
    "வசதியானது", "கொஞ்சம் சிரமம்", "அதிக சுமை", "வட்டி விகிதம்", "உங்களுக்குச் சிறந்த",
    "சிறந்த திட்டம்",
)  # fmt: skip

_WHITESPACE_RUN = r"\s+"


def _english_phrase_pattern(phrase: str) -> str:
    """Gives a whole-word pattern for a phrase, allowing any whitespace between its words."""
    return r"(?<![a-z])" + _WHITESPACE_RUN.join(map(re.escape, phrase.split())) + r"(?![a-z])"


def _tamil_phrase_pattern(phrase: str) -> str:
    """Gives a pattern for a canonically composed Tamil phrase, with flexible whitespace."""
    words = unicodedata.normalize("NFC", phrase).split()
    return _WHITESPACE_RUN.join(map(re.escape, words))


FORBIDDEN_WORDING_PATTERN = re.compile(
    "|".join(
        [
            *(_english_phrase_pattern(phrase) for phrase in FORBIDDEN_ENGLISH_PHRASES),
            *(_tamil_phrase_pattern(phrase) for phrase in FORBIDDEN_TAMIL_PHRASES),
        ]
    ),
    re.IGNORECASE,
)


class ForbiddenWordingGuard:
    """Lists the forbidden phrases a text contains, as written, in reading order."""

    def find_forbidden_phrases(self, text: str) -> tuple[str, ...]:
        """Gives each forbidden phrase found after NFKC; empty when the wording is allowed."""
        searchable_text = unicodedata.normalize("NFKC", text)
        return tuple(match.group() for match in FORBIDDEN_WORDING_PATTERN.finditer(searchable_text))
