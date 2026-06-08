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
    _localize_currency,  # pyright: ignore[reportPrivateUsage] (exported for testing)
    detect_currency_symbol,
)
from .network import ElementUpdater, create_network, evaluate_network_connectivity

__all__ = [
    "STATUS_OPTIONS",
    "CoordinatorData",
    "CoordinatorOutput",
    "ElementUpdater",
    "ForecastPoint",
    "HaeoDataUpdateCoordinator",
    "OptimizationContext",
    "_build_coordinator_output",
    "_build_optimization_context",
    "_localize_currency",
    "create_network",
    "detect_currency_symbol",
    "evaluate_network_connectivity",
]
