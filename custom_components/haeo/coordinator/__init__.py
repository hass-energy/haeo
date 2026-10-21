"""Coordinator module for HAEO integration."""

from custom_components.haeo.core.context import OptimizationContext

from .coordinator import (
    STATUS_OPTIONS,
    CoordinatorData,
    CoordinatorOutput,
    ForecastPoint,
    HaeoDataUpdateCoordinator,
    SubentryDevices,
    _build_coordinator_output,  # pyright: ignore[reportPrivateUsage] (exported for testing)
    _build_optimization_context,  # pyright: ignore[reportPrivateUsage] (exported for testing)
    check_price_currencies,
    detect_currency_symbol,
    forecast_datetimes,
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
    "SubentryDevices",
    "_build_coordinator_output",
    "_build_optimization_context",
    "check_price_currencies",
    "create_network",
    "detect_currency_symbol",
    "evaluate_network_connectivity",
    "forecast_datetimes",
]
