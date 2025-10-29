"""Base classes and utilities for HAEO config flows."""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.selector import NumberSelector, NumberSelectorConfig, NumberSelectorMode
import voluptuous as vol

from custom_components.haeo.const import (
    CONF_DEBOUNCE_SECONDS,
    CONF_HORIZON_HOURS,
    CONF_NAME,
    CONF_PERIOD_MINUTES,
    CONF_UPDATE_INTERVAL_MINUTES,
    DEFAULT_DEBOUNCE_SECONDS,
    DEFAULT_HORIZON_HOURS,
    DEFAULT_PERIOD_MINUTES,
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
            vol.Required(
                CONF_HORIZON_HOURS,
                default=config_entry.data.get(CONF_HORIZON_HOURS, DEFAULT_HORIZON_HOURS)
                if config_entry
                else DEFAULT_HORIZON_HOURS,
            ): vol.All(
                NumberSelector(
                    NumberSelectorConfig(min=1, max=168, step=1, mode=NumberSelectorMode.SLIDER),
                ),
                vol.Coerce(int),
            ),
            vol.Required(
                CONF_PERIOD_MINUTES,
                default=config_entry.data.get(CONF_PERIOD_MINUTES, DEFAULT_PERIOD_MINUTES)
                if config_entry
                else DEFAULT_PERIOD_MINUTES,
            ): vol.All(
                NumberSelector(
                    NumberSelectorConfig(min=1, max=60, step=1, mode=NumberSelectorMode.SLIDER),
                ),
                vol.Coerce(int),
            ),
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
