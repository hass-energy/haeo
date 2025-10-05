"""Base classes and utilities for HAEO config flows."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.helpers.selector import NumberSelector, NumberSelectorConfig
import voluptuous as vol

from custom_components.haeo.const import (
    CONF_HORIZON_HOURS,
    CONF_PERIOD_MINUTES,
    DEFAULT_HORIZON_HOURS,
    DEFAULT_PERIOD_MINUTES,
    MAX_HORIZON_HOURS,
    MAX_NAME_LENGTH,
    MAX_PERIOD_MINUTES,
)

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


def get_network_timing_schema(
    config_entry: ConfigEntry | None = None,
    *,
    include_name: bool = False,
    name_required: bool = True,
    current_name: str | None = None,
) -> vol.Schema:
    """Get schema for network timing configuration.

    Args:
        config_entry: Config entry to get current values from
        include_name: Whether to include name field in schema
        name_required: Whether name field is required
        current_name: Current name value for editing

    Returns:
        Voluptuous schema for network timing configuration

    """
    schema_dict = {}

    # Add name field if requested
    if include_name:
        name_field = vol.Required("name") if name_required else vol.Optional("name", default=current_name or "")
        schema_dict[name_field] = vol.All(
            str,
            vol.Strip,
            vol.Length(min=1, msg="Name cannot be empty"),
            vol.Length(max=255, msg="Name cannot be longer than 255 characters"),
        )

    # Add horizon hours field
    current_horizon = DEFAULT_HORIZON_HOURS
    if config_entry:
        current_horizon = int(config_entry.data.get(CONF_HORIZON_HOURS, DEFAULT_HORIZON_HOURS))

    schema_dict[vol.Required(CONF_HORIZON_HOURS, default=current_horizon)] = NumberSelector(
        NumberSelectorConfig(min=1, max=168, step=1, mode="slider"),
    )

    # Add period minutes field
    current_period = DEFAULT_PERIOD_MINUTES
    if config_entry:
        current_period = int(config_entry.data.get(CONF_PERIOD_MINUTES, DEFAULT_PERIOD_MINUTES))

    schema_dict[vol.Required(CONF_PERIOD_MINUTES, default=current_period)] = NumberSelector(
        NumberSelectorConfig(min=1, max=60, step=1, mode="slider"),
    )

    return vol.Schema(schema_dict)


def validate_network_timing_input(
    user_input: dict[str, Any],
    hass: HomeAssistant | None = None,
    *,
    include_name: bool = False,
    name_required: bool = True,
) -> tuple[dict[str, str], dict[str, Any]]:
    """Validate network timing input data.

    Args:
        user_input: User input dictionary
        hass: Home Assistant instance (needed for name validation)
        include_name: Whether name validation is needed
        name_required: Whether name is required

    Returns:
        Tuple of (errors dict, validated data dict)

    """
    errors = {}

    # Validate horizon hours
    horizon = int(user_input.get(CONF_HORIZON_HOURS, DEFAULT_HORIZON_HOURS))
    if not (1 <= horizon <= MAX_HORIZON_HOURS):
        errors[CONF_HORIZON_HOURS] = "invalid_horizon"

    # Validate period minutes
    period = int(user_input.get(CONF_PERIOD_MINUTES, DEFAULT_PERIOD_MINUTES))
    if not (1 <= period <= MAX_PERIOD_MINUTES):
        errors[CONF_PERIOD_MINUTES] = "invalid_period"

    # Validate name if required
    if include_name and name_required:
        name = user_input.get("name", "").strip()
        if not name:
            errors["name"] = "name_required"
        elif len(name) > MAX_NAME_LENGTH:
            errors["name"] = "name_too_long"
        elif hass:
            # Check for duplicate names
            for entry in hass.config_entries.async_entries("haeo"):
                if entry.title == name:
                    errors["name"] = "name_exists"
                    break

    validated_data = {
        CONF_HORIZON_HOURS: horizon,
        CONF_PERIOD_MINUTES: period,
    }

    if include_name:
        validated_data["name"] = name

    return errors, validated_data
