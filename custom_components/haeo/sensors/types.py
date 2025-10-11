"""Type definitions for HAEO sensors."""

from enum import Enum


class DataSource(Enum):
    """Data source types for sensors."""

    OPTIMIZED = "optimized"  # From optimization results (element_data)
    FORECAST = "forecast"  # From element forecast attribute
    ELEMENT_ATTRIBUTE = "element_attribute"  # Direct from element attribute
