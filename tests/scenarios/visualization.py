"""Visualization utilities for HAEO scenario test results.

This module provides functions to create stacked area and line plots
showing production and consumption values over time for optimization results.

This is a compatibility shim that imports from the new modular visualization package.
"""

# Import everything from the new modular structure
from tests.scenarios.visualisation import (
    create_shadow_price_visualization,
    create_stacked_visualization,
    visualize_scenario_results,
)

__all__ = [
    "create_shadow_price_visualization",
    "create_stacked_visualization",
    "visualize_scenario_results",
]
