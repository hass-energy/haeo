"""Custom subentry flow for Load element with conditional field display."""

from typing import Any, cast

from homeassistant.config_entries import SubentryFlowResult
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)
from homeassistant.helpers.translation import async_get_translations
import voluptuous as vol

from custom_components.haeo.const import CONF_ELEMENT_TYPE, CONF_NAME, DOMAIN
from custom_components.haeo.data.loader.extractors import extract_entity_metadata
from custom_components.haeo.elements import ElementConfigSchema
from custom_components.haeo.elements.load import (
    CONF_CONNECTION,
    CONF_FORECAST,
    CONF_FORECAST_SOURCE,
    CONF_HISTORY_DAYS,
    CONFIG_DEFAULTS,
    DEFAULT_HISTORY_DAYS,
    ELEMENT_TYPE,
    LoadConfigSchema,
)
from custom_components.haeo.network import evaluate_network_connectivity
from custom_components.haeo.schema import schema_for_type
from custom_components.haeo.schema.fields import FORECAST_SOURCE_CUSTOM_SENSOR, FORECAST_SOURCE_ENERGY_TAB
from custom_components.haeo.validation import collect_participant_configs

from .element import ElementSubentryFlow


class LoadSubentryFlow(ElementSubentryFlow):
    """Custom subentry flow for Load element with conditional field display.

    Uses a two-step flow:
    1. Step 1: Basic info (name, connection) and forecast source selection
    2. Step 2: Source-specific fields (history_days or forecast sensors)
    """

    def __init__(self) -> None:
        """Initialize the load subentry flow."""
        super().__init__(ELEMENT_TYPE, LoadConfigSchema, CONFIG_DEFAULTS)
        self._user_input: dict[str, Any] = {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Step 1: Basic configuration and forecast source selection."""
        errors: dict[str, str] = {}

        if user_input is not None:
            name = user_input.get(CONF_NAME)
            if not name:
                errors[CONF_NAME] = "missing_name"
            elif name in self._get_used_names():
                errors[CONF_NAME] = "name_exists"

            if not errors:
                # Store step 1 input and proceed to step 2
                self._user_input = user_input
                return await self.async_step_forecast_config()

        # Build schema for step 1
        participants = self._get_non_connection_element_names()
        connection_options: list[SelectOptionDict] = [SelectOptionDict(value=p, label=p) for p in participants]
        forecast_source_options: list[SelectOptionDict] = [
            SelectOptionDict(value=FORECAST_SOURCE_ENERGY_TAB, label="Energy Tab"),
            SelectOptionDict(value=FORECAST_SOURCE_CUSTOM_SENSOR, label="Custom Sensor"),
        ]

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME): str,
                vol.Required(CONF_CONNECTION): SelectSelector(
                    SelectSelectorConfig(options=connection_options, mode=SelectSelectorMode.DROPDOWN)
                ),
                vol.Required(CONF_FORECAST_SOURCE, default=FORECAST_SOURCE_ENERGY_TAB): SelectSelector(
                    SelectSelectorConfig(options=forecast_source_options, mode=SelectSelectorMode.DROPDOWN)
                ),
            }
        )

        # Get default name
        translations = await async_get_translations(
            self.hass, self.hass.config.language, "config_subentries", integrations=[DOMAIN]
        )
        default_name = translations.get(f"component.{DOMAIN}.config_subentries.{ELEMENT_TYPE}.flow_title", "Load")
        suggested = {CONF_NAME: default_name, **CONFIG_DEFAULTS}
        schema = self.add_suggested_values_to_schema(schema, suggested)

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_forecast_config(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Step 2: Forecast-specific configuration based on selected source."""
        errors: dict[str, str] = {}
        forecast_source = self._user_input.get(CONF_FORECAST_SOURCE, FORECAST_SOURCE_ENERGY_TAB)

        if user_input is not None:
            # Combine with step 1 input
            combined_input = {**self._user_input, **user_input}
            name = combined_input.get(CONF_NAME)

            # Validate forecast-specific fields
            if forecast_source == FORECAST_SOURCE_ENERGY_TAB:
                if not user_input.get(CONF_HISTORY_DAYS):
                    errors[CONF_HISTORY_DAYS] = "missing_history_days"
            elif not user_input.get(CONF_FORECAST):
                errors[CONF_FORECAST] = "missing_forecast"

            if not errors:
                # Create the config
                new_config = cast("ElementConfigSchema", {CONF_ELEMENT_TYPE: ELEMENT_TYPE, **combined_input})

                hub_entry = self._get_entry()
                participant_configs = collect_participant_configs(hub_entry)
                participant_configs[new_config[CONF_NAME]] = new_config
                await evaluate_network_connectivity(self.hass, hub_entry, participant_configs=participant_configs)

                return self.async_create_entry(title=str(name), data=new_config)

        # Build schema based on forecast source
        if forecast_source == FORECAST_SOURCE_ENERGY_TAB:
            schema = vol.Schema(
                {
                    vol.Required(CONF_HISTORY_DAYS, default=DEFAULT_HISTORY_DAYS): NumberSelector(
                        NumberSelectorConfig(
                            mode=NumberSelectorMode.BOX,
                            min=1,
                            max=30,
                            step=1,
                            unit_of_measurement="days",
                        )
                    ),
                }
            )
        else:
            # Custom sensor mode - use the power sensors field from the full schema
            entity_metadata = extract_entity_metadata(self.hass)
            full_schema = schema_for_type(
                LoadConfigSchema,
                entity_metadata=entity_metadata,
                participants=self._get_non_connection_element_names(),
                current_element_name=None,
            )
            # Extract just the forecast field
            forecast_validator = full_schema.schema.get(vol.Optional(CONF_FORECAST)) or full_schema.schema.get(
                vol.Required(CONF_FORECAST)
            )
            schema = vol.Schema({vol.Required(CONF_FORECAST): forecast_validator})

        return self.async_show_form(step_id="forecast_config", data_schema=schema, errors=errors)

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Reconfigure existing load element."""
        errors: dict[str, str] = {}
        hub_entry = self._get_entry()
        subentry = self._get_reconfigure_subentry()
        current_data = dict(subentry.data)

        if user_input is not None:
            new_name = user_input.get(CONF_NAME)
            if not new_name:
                errors[CONF_NAME] = "missing_name"
            elif new_name in self._get_used_names():
                errors[CONF_NAME] = "name_exists"

            # Validate based on forecast source
            forecast_source = user_input.get(CONF_FORECAST_SOURCE, FORECAST_SOURCE_ENERGY_TAB)
            if forecast_source == FORECAST_SOURCE_ENERGY_TAB:
                if not user_input.get(CONF_HISTORY_DAYS):
                    errors[CONF_HISTORY_DAYS] = "missing_history_days"
            elif not user_input.get(CONF_FORECAST):
                errors[CONF_FORECAST] = "missing_forecast"

            if not errors:
                updated_config = cast("ElementConfigSchema", {CONF_ELEMENT_TYPE: ELEMENT_TYPE, **user_input})

                participant_configs = collect_participant_configs(hub_entry)
                current_name = subentry.data.get(CONF_NAME)
                if isinstance(current_name, str):
                    participant_configs.pop(current_name, None)
                participant_configs[updated_config[CONF_NAME]] = updated_config
                await evaluate_network_connectivity(self.hass, hub_entry, participant_configs=participant_configs)

                return self.async_update_and_abort(
                    hub_entry,
                    subentry,
                    title=str(new_name),
                    data=updated_config,
                )

        # Build full schema for reconfiguration
        entity_metadata = extract_entity_metadata(self.hass)
        full_schema = schema_for_type(
            LoadConfigSchema,
            entity_metadata=entity_metadata,
            participants=self._get_non_connection_element_names(),
            current_element_name=subentry.data.get(CONF_NAME),
        )
        full_schema = self.add_suggested_values_to_schema(full_schema, current_data)

        return self.async_show_form(step_id="reconfigure", data_schema=full_schema, errors=errors)
