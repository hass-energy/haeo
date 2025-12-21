"""Base classes and utilities for HAEO config flows."""

import logging
from typing import Any, Final

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
    CONF_TIER_1_COUNT,
    CONF_TIER_1_DURATION,
    CONF_TIER_2_COUNT,
    CONF_TIER_2_DURATION,
    CONF_TIER_3_COUNT,
    CONF_TIER_3_DURATION,
    CONF_TIER_4_COUNT,
    CONF_TIER_4_DURATION,
    CONF_UPDATE_INTERVAL_MINUTES,
    DEFAULT_DEBOUNCE_SECONDS,
    DEFAULT_TIER_1_COUNT,
    DEFAULT_TIER_1_DURATION,
    DEFAULT_TIER_2_COUNT,
    DEFAULT_TIER_2_DURATION,
    DEFAULT_TIER_3_COUNT,
    DEFAULT_TIER_3_DURATION,
    DEFAULT_TIER_4_COUNT,
    DEFAULT_TIER_4_DURATION,
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


def _create_horizon_preset(days: int) -> dict[str, int]:
    """Create tier configuration for a given horizon in days.

    The configuration uses:
    - Tier 1: 5 x 1-minute intervals (5 minutes)
    - Tier 2: 11 x 5-minute intervals (55 minutes, cumulative 60 minutes)
    - Tier 3: 46 x 30-minute intervals (1 day cumulative)
    - Tier 4: 60-minute intervals for the remainder

    """
    min_days = 2
    if days < min_days:
        msg = f"Horizon must be at least {min_days} days"
        raise ValueError(msg)

    total_minutes = days * 24 * 60

    return {
        CONF_TIER_1_COUNT: 5,
        CONF_TIER_1_DURATION: 1,
        CONF_TIER_2_COUNT: 11,
        CONF_TIER_2_DURATION: 5,
        CONF_TIER_3_COUNT: 46,
        CONF_TIER_3_DURATION: 30,
        CONF_TIER_4_COUNT: (total_minutes - 1440) // 60,
        CONF_TIER_4_DURATION: 60,
    }


HORIZON_PRESETS: Final[dict[str, dict[str, int]]] = {
    HORIZON_PRESET_2_DAYS: _create_horizon_preset(2),
    HORIZON_PRESET_3_DAYS: _create_horizon_preset(3),
    HORIZON_PRESET_5_DAYS: _create_horizon_preset(5),
    HORIZON_PRESET_7_DAYS: _create_horizon_preset(7),
}

TIER_CONF_KEYS: Final = [
    CONF_TIER_1_COUNT,
    CONF_TIER_1_DURATION,
    CONF_TIER_2_COUNT,
    CONF_TIER_2_DURATION,
    CONF_TIER_3_COUNT,
    CONF_TIER_3_DURATION,
    CONF_TIER_4_COUNT,
    CONF_TIER_4_DURATION,
]


def get_tier_config(user_input: dict[str, Any], horizon_preset: str | None) -> tuple[dict[str, int], str]:
    """Get tier config from preset or user input.

    Args:
        user_input: User input dictionary containing tier values (if custom)
        horizon_preset: The selected horizon preset or None

    Returns:
        Tuple of (tier_config dict, stored_preset string)

    """
    if horizon_preset and horizon_preset != HORIZON_PRESET_CUSTOM:
        return HORIZON_PRESETS[horizon_preset], horizon_preset
    return {key: user_input[key] for key in TIER_CONF_KEYS}, HORIZON_PRESET_CUSTOM


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
            vol.Required(CONF_HORIZON_PRESET, default=HORIZON_PRESET_5_DAYS): SelectSelector(
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
                    NumberSelectorConfig(min=1, max=120, step=1, mode=NumberSelectorMode.SLIDER),
                ),
                vol.Coerce(int),
            ),
            vol.Required(
                CONF_DEBOUNCE_SECONDS,
                default=DEFAULT_DEBOUNCE_SECONDS,
            ): vol.All(
                NumberSelector(
                    NumberSelectorConfig(min=0, max=30, step=1, mode=NumberSelectorMode.SLIDER),
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
            # Tier 2: Short-term intervals
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
            # Tier 3: Medium-term intervals
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
            # Tier 4: Long-term intervals
            vol.Required(
                CONF_TIER_4_COUNT,
                default=config_entry.data.get(CONF_TIER_4_COUNT, DEFAULT_TIER_4_COUNT)
                if config_entry
                else DEFAULT_TIER_4_COUNT,
            ): vol.All(
                NumberSelector(NumberSelectorConfig(min=0, max=200, step=1, mode=NumberSelectorMode.BOX)),
                vol.Coerce(int),
            ),
            vol.Required(
                CONF_TIER_4_DURATION,
                default=config_entry.data.get(CONF_TIER_4_DURATION, DEFAULT_TIER_4_DURATION)
                if config_entry
                else DEFAULT_TIER_4_DURATION,
            ): vol.All(
                NumberSelector(NumberSelectorConfig(min=1, max=240, step=1, mode=NumberSelectorMode.BOX)),
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
                default=config_entry.data.get(CONF_UPDATE_INTERVAL_MINUTES, DEFAULT_UPDATE_INTERVAL_MINUTES),
            ): vol.All(
                NumberSelector(
                    NumberSelectorConfig(min=1, max=120, step=1, mode=NumberSelectorMode.SLIDER),
                ),
                vol.Coerce(int),
            ),
            vol.Required(
                CONF_DEBOUNCE_SECONDS,
                default=config_entry.data.get(CONF_DEBOUNCE_SECONDS, DEFAULT_DEBOUNCE_SECONDS),
            ): vol.All(
                NumberSelector(
                    NumberSelectorConfig(min=0, max=30, step=1, mode=NumberSelectorMode.SLIDER),
                ),
                vol.Coerce(int),
            ),
        }
    )
