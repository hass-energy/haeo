"""Optimization context for capturing inputs at optimization time."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from custom_components.haeo.core.schema.elements import ElementConfigSchema
from custom_components.haeo.core.state import EntityState


@dataclass(frozen=True, slots=True)
class OptimizationContext:
    """Immutable snapshot of all inputs at optimization time.

    This class captures all inputs needed to reproduce an optimization run:
    - Element configurations (raw schemas, not processed data)
    - Source sensor states captured when entities loaded data
    - Horizon reference time used for period alignment

    The context is built at the start of each optimization run and stored
    in CoordinatorData for diagnostics and reproducibility.
    """

    hub_config: Mapping[str, Any]
    """Hub configuration used to derive periods and timestamps."""

    horizon_start: datetime
    """Horizon start time used for period alignment."""

    participants: dict[str, ElementConfigSchema]
    """Raw element schemas (not processed ElementConfigData)."""

    source_states: Mapping[str, EntityState]
    """Source sensor states captured when entities loaded data."""


__all__ = ["OptimizationContext"]
