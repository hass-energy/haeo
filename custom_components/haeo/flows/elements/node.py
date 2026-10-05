"""Node element configuration flows."""

from typing import Any

from homeassistant.config_entries import ConfigSubentryFlow, SubentryFlowResult
import voluptuous as vol

from custom_components.haeo.core.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.core.schema.elements.node import ELEMENT_TYPE
from custom_components.haeo.flows.element_flow import ElementFlowMixin
from custom_components.haeo.sections import build_common_fields


class NodeSubentryFlowHandler(ElementFlowMixin, ConfigSubentryFlow):
    """Handle node element configuration flows."""

    def _build_schema(self) -> vol.Schema:
        """Build the voluptuous schema for node configuration."""
        return vol.Schema(dict(build_common_fields(include_connection=False).values()))

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
            name = user_input.get(CONF_NAME)
            if self._validate_name(name, errors):
                config = {
                    CONF_ELEMENT_TYPE: ELEMENT_TYPE,
                    CONF_NAME: name,
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
        if subentry is not None:
            schema = self.add_suggested_values_to_schema(schema, dict(subentry.data))

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )
