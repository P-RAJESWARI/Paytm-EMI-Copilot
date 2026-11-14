"""Response schema for the liveness check."""

from typing import Literal

from pydantic import BaseModel, ConfigDict


class HealthResponse(BaseModel):
    """Body returned by GET /health while the process is able to serve requests."""

    model_config = ConfigDict(frozen=True)

    status: Literal["ok"]
