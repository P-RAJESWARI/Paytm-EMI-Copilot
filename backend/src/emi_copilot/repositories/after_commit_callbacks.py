"""AfterCommitCallbacks: work a transaction queues for the moment it has really committed.

The live sale feed uses it, so a shop never hears about a change that is later rolled back.
"""

import logging

from emi_copilot.repositories.unit_of_work_protocol import AfterCommitCallback

after_commit_logger = logging.getLogger(__name__)


class AfterCommitCallbacks:
    """Callbacks queued during one transaction, run once and in order only after it commits.

    A rollback discards them unrun. A failing callback is logged by its error type only (never
    its message, which could carry a payload or token) and never undoes or fails the committed
    request: the data is safe, and only a notification about it was lost.
    """

    def __init__(self) -> None:
        """Starts with nothing queued."""
        self._callbacks: list[AfterCommitCallback] = []

    def add(self, callback: AfterCommitCallback) -> None:
        """Queues one callback behind those already queued."""
        self._callbacks.append(callback)

    def discard_all(self) -> None:
        """Drops every queued callback unrun, as a rollback must."""
        self._callbacks = []

    def run_all(self) -> None:
        """Runs the queued callbacks in order and clears them; a failure is logged, the rest run."""
        callbacks, self._callbacks = self._callbacks, []
        for callback in callbacks:
            try:
                callback()
            except Exception as callback_error:  # noqa: BLE001 - the commit already happened
                # No traceback: an error's message or locals could hold a payload or a token.
                after_commit_logger.error(  # noqa: TRY400
                    "after-commit callback failed",
                    extra={"error_type": type(callback_error).__name__},
                )
