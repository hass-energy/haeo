"""Config entities module for HAEO integration.

This module provides number and switch entities for configurable element fields.
These entities allow runtime adjustment of element parameters through the Home Assistant UI.
"""

from .mode import ConfigEntityMode
from .number import HaeoConfigNumber
from .resolver import (
    get_config_entity_id,
    get_config_entity_unique_id,
    is_config_entity_enabled,
    is_input_required,
    resolve_config_entity_mode,
    resolve_entity_to_load,
)
from .switch import HaeoConfigSwitch

__all__ = [
    "ConfigEntityMode",
    "HaeoConfigNumber",
    "HaeoConfigSwitch",
    "get_config_entity_id",
    "get_config_entity_unique_id",
    "is_config_entity_enabled",
    "is_input_required",
    "resolve_config_entity_mode",
    "resolve_entity_to_load",
]
