"""Input entities for HAEO element configuration.

This module provides number and switch entities that represent configurable
input parameters for HAEO elements. These entities serve as an intermediate
layer between external sensors and the optimization model.
"""

from .haeo_number import ConfigEntityMode, HaeoInputNumber
from .haeo_switch import HaeoInputSwitch

__all__ = [
    "ConfigEntityMode",
    "HaeoInputNumber",
    "HaeoInputSwitch",
]
