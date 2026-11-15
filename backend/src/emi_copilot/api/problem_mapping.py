"""ProblemMapping: how one typed error class is answered as application/problem+json."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProblemMapping:
    """How one error class is answered: its HTTP status and a short English title."""

    status: int
    title: str
