"""An IdGenerator test double that issues predictable, unique 26-character ids."""

ID_LENGTH = 26


class SequentialIdGenerator:
    """Gives PREFIX0000...1, PREFIX0000...2: as long as a ULID, so every id column accepts it."""

    def __init__(self, prefix: str = "01JCTESTID") -> None:
        """Starts counting at zero under a prefix shorter than the id length."""
        self._prefix = prefix
        self._issued_count = 0

    def new_id(self) -> str:
        """Returns the next numbered id."""
        self._issued_count += 1
        return f"{self._prefix}{self._issued_count:0{ID_LENGTH - len(self._prefix)}d}"
