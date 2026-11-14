"""Funnel types: the stages a sale can reach and the append-only record of reaching one."""

from emi_copilot.domain.funnel.funnel_event import FunnelEvent
from emi_copilot.domain.funnel.funnel_stage import FunnelStage

__all__ = ["FunnelEvent", "FunnelStage"]
