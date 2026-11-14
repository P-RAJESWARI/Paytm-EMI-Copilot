"""Runs the project's Alembic migrations on a connection the integration tests already hold."""

from pathlib import Path

from alembic.config import Config
from sqlalchemy import Connection

ALEMBIC_INI_PATH = Path(__file__).resolve().parents[2] / "alembic.ini"


def build_alembic_config(connection: Connection) -> Config:
    """Builds the project's Alembic config set to migrate an already-open connection."""
    alembic_config = Config(str(ALEMBIC_INI_PATH))
    alembic_config.attributes["connection"] = connection
    return alembic_config
