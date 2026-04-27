"""Visualization utilities for HAEO scenario test results.

This is a compatibility shim that imports from the new modular visualization package.
"""

from tests.scenarios.visualisation import create_shadow_price_visualization, visualize_scenario_results

__all__ = [
    "create_shadow_price_visualization",
    "visualize_scenario_results",
]
