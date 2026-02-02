"""Node element configuration flows."""

from typing import Any

from homeassistant.config_entries import ConfigSubentry, ConfigSubentryFlow, SubentryFlowResult, UnknownSubEntry
from homeassistant.helpers.selector import BooleanSelector, BooleanSelectorConfig
import voluptuous as vol

from custom_components.haeo.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.flows.element_flow import ElementFlowMixin
from custom_components.haeo.flows.field_schema import SectionDefinition, build_section_schema
from custom_components.haeo.sections import (
    SECTION_COMMON,
    SECTION_ROLE,
    build_common_fields,
    common_section,
    role_section,
)

from .schema import CONF_IS_SINK, CONF_IS_SOURCE, ELEMENT_TYPE

# Suggested values for first setup (pure junction: no source or sink)
_SUGGESTED_DEFAULTS = {
    SECTION_COMMON: {},
    SECTION_ROLE: {
        CONF_IS_SOURCE: False,
        CONF_IS_SINK: False,
    },
}


class NodeSubentryFlowHandler(ElementFlowMixin, ConfigSubentryFlow):
    """Handle node element configuration flows."""

    def _get_sections(self) -> tuple[SectionDefinition, ...]:
        """Return sections for the configuration step."""
        return (
            common_section((CONF_NAME,), collapsed=False),
            role_section((CONF_IS_SOURCE, CONF_IS_SINK), collapsed=True),
        )

    def _build_schema(self) -> vol.Schema:
        """Build the voluptuous schema for node configuration."""
        sections = self._get_sections()
        field_entries: dict[str, dict[str, tuple[vol.Marker, Any]]] = {
            SECTION_COMMON: build_common_fields(include_connection=False),
            SECTION_ROLE: {
                CONF_IS_SOURCE: (
                    vol.Optional(CONF_IS_SOURCE),
                    vol.All(
                        vol.Coerce(bool),
                        BooleanSelector(BooleanSelectorConfig()),
                    ),
                ),
                CONF_IS_SINK: (
                    vol.Optional(CONF_IS_SINK),
                    vol.All(
                        vol.Coerce(bool),
                        BooleanSelector(BooleanSelectorConfig()),
                    ),
                ),
            },
        }

        return vol.Schema(build_section_schema(sections, field_entries))

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle adding a new node element."""
        return await self._async_step_user(user_input)

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle reconfiguring an existing node element."""
        return await self._async_step_user(user_input)

    async def _async_step_user(self, user_input: dict[str, Any] | None) -> SubentryFlowResult:
        """Shared logic for user and reconfigure steps."""
        errors: dict[str, str] = {}
        subentry = self._get_subentry()

        if user_input is not None:
            common_input = user_input.get(SECTION_COMMON, {})
            role_input = user_input.get(SECTION_ROLE, {})
            name = common_input.get(CONF_NAME)
            if self._validate_name(name, errors):
                config = {
                    CONF_ELEMENT_TYPE: ELEMENT_TYPE,
                    SECTION_COMMON: {CONF_NAME: name},
                    SECTION_ROLE: {
                        CONF_IS_SOURCE: bool(role_input.get(CONF_IS_SOURCE, False)),
                        CONF_IS_SINK: bool(role_input.get(CONF_IS_SINK, False)),
                    },
                }
                if subentry is not None:
                    return self.async_update_and_abort(
                        self._get_entry(),
                        subentry,
                        title=str(name),
                        data=config,
                    )
                return self.async_create_entry(title=name, data=config)

        schema = self._build_schema()
        defaults = dict(subentry.data) if subentry else _SUGGESTED_DEFAULTS
        schema = self.add_suggested_values_to_schema(schema, defaults)

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    def _get_subentry(self) -> ConfigSubentry | None:
        try:
            return self._get_reconfigure_subentry()
        except (ValueError, UnknownSubEntry):
            return None
