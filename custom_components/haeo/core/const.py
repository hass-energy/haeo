"""Constants for the HAEO core module."""

import enum
from typing import Final

CONF_ELEMENT_TYPE: Final = "element_type"
CONF_NAME: Final = "name"

# Hub configuration keys
CONF_DEBOUNCE_SECONDS: Final = "debounce_seconds"
CONF_HORIZON_PRESET: Final = "horizon_preset"
CONF_ADVANCED_MODE: Final = "advanced_mode"

# Interval tier configuration
CONF_TIER_1_COUNT: Final = "tier_1_count"
CONF_TIER_1_DURATION: Final = "tier_1_duration"
CONF_TIER_2_COUNT: Final = "tier_2_count"
CONF_TIER_2_DURATION: Final = "tier_2_duration"
CONF_TIER_3_COUNT: Final = "tier_3_count"
CONF_TIER_3_DURATION: Final = "tier_3_duration"
CONF_TIER_4_COUNT: Final = "tier_4_count"
CONF_TIER_4_DURATION: Final = "tier_4_duration"

# Default tier values
DEFAULT_TIER_1_COUNT: Final = 5
DEFAULT_TIER_1_DURATION: Final = 1
DEFAULT_TIER_2_COUNT: Final = 11
DEFAULT_TIER_2_DURATION: Final = 5
DEFAULT_TIER_3_COUNT: Final = 46
DEFAULT_TIER_3_DURATION: Final = 30
DEFAULT_TIER_4_COUNT: Final = 48
DEFAULT_TIER_4_DURATION: Final = 60

DEFAULT_DEBOUNCE_SECONDS: Final = 2

# Hub section keys
HUB_SECTION_COMMON: Final = "common"
HUB_SECTION_ADVANCED: Final = "advanced"
HUB_SECTION_TIERS: Final = "tiers"

# Horizon presets
HORIZON_PRESET_5_DAYS: Final = "5_days"


class ConnectivityLevel(enum.StrEnum):
    """Connectivity level for element types in connection selectors.

    - ALWAYS: Always shown in connection selectors
    - ADVANCED: Only shown when advanced mode is enabled
    - NEVER: Never shown in connection selectors
    """

    ALWAYS = enum.auto()
    ADVANCED = enum.auto()
    NEVER = enum.auto()
