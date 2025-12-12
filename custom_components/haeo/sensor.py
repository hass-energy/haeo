"""Sensor platform for Home Assistant Energy Optimizer integration.

This module serves as the entry point for the sensor platform, re-exporting
functionality from the sensors package.
"""

from custom_components.haeo.sensors import async_setup_entry

# Sensors are read-only and use coordinator, so unlimited parallel updates is safe
PARALLEL_UPDATES = 0

__all__ = ["async_setup_entry"]
