"""Optimization context for capturing inputs at optimization time."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Self

from homeassistant.core import State

if TYPE_CHECKING:
    from custom_components.haeo.elements import ElementConfigSchema
    from custom_components.haeo.entities.haeo_number import HaeoInputNumber
    from custom_components.haeo.entities.haeo_switch import HaeoInputSwitch
    from custom_components.haeo.horizon import HorizonManager


def _deep_copy_config(obj: Any) -> Any:
    """Deep copy a config structure, handling MappingProxyType.

    MappingProxyType (used by Home Assistant config entries) cannot be
    pickled, so we convert them to regular dicts during copy.
    """
    if isinstance(obj, (MappingProxyType, dict)):
        return {k: _deep_copy_config(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_deep_copy_config(item) for item in obj]
    if isinstance(obj, tuple):
        return tuple(_deep_copy_config(item) for item in obj)
    # Primitives and other immutable types (str, int, float, bool, None) are returned as-is
    return obj


@dataclass(frozen=True, slots=True)
class OptimizationContext:
    """Immutable snapshot of all inputs at optimization time.

    This class captures all inputs needed to reproduce an optimization run:
    - Element configurations (raw schemas, not processed data)
    - Source sensor states captured when entities loaded data
    - Forecast timestamps from horizon manager

    The context is built at the start of each optimization run and stored
    in CoordinatorData for diagnostics reproducibility.
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
        input_entities: Mapping[tuple[str, str], HaeoInputNumber | HaeoInputSwitch],
        horizon_manager: HorizonManager,
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
            source_states=dict(source_states),  # Shallow copy - State objects are effectively immutable
            forecast_timestamps=horizon_manager.get_forecast_timestamps(),
        )


class OptimizationContextBuilder:
    """Tracks element changes and builds optimization context.

    This builder maintains a set of elements that have changed since the last
    optimization run. The coordinator uses this to:
    1. Update only stale elements in the network (via get_stale_elements())
    2. Build the immutable OptimizationContext (via build())

    The build() method clears the stale tracking, so each optimization run
    starts fresh.
    """

    def __init__(self, participant_configs: Mapping[str, ElementConfigSchema]) -> None:
        """Initialize the builder with participant configurations.

        Args:
            participant_configs: Element schemas keyed by element name.

        """
        self._participant_configs = participant_configs
        self._stale_elements: set[str] = set()

    def mark_stale(self, element_name: str) -> None:
        """Mark an element as changed since last optimization.

        Args:
            element_name: Name of the element that has changed.

        """
        self._stale_elements.add(element_name)

    def get_stale_elements(self) -> frozenset[str]:
        """Return elements that have changed since last build.

        Returns:
            Immutable set of element names needing network update.

        """
        return frozenset(self._stale_elements)

    def build(
        self,
        input_entities: Mapping[tuple[str, str], HaeoInputNumber | HaeoInputSwitch],
        horizon_manager: HorizonManager,
    ) -> OptimizationContext:
        """Build immutable context and clear stale tracking.

        Pure operation - no side effects on network.
        Caller should update network for stale elements before calling build().

        Args:
            input_entities: runtime_data.input_entities dict
            horizon_manager: runtime_data.horizon_manager

        Returns:
            Immutable OptimizationContext with all inputs captured.

        """
        self._stale_elements.clear()

        # Pull source states from all input entities
        source_states: dict[str, State] = {}
        for entity in input_entities.values():
            source_states.update(entity.get_captured_source_states())

        return OptimizationContext(
            participants=_deep_copy_config(self._participant_configs),
            source_states=source_states,
            forecast_timestamps=horizon_manager.get_forecast_timestamps(),
        )


__all__ = ["OptimizationContext", "OptimizationContextBuilder"]
