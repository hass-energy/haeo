"""Optimization context for capturing inputs at optimization time."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime

from custom_components.haeo.core.schema.elements import HaeoConfigEntryDict
from custom_components.haeo.core.state import EntityState


@dataclass(frozen=True, slots=True)
class OptimizationContext:
    """Immutable snapshot of all inputs at optimization time.

    Captures the typed config-entry snapshot (hub data + subentries) plus the
    sensor states and horizon timing used by the optimization run, so that the
    run is fully reproducible from the context alone.
    """

    config: HaeoConfigEntryDict
    """Typed snapshot of entry.as_dict() (HA bookkeeping blocklisted)."""

    horizon_start: datetime
    """Horizon start time used for period alignment."""

    source_states: Mapping[str, EntityState]
    """Source sensor states captured when entities loaded data."""


__all__ = ["OptimizationContext"]
