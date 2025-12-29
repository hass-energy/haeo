"""Coordinator modules for HAEO integration.

This package contains:
- ElementInputCoordinator: Per-subentry coordinator for input entity values
- HaeoDataUpdateCoordinator: Network-level coordinator for optimization
"""

from custom_components.haeo.coordinator.element_coordinator import ElementInputCoordinator, ElementInputData
from custom_components.haeo.coordinator.network_coordinator import (
    CoordinatorData,
    CoordinatorOutput,
    ForecastPoint,
    HaeoDataUpdateCoordinator,
    collect_entity_ids,
    extract_entity_ids_from_config,
)

__all__ = [
    "CoordinatorData",
    "CoordinatorOutput",
    "ElementInputCoordinator",
    "ElementInputData",
    "ForecastPoint",
    "HaeoDataUpdateCoordinator",
    "collect_entity_ids",
    "extract_entity_ids_from_config",
]
