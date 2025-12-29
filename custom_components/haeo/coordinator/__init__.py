"""Coordinator modules for HAEO integration.

This package contains:
- ElementInputCoordinator: Per-subentry coordinator for input entity values
- HaeoDataUpdateCoordinator: Network-level coordinator for optimization
"""

from custom_components.haeo.coordinator.element_coordinator import ElementInputCoordinator, ElementInputData

__all__ = [
    "ElementInputCoordinator",
    "ElementInputData",
]
