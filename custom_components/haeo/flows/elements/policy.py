"""Policy element configuration flows."""

from typing import Any

from homeassistant.config_entries import ConfigSubentryFlow, SubentryFlowResult
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)
import voluptuous as vol

from custom_components.haeo.core.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.core.schema import normalize_connection_target
from custom_components.haeo.core.schema.elements.policy import (
    CONF_PRICE_SOURCE_TARGET,
    CONF_PRICE_TARGET_SOURCE,
    CONF_SOURCE,
    CONF_TAG,
    CONF_TARGET,
    ELEMENT_TYPE,
    SECTION_ENDPOINTS,
    SECTION_TAG_PRICING,
)
from custom_components.haeo.flows.element_flow import ElementFlowMixin
from custom_components.haeo.flows.field_schema import SectionDefinition, build_section_schema
from custom_components.haeo.sections import build_common_fields


class PolicySubentryFlowHandler(ElementFlowMixin, ConfigSubentryFlow):
    """Handle policy element configuration flows."""

    def _get_sections(self) -> tuple[SectionDefinition, ...]:
        """Return sections for the configuration step."""
        return (
            SectionDefinition(
                key=SECTION_ENDPOINTS,
                fields=(CONF_SOURCE, CONF_TARGET),
                collapsed=False,
            ),
            SectionDefinition(
                key=SECTION_TAG_PRICING,
                fields=(CONF_TAG, CONF_PRICE_SOURCE_TARGET, CONF_PRICE_TARGET_SOURCE),
                collapsed=False,
            ),
        )

    def _build_schema(self, participants: list[str]) -> vol.Schema:
        """Build the voluptuous schema for policy configuration."""
        sections = self._get_sections()
        field_entries: dict[str, dict[str, tuple[vol.Marker, Any]]] = {
            SECTION_ENDPOINTS: {
                CONF_SOURCE: (
                    vol.Required(CONF_SOURCE),
                    SelectSelector(
                        SelectSelectorConfig(
                            options=participants,
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    ),
                ),
                CONF_TARGET: (
                    vol.Required(CONF_TARGET),
                    SelectSelector(
                        SelectSelectorConfig(
                            options=participants,
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    ),
                ),
            },
            SECTION_TAG_PRICING: {
                CONF_TAG: (
                    vol.Required(CONF_TAG),
                    TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT)),
                ),
                CONF_PRICE_SOURCE_TARGET: (
                    vol.Optional(CONF_PRICE_SOURCE_TARGET),
                    NumberSelector(
                        NumberSelectorConfig(
                            min=0,
                            max=100,
                            step=0.001,
                            mode=NumberSelectorMode.BOX,
                            unit_of_measurement="$/kWh",
                        )
                    ),
                ),
                CONF_PRICE_TARGET_SOURCE: (
                    vol.Optional(CONF_PRICE_TARGET_SOURCE),
                    NumberSelector(
                        NumberSelectorConfig(
                            min=0,
                            max=100,
                            step=0.001,
                            mode=NumberSelectorMode.BOX,
                            unit_of_measurement="$/kWh",
                        )
                    ),
                ),
            },
        }

        return vol.Schema(
            build_section_schema(
                sections,
                field_entries,
                top_level_entries=build_common_fields(include_connection=False),
            )
        )

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle adding a new policy element."""
        return await self._async_step_user(user_input)

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle reconfiguring an existing policy element."""
        return await self._async_step_user(user_input)

    async def _async_step_user(self, user_input: dict[str, Any] | None) -> SubentryFlowResult:
        """Shared logic for user and reconfigure steps."""
        errors: dict[str, str] = {}
        subentry = self._get_subentry()
        participants = self._get_participant_names()

        if user_input is not None:
            name = user_input.get(CONF_NAME)
            endpoints = user_input.get(SECTION_ENDPOINTS, {})
            tag_pricing = user_input.get(SECTION_TAG_PRICING, {})

            if self._validate_name(name, errors):
                source = endpoints.get(CONF_SOURCE)
                target = endpoints.get(CONF_TARGET)

                if source == target:
                    errors["base"] = "source_target_same"
                elif not source or not target:
                    errors["base"] = "missing_endpoints"
                else:
                    config: dict[str, Any] = {
                        CONF_ELEMENT_TYPE: ELEMENT_TYPE,
                        CONF_NAME: name,
                        SECTION_ENDPOINTS: {
                            CONF_SOURCE: normalize_connection_target(source),
                            CONF_TARGET: normalize_connection_target(target),
                        },
                        SECTION_TAG_PRICING: {
                            CONF_TAG: tag_pricing.get(CONF_TAG, "default"),
                        },
                    }
                    if CONF_PRICE_SOURCE_TARGET in tag_pricing and tag_pricing[CONF_PRICE_SOURCE_TARGET] is not None:
                        config[SECTION_TAG_PRICING][CONF_PRICE_SOURCE_TARGET] = {
                            "type": "constant",
                            "value": float(tag_pricing[CONF_PRICE_SOURCE_TARGET]),
                        }
                    if CONF_PRICE_TARGET_SOURCE in tag_pricing and tag_pricing[CONF_PRICE_TARGET_SOURCE] is not None:
                        config[SECTION_TAG_PRICING][CONF_PRICE_TARGET_SOURCE] = {
                            "type": "constant",
                            "value": float(tag_pricing[CONF_PRICE_TARGET_SOURCE]),
                        }

                    if subentry is not None:
                        return self.async_update_and_abort(
                            self._get_entry(),
                            subentry,
                            title=str(name),
                            data=config,
                        )
                    return self.async_create_entry(title=name, data=config)

        schema = self._build_schema(participants)
        defaults = dict(subentry.data) if subentry else {}
        schema = self.add_suggested_values_to_schema(schema, defaults)

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )
