"""Entities for HAEO element configuration and outputs.

This module provides:
- HaeoSensor: Sensor entity for optimization outputs
- HaeoInputNumber: Number entity for configurable parameters
- HaeoInputSwitch: Switch entity for boolean parameters
- HaeoHorizonEntity: Sensor providing forecast time windows

Note: Device creation utilities are in entities.device module.
Import directly from that module to avoid circular imports:
    from custom_components.haeo.entities.device import get_or_create_element_device
"""

from .haeo_horizon import HaeoHorizonEntity
from .haeo_number import ConfigEntityMode, HaeoInputNumber
from .haeo_sensor import HaeoSensor
from .haeo_switch import HaeoInputSwitch

__all__ = [
    "ConfigEntityMode",
    "HaeoHorizonEntity",
    "HaeoInputNumber",
    "HaeoInputSwitch",
    "HaeoSensor",
]
