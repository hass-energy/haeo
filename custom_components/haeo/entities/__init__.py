"""Entities for HAEO element configuration and outputs.

This module provides:
- HaeoSensor: Sensor entity for optimization outputs
- HaeoInputNumber: Number entity for configurable parameters
- HaeoInputSwitch: Switch entity for boolean parameters
- HaeoHorizonEntity: Sensor providing forecast time windows
- AutoOptimizeSwitch: Switch entity for auto-optimization control
"""

from .auto_optimize_switch import AutoOptimizeSwitch
from .haeo_horizon import HaeoHorizonEntity
from .haeo_number import ConfigEntityMode, HaeoInputNumber
from .haeo_sensor import HaeoSensor
from .haeo_switch import HaeoInputSwitch

__all__ = [
    "AutoOptimizeSwitch",
    "ConfigEntityMode",
    "HaeoHorizonEntity",
    "HaeoInputNumber",
    "HaeoInputSwitch",
    "HaeoSensor",
]
