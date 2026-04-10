"""Tariff element configuration flows."""

from typing import Any

from homeassistant.config_entries import ConfigSubentryFlow, SubentryFlowResult
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)
import voluptuous as vol

from custom_components.haeo.core.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.core.schema.elements.tariff import (
    CONF_DESTINATIONS,
    CONF_PRICE_SOURCE_TARGET,
    CONF_PRICE_TARGET_SOURCE,
    CONF_SOURCES,
    ELEMENT_TYPE,
    SECTION_ENDPOINTS,
    SECTION_TAG_PRICING,
)
from custom_components.haeo.flows.element_flow import ElementFlowMixin
from custom_components.haeo.flows.field_schema import SectionDefinition, build_section_schema
from custom_components.haeo.sections import build_common_fields

# Special value for "any node"
ANY_NODE = "*"


class TariffSubentryFlowHandler(ElementFlowMixin, ConfigSubentryFlow):
    """Handle tariff element configuration flows."""

    def _get_sections(self) -> tuple[SectionDefinition, ...]:
        """Return sections for the configuration step."""
        return (
            SectionDefinition(
                key=SECTION_ENDPOINTS,
                fields=(CONF_SOURCES, CONF_DESTINATIONS),
                collapsed=False,
            ),
            SectionDefinition(
                key=SECTION_TAG_PRICING,
                fields=(CONF_PRICE_SOURCE_TARGET, CONF_PRICE_TARGET_SOURCE),
                collapsed=False,
            ),
        )

    def _build_schema(self, participants: list[str]) -> vol.Schema:
        """Build the voluptuous schema for tariff configuration."""
        # Add "Any" option to participant list
        source_options = [ANY_NODE, *participants]
        dest_options = [ANY_NODE, *participants]

        sections = self._get_sections()
        field_entries: dict[str, dict[str, tuple[vol.Marker, Any]]] = {
            SECTION_ENDPOINTS: {
                CONF_SOURCES: (
                    vol.Required(CONF_SOURCES),
                    SelectSelector(
                        SelectSelectorConfig(
                            options=source_options,
                            mode=SelectSelectorMode.DROPDOWN,
                            multiple=True,
                            translation_key="tariff_sources",
                        )
                    ),
                ),
                CONF_DESTINATIONS: (
                    vol.Required(CONF_DESTINATIONS),
                    SelectSelector(
                        SelectSelectorConfig(
                            options=dest_options,
                            mode=SelectSelectorMode.DROPDOWN,
                            multiple=True,
                            translation_key="tariff_destinations",
                        )
                    ),
                ),
            },
            SECTION_TAG_PRICING: {
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
        """Handle adding a new tariff element."""
        return await self._async_step_user(user_input)

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle reconfiguring an existing tariff element."""
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

            sources = endpoints.get(CONF_SOURCES, [])
            destinations = endpoints.get(CONF_DESTINATIONS, [])

            if self._validate_name(name, errors):
                if not sources:
                    errors["base"] = "missing_sources"
                elif not destinations:
                    errors["base"] = "missing_destinations"
                else:
                    # Normalize "any" selections
                    if ANY_NODE in sources:
                        sources = [ANY_NODE]
                    if ANY_NODE in destinations:
                        destinations = [ANY_NODE]

                    config: dict[str, Any] = {
                        CONF_ELEMENT_TYPE: ELEMENT_TYPE,
                        CONF_NAME: name,
                        SECTION_ENDPOINTS: {
                            CONF_SOURCES: sources,
                            CONF_DESTINATIONS: destinations,
                        },
                        SECTION_TAG_PRICING: {},
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
