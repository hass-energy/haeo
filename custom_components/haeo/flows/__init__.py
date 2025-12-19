"""Base classes and utilities for HAEO config flows."""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.selector import NumberSelector, NumberSelectorConfig, NumberSelectorMode
import voluptuous as vol

from custom_components.haeo.const import (
    CONF_DEBOUNCE_SECONDS,
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
                        vol.Length(max=255, msg="Name cannot be longer than 255 characters"),
                    ),
                }
                if config_entry is None
                else {}
            ),
            # Tier 1: Fine-grained near-term intervals
            vol.Required(
                CONF_TIER_1_DURATION,
                default=config_entry.data.get(CONF_TIER_1_DURATION, DEFAULT_TIER_1_DURATION)
                if config_entry
                else DEFAULT_TIER_1_DURATION,
            ): vol.All(
                NumberSelector(NumberSelectorConfig(min=1, max=60, step=1, mode=NumberSelectorMode.BOX)),
                vol.Coerce(int),
            ),
            vol.Required(
                CONF_TIER_1_UNTIL,
                default=config_entry.data.get(CONF_TIER_1_UNTIL, DEFAULT_TIER_1_UNTIL)
                if config_entry
                else DEFAULT_TIER_1_UNTIL,
            ): vol.All(
                NumberSelector(NumberSelectorConfig(min=1, max=60, step=1, mode=NumberSelectorMode.BOX)),
                vol.Coerce(int),
            ),
            # Tier 2: Short-term intervals
            vol.Required(
                CONF_TIER_2_DURATION,
                default=config_entry.data.get(CONF_TIER_2_DURATION, DEFAULT_TIER_2_DURATION)
                if config_entry
                else DEFAULT_TIER_2_DURATION,
            ): vol.All(
                NumberSelector(NumberSelectorConfig(min=1, max=60, step=1, mode=NumberSelectorMode.BOX)),
                vol.Coerce(int),
            ),
            vol.Required(
                CONF_TIER_2_UNTIL,
                default=config_entry.data.get(CONF_TIER_2_UNTIL, DEFAULT_TIER_2_UNTIL)
                if config_entry
                else DEFAULT_TIER_2_UNTIL,
            ): vol.All(
                NumberSelector(NumberSelectorConfig(min=1, max=120, step=1, mode=NumberSelectorMode.BOX)),
                vol.Coerce(int),
            ),
            # Tier 3: Medium-term intervals
            vol.Required(
                CONF_TIER_3_DURATION,
                default=config_entry.data.get(CONF_TIER_3_DURATION, DEFAULT_TIER_3_DURATION)
                if config_entry
                else DEFAULT_TIER_3_DURATION,
            ): vol.All(
                NumberSelector(NumberSelectorConfig(min=1, max=120, step=1, mode=NumberSelectorMode.BOX)),
                vol.Coerce(int),
            ),
            vol.Required(
                CONF_TIER_3_UNTIL,
                default=config_entry.data.get(CONF_TIER_3_UNTIL, DEFAULT_TIER_3_UNTIL)
                if config_entry
                else DEFAULT_TIER_3_UNTIL,
            ): vol.All(
                NumberSelector(NumberSelectorConfig(min=1, max=2880, step=1, mode=NumberSelectorMode.BOX)),
                vol.Coerce(int),
            ),
            # Tier 4: Long-term intervals
            vol.Required(
                CONF_TIER_4_DURATION,
                default=config_entry.data.get(CONF_TIER_4_DURATION, DEFAULT_TIER_4_DURATION)
                if config_entry
                else DEFAULT_TIER_4_DURATION,
            ): vol.All(
                NumberSelector(NumberSelectorConfig(min=1, max=240, step=1, mode=NumberSelectorMode.BOX)),
                vol.Coerce(int),
            ),
            vol.Required(
                CONF_TIER_4_UNTIL,
                default=config_entry.data.get(CONF_TIER_4_UNTIL, DEFAULT_TIER_4_UNTIL)
                if config_entry
                else DEFAULT_TIER_4_UNTIL,
            ): vol.All(
                NumberSelector(NumberSelectorConfig(min=1, max=10080, step=1, mode=NumberSelectorMode.BOX)),
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
