"""Coordinator module for HAEO integration."""

from custom_components.haeo.core.context import OptimizationContext

from .coordinator import (
    STATUS_OPTIONS,
    CoordinatorData,
    CoordinatorOutput,
    ForecastPoint,
    HaeoDataUpdateCoordinator,
    _build_coordinator_output,  # pyright: ignore[reportPrivateUsage] (exported for testing)
    _build_optimization_context,  # pyright: ignore[reportPrivateUsage] (exported for testing)
)
from .network import create_network, evaluate_network_connectivity, update_element

__all__ = [
    "STATUS_OPTIONS",
    "CoordinatorData",
    "CoordinatorOutput",
    "ForecastPoint",
    "HaeoDataUpdateCoordinator",
    "OptimizationContext",
    "_build_coordinator_output",
    "_build_optimization_context",
    "create_network",
    "evaluate_network_connectivity",
    "update_element",
]
