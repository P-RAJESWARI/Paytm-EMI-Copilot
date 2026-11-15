"""Deterministic reading of what the customer said; no AI model ever decides a number here."""

from emi_copilot.domain.speech.spoken_amount_parser import SpokenAmountParser

__all__ = ["SpokenAmountParser"]
