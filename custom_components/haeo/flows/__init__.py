"""Base classes and utilities for HAEO config flows."""

from collections.abc import Sequence
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.selector import NumberSelector, NumberSelectorConfig
import voluptuous as vol

from custom_components.haeo.const import (
    CONF_HORIZON_HOURS,
    CONF_NAME,
    CONF_PERIOD_MINUTES,
    DEFAULT_HORIZON_HOURS,
    DEFAULT_PERIOD_MINUTES,
)

_LOGGER = logging.getLogger(__name__)


def get_network_config_schema(
    config_entry: ConfigEntry | None = None,
    existing_names: Sequence[str] | None = None,
) -> vol.Schema:
    """Get schema for network configuration.

    Args:
        config_entry: Config entry to get current values from
        existing_names: Set of existing network names to check for duplicates

    Returns:
        Voluptuous schema for network configuration

    """

    def validate_unique_network_name(name: str) -> str:
        """Validate that the network name is unique."""
        if existing_names and name in existing_names:
            msg = "Name already exists"
            raise vol.Invalid(msg)
        return name

    return vol.Schema(
        {
            **(
                {
                    vol.Required(CONF_NAME): vol.All(
                        str,
                        vol.Strip,
                        vol.Length(min=1, msg="Name cannot be empty"),
                        vol.Length(max=255, msg="Name cannot be longer than 255 characters"),
                        validate_unique_network_name,
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
            ): NumberSelector(
                NumberSelectorConfig(min=1, max=168, step=1, mode="slider"),
            ),
            vol.Required(
                CONF_PERIOD_MINUTES,
                default=config_entry.data.get(CONF_PERIOD_MINUTES, DEFAULT_PERIOD_MINUTES)
                if config_entry
                else DEFAULT_PERIOD_MINUTES,
            ): NumberSelector(
                NumberSelectorConfig(min=1, max=60, step=1, mode="slider"),
            ),
        }
    )
