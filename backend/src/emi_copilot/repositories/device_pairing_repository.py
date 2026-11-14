"""Stores and finds paired devices by their token hash; the token itself is never stored."""

from datetime import UTC

from sqlalchemy import select
from sqlalchemy.orm import Session

from emi_copilot.core.clock import Clock
from emi_copilot.domain.merchants import DevicePairing
from emi_copilot.models import DevicePairingModel


def _to_domain(device_pairing_model: DevicePairingModel) -> DevicePairing:
    """Maps an ORM row back to a validated domain entity; timestamps are returned in UTC."""
    revoked_at = device_pairing_model.revoked_at
    return DevicePairing(
        id=device_pairing_model.id,
        merchant_id=device_pairing_model.merchant_id,
        device_label=device_pairing_model.device_label,
        access_token_hash=device_pairing_model.access_token_hash,
        expires_at=device_pairing_model.expires_at.astimezone(UTC),
        revoked_at=None if revoked_at is None else revoked_at.astimezone(UTC),
    )


# Pattern: Repository. Keeps every device_pairing query out of services; no rules here.
class DevicePairingRepository:
    """Adds device pairings and finds one by its access token hash."""

    def __init__(self, session: Session, clock: Clock) -> None:
        """Uses the unit of work's session and the injected clock for created_at and updated_at."""
        self._session = session
        self._clock = clock

    def add(self, device_pairing: DevicePairing) -> None:
        """Inserts a new pairing now; a duplicate token hash fails on the unique constraint."""
        now = self._clock.now()
        self._session.add(
            DevicePairingModel(
                id=device_pairing.id,
                merchant_id=device_pairing.merchant_id,
                device_label=device_pairing.device_label,
                access_token_hash=device_pairing.access_token_hash,
                expires_at=device_pairing.expires_at,
                revoked_at=device_pairing.revoked_at,
                created_at=now,
                updated_at=now,
            )
        )
        self._session.flush()

    def find_by_access_token_hash(self, access_token_hash: str) -> DevicePairing | None:
        """Returns the pairing whose token hashes to this value, or None; usable or not."""
        device_pairing_model = self._session.scalars(
            select(DevicePairingModel).where(
                DevicePairingModel.access_token_hash == access_token_hash
            )
        ).one_or_none()
        return None if device_pairing_model is None else _to_domain(device_pairing_model)
