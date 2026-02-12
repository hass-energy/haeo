"""Optimization context for capturing inputs at optimization time."""

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any, Self, cast

from homeassistant.core import State
from homeassistant.util import dt as dt_util

from custom_components.haeo.elements import ElementConfigSchema, InputFieldPath

if TYPE_CHECKING:
    from custom_components.haeo import InputEntity
    from custom_components.haeo.horizon import HorizonManager


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

    source_states: Mapping[str, State]
    """Source sensor states captured when entities loaded data."""

    @classmethod
    def build(
        cls,
        hub_config: Mapping[str, Any],
        participant_configs: Mapping[str, ElementConfigSchema],
        input_entities: Mapping[tuple[str, InputFieldPath], "InputEntity"],
        horizon_manager: "HorizonManager",
    ) -> Self:
        """Build context by pulling from existing sources.

        Called at start of _async_update_data() before optimization runs.

        Args:
            hub_config: Config entry data used for horizon calculation
            participant_configs: Coordinator's _participant_configs dict
            input_entities: runtime_data.input_entities dict
            horizon_manager: runtime_data.horizon_manager

        Returns:
            Immutable OptimizationContext with all inputs captured.

        """
        # Pull source states from all input entities (they captured these when loading data)
        source_states: dict[str, State] = {}
        for entity in input_entities.values():
            source_states.update(entity.get_captured_source_states())

        start_time = horizon_manager.current_start_time
        if start_time is None:
            start_time = dt_util.utcnow()

        return cls(
            hub_config=deepcopy(dict(hub_config)),
            horizon_start=start_time,
            participants=_deep_copy_config(participant_configs),
            source_states=source_states,
        )


def _deep_copy_config(configs: Mapping[str, ElementConfigSchema]) -> dict[str, ElementConfigSchema]:
    """Deep copy participant configs for immutable storage.

    Home Assistant config entries wrap data in MappingProxyType which can't be
    deepcopied directly. Converting to dict first (like HA does internally)
    allows deepcopy to work.
    """
    return {name: cast("ElementConfigSchema", deepcopy(dict(config))) for name, config in configs.items()}


__all__ = ["OptimizationContext"]
