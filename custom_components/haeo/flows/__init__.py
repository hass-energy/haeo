"""Base classes and utilities for HAEO config flows."""

import logging
from typing import Final

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)
import voluptuous as vol

from custom_components.haeo.const import (
    CONF_DEBOUNCE_SECONDS,
    CONF_HORIZON_PRESET,
    CONF_NAME,
    CONF_TIER_1_DURATION,
    CONF_TIER_1_UNTIL,
    CONF_TIER_2_DURATION,
    CONF_TIER_2_UNTIL,
    CONF_TIER_3_DURATION,
    CONF_TIER_3_UNTIL,
    CONF_TIER_4_DURATION,
    CONF_TIER_4_UNTIL,
    CONF_UPDATE_INTERVAL_MINUTES,
    DEFAULT_DEBOUNCE_SECONDS,
    DEFAULT_TIER_1_DURATION,
    DEFAULT_TIER_1_UNTIL,
    DEFAULT_TIER_2_DURATION,
    DEFAULT_TIER_2_UNTIL,
    DEFAULT_TIER_3_DURATION,
    DEFAULT_TIER_3_UNTIL,
    DEFAULT_TIER_4_DURATION,
    DEFAULT_TIER_4_UNTIL,
    DEFAULT_UPDATE_INTERVAL_MINUTES,
)

_LOGGER = logging.getLogger(__name__)

# Horizon preset options
HORIZON_PRESET_2_DAYS: Final = "2_days"
HORIZON_PRESET_3_DAYS: Final = "3_days"
HORIZON_PRESET_5_DAYS: Final = "5_days"  # Default
HORIZON_PRESET_7_DAYS: Final = "7_days"
HORIZON_PRESET_CUSTOM: Final = "custom"

HORIZON_PRESET_OPTIONS: Final = [
    HORIZON_PRESET_2_DAYS,
    HORIZON_PRESET_3_DAYS,
    HORIZON_PRESET_5_DAYS,
    HORIZON_PRESET_7_DAYS,
    HORIZON_PRESET_CUSTOM,
]

# Preset tier configurations for each horizon option
HORIZON_PRESETS: Final[dict[str, dict[str, int]]] = {
    HORIZON_PRESET_2_DAYS: {
        CONF_TIER_1_DURATION: 1,
        CONF_TIER_1_UNTIL: 5,
        CONF_TIER_2_DURATION: 5,
        CONF_TIER_2_UNTIL: 60,
        CONF_TIER_3_DURATION: 30,
        CONF_TIER_3_UNTIL: 720,  # 12 hours
        CONF_TIER_4_DURATION: 60,
        CONF_TIER_4_UNTIL: 2880,  # 2 days
    },
    HORIZON_PRESET_3_DAYS: {
        CONF_TIER_1_DURATION: DEFAULT_TIER_1_DURATION,
        CONF_TIER_1_UNTIL: DEFAULT_TIER_1_UNTIL,
        CONF_TIER_2_DURATION: DEFAULT_TIER_2_DURATION,
        CONF_TIER_2_UNTIL: DEFAULT_TIER_2_UNTIL,
        CONF_TIER_3_DURATION: DEFAULT_TIER_3_DURATION,
        CONF_TIER_3_UNTIL: DEFAULT_TIER_3_UNTIL,
        CONF_TIER_4_DURATION: DEFAULT_TIER_4_DURATION,
        CONF_TIER_4_UNTIL: DEFAULT_TIER_4_UNTIL,  # 3 days
    },
    HORIZON_PRESET_5_DAYS: {
        CONF_TIER_1_DURATION: 1,
        CONF_TIER_1_UNTIL: 5,
        CONF_TIER_2_DURATION: 5,
        CONF_TIER_2_UNTIL: 60,
        CONF_TIER_3_DURATION: 30,
        CONF_TIER_3_UNTIL: 1440,  # 1 day
        CONF_TIER_4_DURATION: 60,
        CONF_TIER_4_UNTIL: 7200,  # 5 days
    },
    HORIZON_PRESET_7_DAYS: {
        CONF_TIER_1_DURATION: 1,
        CONF_TIER_1_UNTIL: 5,
        CONF_TIER_2_DURATION: 5,
        CONF_TIER_2_UNTIL: 60,
        CONF_TIER_3_DURATION: 30,
        CONF_TIER_3_UNTIL: 1440,  # 1 day
        CONF_TIER_4_DURATION: 60,
        CONF_TIER_4_UNTIL: 10080,  # 7 days
    },
}


def get_hub_setup_schema() -> vol.Schema:
    """Get simplified schema for initial hub setup.

    Returns:
        Voluptuous schema with name, horizon preset, and basic settings.

    """
    return vol.Schema(
        {
            vol.Required(CONF_NAME): vol.All(
                str,
                vol.Strip,
                vol.Length(min=1, msg="Name cannot be empty"),
                vol.Length(max=255, msg="Name cannot be longer than 255 characters"),
            ),
            vol.Required(
                CONF_HORIZON_PRESET, default=HORIZON_PRESET_5_DAYS
            ): SelectSelector(
                SelectSelectorConfig(
                    options=HORIZON_PRESET_OPTIONS,
                    mode=SelectSelectorMode.DROPDOWN,
                    translation_key="horizon_preset",
                )
            ),
            vol.Required(
                CONF_UPDATE_INTERVAL_MINUTES,
                default=DEFAULT_UPDATE_INTERVAL_MINUTES,
            ): vol.All(
                NumberSelector(
                    NumberSelectorConfig(
                        min=1, max=120, step=1, mode=NumberSelectorMode.SLIDER
                    ),
                ),
                vol.Coerce(int),
            ),
            vol.Required(
                CONF_DEBOUNCE_SECONDS,
                default=DEFAULT_DEBOUNCE_SECONDS,
            ): vol.All(
                NumberSelector(
                    NumberSelectorConfig(
                        min=0, max=30, step=1, mode=NumberSelectorMode.SLIDER
                    ),
                ),
                vol.Coerce(int),
            ),
        }
    )


def get_custom_tiers_schema(config_entry: ConfigEntry | None = None) -> vol.Schema:
    """Get schema for custom tier configuration step.

    Args:
        config_entry: Optional config entry to get current values from

    Returns:
        Voluptuous schema with all tier configuration fields.

    """
    return vol.Schema(
        {
            # Tier 1: Fine-grained near-term intervals
            vol.Required(
                CONF_TIER_1_DURATION,
                default=config_entry.data.get(
                    CONF_TIER_1_DURATION, DEFAULT_TIER_1_DURATION
                )
                if config_entry
                else DEFAULT_TIER_1_DURATION,
            ): vol.All(
                NumberSelector(
                    NumberSelectorConfig(
                        min=1, max=60, step=1, mode=NumberSelectorMode.BOX
                    )
                ),
                vol.Coerce(int),
            ),
            vol.Required(
                CONF_TIER_1_UNTIL,
                default=config_entry.data.get(CONF_TIER_1_UNTIL, DEFAULT_TIER_1_UNTIL)
                if config_entry
                else DEFAULT_TIER_1_UNTIL,
            ): vol.All(
                NumberSelector(
                    NumberSelectorConfig(
                        min=1, max=60, step=1, mode=NumberSelectorMode.BOX
                    )
                ),
                vol.Coerce(int),
            ),
            # Tier 2: Short-term intervals
            vol.Required(
                CONF_TIER_2_DURATION,
                default=config_entry.data.get(
                    CONF_TIER_2_DURATION, DEFAULT_TIER_2_DURATION
                )
                if config_entry
                else DEFAULT_TIER_2_DURATION,
            ): vol.All(
                NumberSelector(
                    NumberSelectorConfig(
                        min=1, max=60, step=1, mode=NumberSelectorMode.BOX
                    )
                ),
                vol.Coerce(int),
            ),
            vol.Required(
                CONF_TIER_2_UNTIL,
                default=config_entry.data.get(CONF_TIER_2_UNTIL, DEFAULT_TIER_2_UNTIL)
                if config_entry
                else DEFAULT_TIER_2_UNTIL,
            ): vol.All(
                NumberSelector(
                    NumberSelectorConfig(
                        min=1, max=120, step=1, mode=NumberSelectorMode.BOX
                    )
                ),
                vol.Coerce(int),
            ),
            # Tier 3: Medium-term intervals
            vol.Required(
                CONF_TIER_3_DURATION,
                default=config_entry.data.get(
                    CONF_TIER_3_DURATION, DEFAULT_TIER_3_DURATION
                )
                if config_entry
                else DEFAULT_TIER_3_DURATION,
            ): vol.All(
                NumberSelector(
                    NumberSelectorConfig(
                        min=1, max=120, step=1, mode=NumberSelectorMode.BOX
                    )
                ),
                vol.Coerce(int),
            ),
            vol.Required(
                CONF_TIER_3_UNTIL,
                default=config_entry.data.get(CONF_TIER_3_UNTIL, DEFAULT_TIER_3_UNTIL)
                if config_entry
                else DEFAULT_TIER_3_UNTIL,
            ): vol.All(
                NumberSelector(
                    NumberSelectorConfig(
                        min=1, max=2880, step=1, mode=NumberSelectorMode.BOX
                    )
                ),
                vol.Coerce(int),
            ),
            # Tier 4: Long-term intervals
            vol.Required(
                CONF_TIER_4_DURATION,
                default=config_entry.data.get(
                    CONF_TIER_4_DURATION, DEFAULT_TIER_4_DURATION
                )
                if config_entry
                else DEFAULT_TIER_4_DURATION,
            ): vol.All(
                NumberSelector(
                    NumberSelectorConfig(
                        min=1, max=240, step=1, mode=NumberSelectorMode.BOX
                    )
                ),
                vol.Coerce(int),
            ),
            vol.Required(
                CONF_TIER_4_UNTIL,
                default=config_entry.data.get(CONF_TIER_4_UNTIL, DEFAULT_TIER_4_UNTIL)
                if config_entry
                else DEFAULT_TIER_4_UNTIL,
            ): vol.All(
                NumberSelector(
                    NumberSelectorConfig(
                        min=1, max=10080, step=1, mode=NumberSelectorMode.BOX
                    )
                ),
                vol.Coerce(int),
            ),
        }
    )


def get_hub_options_schema(config_entry: ConfigEntry) -> vol.Schema:
    """Get simplified schema for hub options (edit) flow.

    Args:
        config_entry: Config entry to get current values from

    Returns:
        Voluptuous schema with horizon preset dropdown and basic settings.

    """
    # Get stored preset, defaulting to 5_days if not stored
    current_preset = config_entry.data.get(CONF_HORIZON_PRESET, HORIZON_PRESET_5_DAYS)

    return vol.Schema(
        {
            vol.Required(CONF_HORIZON_PRESET, default=current_preset): SelectSelector(
                SelectSelectorConfig(
                    options=HORIZON_PRESET_OPTIONS,
                    mode=SelectSelectorMode.DROPDOWN,
                    translation_key="horizon_preset",
                )
            ),
            vol.Required(
                CONF_UPDATE_INTERVAL_MINUTES,
                default=config_entry.data.get(
                    CONF_UPDATE_INTERVAL_MINUTES, DEFAULT_UPDATE_INTERVAL_MINUTES
                ),
            ): vol.All(
                NumberSelector(
                    NumberSelectorConfig(
                        min=1, max=120, step=1, mode=NumberSelectorMode.SLIDER
                    ),
                ),
                vol.Coerce(int),
            ),
            vol.Required(
                CONF_DEBOUNCE_SECONDS,
                default=config_entry.data.get(
                    CONF_DEBOUNCE_SECONDS, DEFAULT_DEBOUNCE_SECONDS
                ),
            ): vol.All(
                NumberSelector(
                    NumberSelectorConfig(
                        min=0, max=30, step=1, mode=NumberSelectorMode.SLIDER
                    ),
                ),
                vol.Coerce(int),
            ),
        }
    )


def get_network_config_schema(
    config_entry: ConfigEntry | None = None,
) -> vol.Schema:
    """Get schema for network configuration.

    Args:
        config_entry: Config entry to get current values from

    Returns:
        Voluptuous schema for network configuration

    The configuration uses 4 tiers of intervals with variable durations.
    Each tier specifies interval size (duration) and cumulative end time (until):
    - Tier 1: 1 min slices until 5 min → 5 periods
    - Tier 2: 5 min slices until 60 min → 11 periods
    - Tier 3: 30 min slices until 1 day → 46 periods
    - Tier 4: 60 min slices until 3 days → 48 periods

    Total default: 110 periods covering 72 hours

    """
    return vol.Schema(
        {
            **(
                {
                    vol.Required(CONF_NAME): vol.All(
                        str,
                        vol.Strip,
                        vol.Length(min=1, msg="Name cannot be empty"),
                        vol.Length(
                            max=255, msg="Name cannot be longer than 255 characters"
                        ),
                    ),
                }
                if config_entry is None
                else {}
            ),
            # Tier 1: Fine-grained near-term intervals
            vol.Required(
                CONF_TIER_1_DURATION,
                default=config_entry.data.get(
                    CONF_TIER_1_DURATION, DEFAULT_TIER_1_DURATION
                )
                if config_entry
                else DEFAULT_TIER_1_DURATION,
            ): vol.All(
                NumberSelector(
                    NumberSelectorConfig(
                        min=1, max=60, step=1, mode=NumberSelectorMode.BOX
                    )
                ),
                vol.Coerce(int),
            ),
            vol.Required(
                CONF_TIER_1_UNTIL,
                default=config_entry.data.get(CONF_TIER_1_UNTIL, DEFAULT_TIER_1_UNTIL)
                if config_entry
                else DEFAULT_TIER_1_UNTIL,
            ): vol.All(
                NumberSelector(
                    NumberSelectorConfig(
                        min=1, max=60, step=1, mode=NumberSelectorMode.BOX
                    )
                ),
                vol.Coerce(int),
            ),
            # Tier 2: Short-term intervals
            vol.Required(
                CONF_TIER_2_DURATION,
                default=config_entry.data.get(
                    CONF_TIER_2_DURATION, DEFAULT_TIER_2_DURATION
                )
                if config_entry
                else DEFAULT_TIER_2_DURATION,
            ): vol.All(
                NumberSelector(
                    NumberSelectorConfig(
                        min=1, max=60, step=1, mode=NumberSelectorMode.BOX
                    )
                ),
                vol.Coerce(int),
            ),
            vol.Required(
                CONF_TIER_2_UNTIL,
                default=config_entry.data.get(CONF_TIER_2_UNTIL, DEFAULT_TIER_2_UNTIL)
                if config_entry
                else DEFAULT_TIER_2_UNTIL,
            ): vol.All(
                NumberSelector(
                    NumberSelectorConfig(
                        min=1, max=120, step=1, mode=NumberSelectorMode.BOX
                    )
                ),
                vol.Coerce(int),
            ),
            # Tier 3: Medium-term intervals
            vol.Required(
                CONF_TIER_3_DURATION,
                default=config_entry.data.get(
                    CONF_TIER_3_DURATION, DEFAULT_TIER_3_DURATION
                )
                if config_entry
                else DEFAULT_TIER_3_DURATION,
            ): vol.All(
                NumberSelector(
                    NumberSelectorConfig(
                        min=1, max=120, step=1, mode=NumberSelectorMode.BOX
                    )
                ),
                vol.Coerce(int),
            ),
            vol.Required(
                CONF_TIER_3_UNTIL,
                default=config_entry.data.get(CONF_TIER_3_UNTIL, DEFAULT_TIER_3_UNTIL)
                if config_entry
                else DEFAULT_TIER_3_UNTIL,
            ): vol.All(
                NumberSelector(
                    NumberSelectorConfig(
                        min=1, max=2880, step=1, mode=NumberSelectorMode.BOX
                    )
                ),
                vol.Coerce(int),
            ),
            # Tier 4: Long-term intervals
            vol.Required(
                CONF_TIER_4_DURATION,
                default=config_entry.data.get(
                    CONF_TIER_4_DURATION, DEFAULT_TIER_4_DURATION
                )
                if config_entry
                else DEFAULT_TIER_4_DURATION,
            ): vol.All(
                NumberSelector(
                    NumberSelectorConfig(
                        min=1, max=240, step=1, mode=NumberSelectorMode.BOX
                    )
                ),
                vol.Coerce(int),
            ),
            vol.Required(
                CONF_TIER_4_UNTIL,
                default=config_entry.data.get(CONF_TIER_4_UNTIL, DEFAULT_TIER_4_UNTIL)
                if config_entry
                else DEFAULT_TIER_4_UNTIL,
            ): vol.All(
                NumberSelector(
                    NumberSelectorConfig(
                        min=1, max=10080, step=1, mode=NumberSelectorMode.BOX
                    )
                ),
                vol.Coerce(int),
            ),
            # Update and debounce settings
            vol.Required(
                CONF_UPDATE_INTERVAL_MINUTES,
                default=config_entry.data.get(
                    CONF_UPDATE_INTERVAL_MINUTES, DEFAULT_UPDATE_INTERVAL_MINUTES
                )
                if config_entry
                else DEFAULT_UPDATE_INTERVAL_MINUTES,
            ): vol.All(
                NumberSelector(
                    NumberSelectorConfig(
                        min=1, max=120, step=1, mode=NumberSelectorMode.SLIDER
                    ),
                ),
                vol.Coerce(int),
            ),
            vol.Required(
                CONF_DEBOUNCE_SECONDS,
                default=config_entry.data.get(
                    CONF_DEBOUNCE_SECONDS, DEFAULT_DEBOUNCE_SECONDS
                )
                if config_entry
                else DEFAULT_DEBOUNCE_SECONDS,
            ): vol.All(
                NumberSelector(
                    NumberSelectorConfig(
                        min=0, max=30, step=1, mode=NumberSelectorMode.SLIDER
                    ),
                ),
                vol.Coerce(int),
            ),
        }
    )
