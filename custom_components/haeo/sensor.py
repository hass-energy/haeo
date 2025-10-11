"""Sensor platform for Home Assistant Energy Optimization integration.

This module serves as the entry point for the sensor platform, re-exporting
functionality from the sensors package.
"""

# Re-export the setup function for Home Assistant
from custom_components.haeo.sensors import async_setup_entry as async_setup_entry
