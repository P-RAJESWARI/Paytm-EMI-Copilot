"""Shared fixtures for every test level."""

import logging
from collections.abc import Iterator

import pytest

from emi_copilot.core.logging import (
    HTTP_CLIENT_LOGGER_NAMES,
    UVICORN_ACCESS_LOGGER_NAME,
    UVICORN_LOGGER_NAMES,
)


@pytest.fixture(autouse=True)
def restore_global_logging_configuration() -> Iterator[None]:
    """Undoes any logging setup a test performs so tests never leak handlers into each other."""
    root_logger = logging.getLogger()
    original_root_handlers = list(root_logger.handlers)
    original_root_level = root_logger.level
    original_uvicorn_state = {
        logger_name: (
            list(logging.getLogger(logger_name).handlers),
            logging.getLogger(logger_name).propagate,
        )
        for logger_name in (*UVICORN_LOGGER_NAMES, UVICORN_ACCESS_LOGGER_NAME)
    }
    original_http_client_levels = {
        logger_name: logging.getLogger(logger_name).level
        for logger_name in HTTP_CLIENT_LOGGER_NAMES
    }
    yield
    root_logger.handlers[:] = original_root_handlers
    root_logger.setLevel(original_root_level)
    for logger_name, (handlers, propagate) in original_uvicorn_state.items():
        logging.getLogger(logger_name).handlers[:] = handlers
        logging.getLogger(logger_name).propagate = propagate
    for logger_name, level in original_http_client_levels.items():
        logging.getLogger(logger_name).setLevel(level)
