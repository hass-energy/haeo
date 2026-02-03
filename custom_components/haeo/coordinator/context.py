"""Optimization context for capturing inputs at optimization time."""

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
from typing import TYPE_CHECKING, Self, cast

from homeassistant.core import State

from custom_components.haeo.elements import ElementConfigSchema, InputFieldPath

if TYPE_CHECKING:
    from custom_components.haeo.entities.haeo_number import HaeoInputNumber
    from custom_components.haeo.entities.haeo_switch import HaeoInputSwitch
    from custom_components.haeo.horizon import HorizonManager


@dataclass(frozen=True, slots=True)
class OptimizationContext:
    """Immutable snapshot of all inputs at optimization time.

    This class captures all inputs needed to reproduce an optimization run:
    - Element configurations (raw schemas, not processed data)
    - Source sensor states captured when entities loaded data
    - Forecast timestamps from horizon manager

    The context is built at the start of each optimization run and stored
    in CoordinatorData for diagnostics and reproducibility.
    """

    participants: dict[str, ElementConfigSchema]
    """Raw element schemas (not processed ElementConfigData)."""

    source_states: dict[str, State]
    """Source sensor states captured when entities loaded data."""

    forecast_timestamps: tuple[float, ...]
    """Forecast timestamps from horizon manager."""

    @classmethod
    def build(
        cls,
        participant_configs: Mapping[str, ElementConfigSchema],
        input_entities: Mapping[tuple[str, InputFieldPath], "HaeoInputNumber | HaeoInputSwitch"],
        horizon_manager: "HorizonManager",
    ) -> Self:
        """Build context by pulling from existing sources.

        Called at start of _async_update_data() before optimization runs.

        Args:
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

        return cls(
            participants=_deep_copy_config(participant_configs),
            source_states=source_states,
            forecast_timestamps=horizon_manager.get_forecast_timestamps(),
        )


def _deep_copy_config(configs: Mapping[str, ElementConfigSchema]) -> dict[str, ElementConfigSchema]:
    """Deep copy participant configs for immutable storage.

    Home Assistant config entries wrap data in MappingProxyType which can't be
    deepcopied directly. Converting to dict first (like HA does internally)
    allows deepcopy to work.
    """
    return {name: cast("ElementConfigSchema", deepcopy(dict(config))) for name, config in configs.items()}


__all__ = ["OptimizationContext"]
