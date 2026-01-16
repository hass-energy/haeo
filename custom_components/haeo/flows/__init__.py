"""Base classes and utilities for HAEO config flows."""

import logging
from typing import Any, Final

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.selector import NumberSelector, NumberSelectorConfig, NumberSelectorMode
import voluptuous as vol

from custom_components.haeo.const import (
    CONF_ADVANCED_MODE,
    CONF_DEBOUNCE_SECONDS,
    CONF_HORIZON_DURATION_MINUTES,
    CONF_NAME,
    CONF_TIER_1_COUNT,
    CONF_TIER_1_DURATION,
    CONF_TIER_2_COUNT,
    CONF_TIER_2_DURATION,
    CONF_TIER_3_COUNT,
    CONF_TIER_3_DURATION,
    CONF_TIER_4_DURATION,
    CONF_UPDATE_INTERVAL_MINUTES,
    DEFAULT_DEBOUNCE_SECONDS,
    DEFAULT_HORIZON_DURATION_MINUTES,
    DEFAULT_TIER_1_COUNT,
    DEFAULT_TIER_1_DURATION,
    DEFAULT_TIER_2_COUNT,
    DEFAULT_TIER_2_DURATION,
    DEFAULT_TIER_3_COUNT,
    DEFAULT_TIER_3_DURATION,
    DEFAULT_TIER_4_DURATION,
    DEFAULT_UPDATE_INTERVAL_MINUTES,
)

_LOGGER = logging.getLogger(__name__)

# Configuration key for horizon input in days (UI only, converted to minutes for storage)
CONF_HORIZON_DAYS: Final = "horizon_days"

# Horizon display units
HORIZON_UNIT_DAYS: Final = "days"
HORIZON_UNIT_HOURS: Final = "hours"
HORIZON_UNIT_MINUTES: Final = "minutes"

# Minimum horizon: 2 days in minutes
MIN_HORIZON_MINUTES: Final = 2 * 24 * 60
# Maximum horizon: 14 days in minutes
MAX_HORIZON_MINUTES: Final = 14 * 24 * 60


def convert_horizon_days_to_minutes(user_input: dict[str, Any]) -> dict[str, Any]:
    """Convert horizon_days from user input to horizon_duration_minutes.

    This function should be called after schema validation to convert the
    UI-friendly days value to the stored minutes value.
    """
    if CONF_HORIZON_DAYS in user_input:
        days = user_input.pop(CONF_HORIZON_DAYS)
        user_input[CONF_HORIZON_DURATION_MINUTES] = int(days) * 24 * 60
    return user_input


# Tier configuration keys (for reference)
TIER_CONF_KEYS: Final = [
    CONF_TIER_1_COUNT,
    CONF_TIER_1_DURATION,
    CONF_TIER_2_COUNT,
    CONF_TIER_2_DURATION,
    CONF_TIER_3_COUNT,
    CONF_TIER_3_DURATION,
    CONF_TIER_4_DURATION,
]


def get_default_tier_config(horizon_minutes: int | None = None) -> dict[str, int]:
    """Get default tier configuration.

    Args:
        horizon_minutes: Optional horizon duration in minutes. Defaults to 5 days.

    Returns:
        Dictionary with tier configuration keys.

    """
    return {
        CONF_TIER_1_COUNT: DEFAULT_TIER_1_COUNT,
        CONF_TIER_1_DURATION: DEFAULT_TIER_1_DURATION,
        CONF_TIER_2_COUNT: DEFAULT_TIER_2_COUNT,
        CONF_TIER_2_DURATION: DEFAULT_TIER_2_DURATION,
        CONF_TIER_3_COUNT: DEFAULT_TIER_3_COUNT,
        CONF_TIER_3_DURATION: DEFAULT_TIER_3_DURATION,
        CONF_TIER_4_DURATION: DEFAULT_TIER_4_DURATION,
        CONF_HORIZON_DURATION_MINUTES: horizon_minutes or DEFAULT_HORIZON_DURATION_MINUTES,
    }


def horizon_minutes_to_display(horizon_minutes: int) -> tuple[str, int]:
    """Convert horizon minutes to display unit and value.

    Args:
        horizon_minutes: Horizon duration in minutes.

    Returns:
        Tuple of (unit, value) for display.

    """
    if horizon_minutes % (24 * 60) == 0:
        return HORIZON_UNIT_DAYS, horizon_minutes // (24 * 60)
    if horizon_minutes % 60 == 0:
        return HORIZON_UNIT_HOURS, horizon_minutes // 60
    return HORIZON_UNIT_MINUTES, horizon_minutes


def get_hub_setup_schema(suggested_name: str | None = None) -> vol.Schema:
    """Get simplified schema for initial hub setup.

    Args:
        suggested_name: Optional suggested name for the hub (translatable default)

    Returns:
        Voluptuous schema with name, horizon duration (in days), and basic settings.
        Update interval and debounce settings are hidden during add and use defaults.

    Note:
        The schema uses CONF_HORIZON_DAYS for UI input. Call convert_horizon_days_to_minutes()
        on user_input after validation to convert to CONF_HORIZON_DURATION_MINUTES.

    """
    name_key = (
        vol.Required(CONF_NAME, description={"suggested_value": suggested_name})
        if suggested_name
        else vol.Required(CONF_NAME)
    )

    # Default: 5 days
    default_days = DEFAULT_HORIZON_DURATION_MINUTES // (24 * 60)

    return vol.Schema(
        {
            name_key: vol.All(
                str,
                vol.Strip,
                vol.Length(min=1, msg="Name cannot be empty"),
                vol.Length(max=255, msg="Name cannot be longer than 255 characters"),
            ),
            vol.Required(CONF_HORIZON_DAYS, default=default_days): vol.All(
                NumberSelector(
                    NumberSelectorConfig(
                        min=2,
                        max=14,
                        step=1,
                        mode=NumberSelectorMode.SLIDER,
                        unit_of_measurement="days",
                    )
                ),
                vol.Coerce(int),
            ),
            vol.Required(CONF_ADVANCED_MODE, default=False): bool,
        }
    )


def get_custom_tiers_schema(config_entry: ConfigEntry | None = None) -> vol.Schema:
    """Get schema for custom tier configuration step.

    Args:
        config_entry: Optional config entry to get current values from

    Returns:
        Voluptuous schema with tier configuration fields (counts are minimums).

    """
    return vol.Schema(
        {
            # Tier 1: Fine-grained near-term intervals (minimum count)
            vol.Required(
                CONF_TIER_1_COUNT,
                default=config_entry.data.get(CONF_TIER_1_COUNT, DEFAULT_TIER_1_COUNT)
                if config_entry
                else DEFAULT_TIER_1_COUNT,
            ): vol.All(
                NumberSelector(NumberSelectorConfig(min=0, max=60, step=1, mode=NumberSelectorMode.BOX)),
                vol.Coerce(int),
            ),
            vol.Required(
                CONF_TIER_1_DURATION,
                default=config_entry.data.get(CONF_TIER_1_DURATION, DEFAULT_TIER_1_DURATION)
                if config_entry
                else DEFAULT_TIER_1_DURATION,
            ): vol.All(
                NumberSelector(NumberSelectorConfig(min=1, max=60, step=1, mode=NumberSelectorMode.BOX)),
                vol.Coerce(int),
            ),
            # Tier 2: Short-term intervals (minimum count)
            vol.Required(
                CONF_TIER_2_COUNT,
                default=config_entry.data.get(CONF_TIER_2_COUNT, DEFAULT_TIER_2_COUNT)
                if config_entry
                else DEFAULT_TIER_2_COUNT,
            ): vol.All(
                NumberSelector(NumberSelectorConfig(min=0, max=60, step=1, mode=NumberSelectorMode.BOX)),
                vol.Coerce(int),
            ),
            vol.Required(
                CONF_TIER_2_DURATION,
                default=config_entry.data.get(CONF_TIER_2_DURATION, DEFAULT_TIER_2_DURATION)
                if config_entry
                else DEFAULT_TIER_2_DURATION,
            ): vol.All(
                NumberSelector(NumberSelectorConfig(min=1, max=60, step=1, mode=NumberSelectorMode.BOX)),
                vol.Coerce(int),
            ),
            # Tier 3: Medium-term intervals (minimum count)
            vol.Required(
                CONF_TIER_3_COUNT,
                default=config_entry.data.get(CONF_TIER_3_COUNT, DEFAULT_TIER_3_COUNT)
                if config_entry
                else DEFAULT_TIER_3_COUNT,
            ): vol.All(
                NumberSelector(NumberSelectorConfig(min=0, max=100, step=1, mode=NumberSelectorMode.BOX)),
                vol.Coerce(int),
            ),
            vol.Required(
                CONF_TIER_3_DURATION,
                default=config_entry.data.get(CONF_TIER_3_DURATION, DEFAULT_TIER_3_DURATION)
                if config_entry
                else DEFAULT_TIER_3_DURATION,
            ): vol.All(
                NumberSelector(NumberSelectorConfig(min=1, max=120, step=1, mode=NumberSelectorMode.BOX)),
                vol.Coerce(int),
            ),
            # Tier 4: Long-term intervals (duration only, count computed at runtime)
            vol.Required(
                CONF_TIER_4_DURATION,
                default=config_entry.data.get(CONF_TIER_4_DURATION, DEFAULT_TIER_4_DURATION)
                if config_entry
                else DEFAULT_TIER_4_DURATION,
            ): vol.All(
                NumberSelector(NumberSelectorConfig(min=1, max=240, step=1, mode=NumberSelectorMode.BOX)),
                vol.Coerce(int),
            ),
            # Horizon duration in minutes
            vol.Required(
                CONF_HORIZON_DURATION_MINUTES,
                default=config_entry.data.get(CONF_HORIZON_DURATION_MINUTES, DEFAULT_HORIZON_DURATION_MINUTES)
                if config_entry
                else DEFAULT_HORIZON_DURATION_MINUTES,
            ): vol.All(
                NumberSelector(
                    NumberSelectorConfig(
                        min=MIN_HORIZON_MINUTES,
                        max=MAX_HORIZON_MINUTES,
                        step=60,
                        mode=NumberSelectorMode.BOX,
                        unit_of_measurement="minutes",
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
        Voluptuous schema with horizon duration (in days) and basic settings.

    Note:
        The schema uses CONF_HORIZON_DAYS for UI input. Call convert_horizon_days_to_minutes()
        on user_input after validation to convert to CONF_HORIZON_DURATION_MINUTES.

    """
    # Get current horizon in days (rounded)
    current_horizon_minutes = config_entry.data.get(CONF_HORIZON_DURATION_MINUTES, DEFAULT_HORIZON_DURATION_MINUTES)
    current_days = current_horizon_minutes // (24 * 60)

    return vol.Schema(
        {
            vol.Required(CONF_HORIZON_DAYS, default=current_days): vol.All(
                NumberSelector(
                    NumberSelectorConfig(
                        min=2,
                        max=14,
                        step=1,
                        mode=NumberSelectorMode.SLIDER,
                        unit_of_measurement="days",
                    )
                ),
                vol.Coerce(int),
            ),
            vol.Required(
                CONF_UPDATE_INTERVAL_MINUTES,
                default=config_entry.data.get(CONF_UPDATE_INTERVAL_MINUTES, DEFAULT_UPDATE_INTERVAL_MINUTES),
            ): vol.All(
                NumberSelector(
                    NumberSelectorConfig(min=1, max=120, step=1, mode=NumberSelectorMode.BOX),
                ),
                vol.Coerce(int),
            ),
            vol.Required(
                CONF_DEBOUNCE_SECONDS,
                default=config_entry.data.get(CONF_DEBOUNCE_SECONDS, DEFAULT_DEBOUNCE_SECONDS),
            ): vol.All(
                NumberSelector(
                    NumberSelectorConfig(min=0, max=30, step=1, mode=NumberSelectorMode.BOX),
                ),
                vol.Coerce(int),
            ),
            vol.Required(
                CONF_ADVANCED_MODE,
                default=config_entry.data.get(CONF_ADVANCED_MODE, False),
            ): bool,
        }
    )
