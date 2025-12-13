"""Base classes and utilities for HAEO config flows."""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.selector import NumberSelector, NumberSelectorConfig, NumberSelectorMode
import voluptuous as vol

from custom_components.haeo.const import (
    CONF_DEBOUNCE_SECONDS,
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


def get_network_config_schema(
    config_entry: ConfigEntry | None = None,
) -> vol.Schema:
    """Get schema for network configuration.

    Args:
        config_entry: Config entry to get current values from

    Returns:
        Voluptuous schema for network configuration

    The configuration uses 4 tiers of intervals with variable durations:
    - Tier 1: Fine-grained near-term intervals (default: 5 x 1 min = 5 min)
    - Tier 2: Short-term intervals (default: 11 x 5 min = 55 min)
    - Tier 3: Medium-term intervals (default: 46 x 30 min = 23 hr)
    - Tier 4: Long-term intervals (default: 48 x 60 min = 48 hr)

    Total default: 110 periods covering ~72 hours
    """
    return vol.Schema(
        {
            **(
                {
                    vol.Required(CONF_NAME): vol.All(
                        str,
                        vol.Strip,
                        vol.Length(min=1, msg="Name cannot be empty"),
                        vol.Length(max=255, msg="Name cannot be longer than 255 characters"),
                    ),
                }
                if config_entry is None
                else {}
            ),
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
            # Update and debounce settings
            vol.Required(
                CONF_UPDATE_INTERVAL_MINUTES,
                default=config_entry.data.get(CONF_UPDATE_INTERVAL_MINUTES, DEFAULT_UPDATE_INTERVAL_MINUTES)
                if config_entry
                else DEFAULT_UPDATE_INTERVAL_MINUTES,
            ): vol.All(
                NumberSelector(
                    NumberSelectorConfig(min=1, max=120, step=1, mode=NumberSelectorMode.SLIDER),
                ),
                vol.Coerce(int),
            ),
            vol.Required(
                CONF_DEBOUNCE_SECONDS,
                default=config_entry.data.get(CONF_DEBOUNCE_SECONDS, DEFAULT_DEBOUNCE_SECONDS)
                if config_entry
                else DEFAULT_DEBOUNCE_SECONDS,
            ): vol.All(
                NumberSelector(
                    NumberSelectorConfig(min=0, max=30, step=1, mode=NumberSelectorMode.SLIDER),
                ),
                vol.Coerce(int),
            ),
        }
    )
