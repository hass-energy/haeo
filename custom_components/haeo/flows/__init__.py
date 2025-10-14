"""Base classes and utilities for HAEO config flows."""

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
)
import voluptuous as vol

from custom_components.haeo.const import (
    AVAILABLE_OPTIMIZERS,
    CONF_HORIZON_HOURS,
    CONF_NAME,
    CONF_OPTIMIZER,
    CONF_PERIOD_MINUTES,
    DEFAULT_HORIZON_HOURS,
    DEFAULT_OPTIMIZER,
    DEFAULT_PERIOD_MINUTES,
    OPTIMIZER_NAME_MAP,
)

_LOGGER = logging.getLogger(__name__)

# Map actual optimizer names to translation-friendly keys (reverse of OPTIMIZER_NAME_MAP)
OPTIMIZER_KEY_MAP = {v: k for k, v in OPTIMIZER_NAME_MAP.items()}


def get_network_config_schema(
    config_entry: ConfigEntry | None = None,
) -> vol.Schema:
    """Get schema for network configuration.

    Args:
        config_entry: Config entry to get current values from

    Returns:
        Voluptuous schema for network configuration

    """
    # Build optimizer options with translation-friendly keys
    optimizer_options = [
        SelectOptionDict(value=OPTIMIZER_KEY_MAP.get(opt, opt.lower()), label=opt)
        for opt in AVAILABLE_OPTIMIZERS
        if opt in OPTIMIZER_KEY_MAP or opt.lower() in OPTIMIZER_NAME_MAP
    ]

    # Get default optimizer (convert from actual name to key if needed)
    default_optimizer = DEFAULT_OPTIMIZER
    if config_entry:
        stored_optimizer = config_entry.data.get(CONF_OPTIMIZER, DEFAULT_OPTIMIZER)
        # Convert old actual names to keys if needed
        default_optimizer = OPTIMIZER_KEY_MAP.get(stored_optimizer, stored_optimizer)
    else:
        default_optimizer = OPTIMIZER_KEY_MAP.get(DEFAULT_OPTIMIZER, DEFAULT_OPTIMIZER)

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
                vol.Coerce(int),
                NumberSelector(
                    NumberSelectorConfig(min=1, max=168, step=1, mode=NumberSelectorMode.SLIDER),
                ),
            ),
            vol.Required(
                CONF_PERIOD_MINUTES,
                default=config_entry.data.get(CONF_PERIOD_MINUTES, DEFAULT_PERIOD_MINUTES)
                if config_entry
                else DEFAULT_PERIOD_MINUTES,
            ): vol.All(
                vol.Coerce(int),
                NumberSelector(
                    NumberSelectorConfig(min=1, max=60, step=1, mode=NumberSelectorMode.SLIDER),
                ),
            ),
            vol.Required(
                CONF_OPTIMIZER,
                default=default_optimizer,
            ): SelectSelector(
                SelectSelectorConfig(
                    options=optimizer_options,
                    translation_key="optimizer",
                ),
            ),
        }
    )
