"""Connection element configuration flows."""

from typing import Any, cast

from homeassistant.config_entries import ConfigSubentryFlow, SubentryFlowResult
from homeassistant.data_entry_flow import section
from homeassistant.helpers.selector import EntitySelector, EntitySelectorConfig, TextSelector, TextSelectorConfig
import voluptuous as vol

from custom_components.haeo.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.data.loader.extractors import extract_entity_metadata
from custom_components.haeo.flows.element_flow import ElementFlowMixin, build_exclusion_map, build_participant_selector

from .schema import (
    CONF_EFFICIENCY_SOURCE_TARGET,
    CONF_EFFICIENCY_TARGET_SOURCE,
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_MAX_POWER_TARGET_SOURCE,
    CONF_PRICE_SOURCE_TARGET,
    CONF_PRICE_TARGET_SOURCE,
    CONF_SOURCE,
    CONF_TARGET,
    ELEMENT_TYPE,
    INPUT_FIELDS,
    ConnectionConfigSchema,
)


def _flatten_sections(user_input: dict[str, Any]) -> dict[str, Any]:
    """Flatten section-nested user input for connection config."""
    result: dict[str, Any] = {}
    for key, value in user_input.items():
        # Check if this is a section group (INPUT_FIELDS keys)
        if key in INPUT_FIELDS and isinstance(value, dict):
            result.update(value)
        else:
            result[key] = value
    return result


def _build_schema(
    exclusion_map: dict[str, list[str]],
    participants: list[str],
    current_source: str | None = None,
    current_target: str | None = None,
) -> vol.Schema:
    """Build the voluptuous schema for connection configuration."""
    return vol.Schema(
        {
            vol.Required(CONF_NAME): vol.All(
                vol.Coerce(str),
                vol.Strip,
                vol.Length(min=1, msg="Name cannot be empty"),
                TextSelector(TextSelectorConfig()),
            ),
            vol.Required(CONF_SOURCE): build_participant_selector(participants, current_source),
            vol.Required(CONF_TARGET): build_participant_selector(participants, current_target),
            # Source to Target section
            vol.Required("source_to_target"): section(
                vol.Schema(
                    {
                        vol.Optional(CONF_MAX_POWER_SOURCE_TARGET): EntitySelector(
                            EntitySelectorConfig(
                                domain=["sensor", "input_number"],
                                multiple=True,
                                exclude_entities=exclusion_map.get(CONF_MAX_POWER_SOURCE_TARGET, []),
                            )
                        ),
                        vol.Optional(CONF_EFFICIENCY_SOURCE_TARGET): EntitySelector(
                            EntitySelectorConfig(
                                domain=["sensor", "input_number"],
                                multiple=True,
                                exclude_entities=exclusion_map.get(CONF_EFFICIENCY_SOURCE_TARGET, []),
                            )
                        ),
                        vol.Optional(CONF_PRICE_SOURCE_TARGET): EntitySelector(
                            EntitySelectorConfig(
                                domain=["sensor", "input_number"],
                                multiple=True,
                                exclude_entities=exclusion_map.get(CONF_PRICE_SOURCE_TARGET, []),
                            )
                        ),
                    }
                ),
                {"collapsed": True},
            ),
            # Target to Source section
            vol.Required("target_to_source"): section(
                vol.Schema(
                    {
                        vol.Optional(CONF_MAX_POWER_TARGET_SOURCE): EntitySelector(
                            EntitySelectorConfig(
                                domain=["sensor", "input_number"],
                                multiple=True,
                                exclude_entities=exclusion_map.get(CONF_MAX_POWER_TARGET_SOURCE, []),
                            )
                        ),
                        vol.Optional(CONF_EFFICIENCY_TARGET_SOURCE): EntitySelector(
                            EntitySelectorConfig(
                                domain=["sensor", "input_number"],
                                multiple=True,
                                exclude_entities=exclusion_map.get(CONF_EFFICIENCY_TARGET_SOURCE, []),
                            )
                        ),
                        vol.Optional(CONF_PRICE_TARGET_SOURCE): EntitySelector(
                            EntitySelectorConfig(
                                domain=["sensor", "input_number"],
                                multiple=True,
                                exclude_entities=exclusion_map.get(CONF_PRICE_TARGET_SOURCE, []),
                            )
                        ),
                    }
                ),
                {"collapsed": True},
            ),
        }
    )


class ConnectionSubentryFlowHandler(ElementFlowMixin, ConfigSubentryFlow):
    """Handle connection element configuration flows."""

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle adding a new connection element."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Flatten section-nested input
            flat_input = _flatten_sections(user_input)
            name = flat_input.get(CONF_NAME)
            if self._validate_name(name, errors):
                # Validate source != target
                source = flat_input.get(CONF_SOURCE)
                target = flat_input.get(CONF_TARGET)
                if source and target and source == target:
                    errors[CONF_TARGET] = "cannot_connect_to_self"

            if not errors:
                config = cast("ConnectionConfigSchema", {CONF_ELEMENT_TYPE: ELEMENT_TYPE, **flat_input})
                return self.async_create_entry(title=name, data=config)

        entity_metadata = extract_entity_metadata(self.hass)
        exclusion_map = build_exclusion_map(INPUT_FIELDS, entity_metadata)
        participants = self._get_participant_names()
        schema = _build_schema(exclusion_map, participants)

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle reconfiguring an existing connection element."""
        errors: dict[str, str] = {}
        subentry = self._get_reconfigure_subentry()

        if user_input is not None:
            # Flatten section-nested input
            flat_input = _flatten_sections(user_input)
            name = flat_input.get(CONF_NAME)
            if self._validate_name(name, errors):
                # Validate source != target
                source = flat_input.get(CONF_SOURCE)
                target = flat_input.get(CONF_TARGET)
                if source and target and source == target:
                    errors[CONF_TARGET] = "cannot_connect_to_self"

            if not errors:
                config = cast("ConnectionConfigSchema", {CONF_ELEMENT_TYPE: ELEMENT_TYPE, **flat_input})
                return self.async_update_and_abort(
                    self._get_entry(),
                    subentry,
                    title=str(name),
                    data=config,
                )

        entity_metadata = extract_entity_metadata(self.hass)
        exclusion_map = build_exclusion_map(INPUT_FIELDS, entity_metadata)
        current_source = subentry.data.get(CONF_SOURCE)
        current_target = subentry.data.get(CONF_TARGET)
        participants = self._get_participant_names()
        schema = _build_schema(
            exclusion_map,
            participants,
            current_source=current_source if isinstance(current_source, str) else None,
            current_target=current_target if isinstance(current_target, str) else None,
        )
        schema = self.add_suggested_values_to_schema(schema, subentry.data)

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=schema,
            errors=errors,
        )
