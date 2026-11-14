"""Declarative base whose naming convention gives every constraint and index a stable name."""

from collections.abc import Iterable
from enum import StrEnum

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# Stable names let migrations drop or alter a constraint by name and keep autogenerate diffs clean.
NAMING_CONVENTION = {
    "pk": "pk_%(table_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
}


class Base(DeclarativeBase):
    """Parent of every ORM table class; carries the shared metadata and naming convention."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def sql_value_list(enumeration: type[StrEnum]) -> str:
    """Renders an enum's stored values as a SQL IN list, for CHECK constraints on status columns."""
    return ", ".join(f"'{member.value}'" for member in enumeration)


def sql_member_list(members: Iterable[StrEnum]) -> str:
    """Renders some enum members' stored values as a sorted SQL IN list, so the text is stable."""
    return ", ".join(f"'{member.value}'" for member in sorted(members))
