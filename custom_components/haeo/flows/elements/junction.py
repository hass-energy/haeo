"""Junction element configuration flows."""

from typing import (
    Any,  # noqa: TID251  # HA flow signatures upstream; voluptuous schema value types are heterogeneous by design
)

from homeassistant.config_entries import ConfigSubentryFlow, SubentryFlowResult
import voluptuous as vol

from custom_components.haeo.core.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.core.schema.elements.junction import ELEMENT_TYPE
from custom_components.haeo.flows.element_flow import ElementFlowMixin
from custom_components.haeo.flows.field_schema import as_str
from custom_components.haeo.sections import build_common_fields


class JunctionSubentryFlowHandler(ElementFlowMixin, ConfigSubentryFlow):
    """Handle junction element configuration flows."""

    def _build_schema(self) -> vol.Schema:
        """Build the voluptuous schema for junction configuration."""
        return vol.Schema(dict(build_common_fields(include_connection=False).values()))

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle adding a new junction element."""
        return await self._async_step_user(user_input)

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle reconfiguring an existing junction element."""
        return await self._async_step_user(user_input)

    async def _async_step_user(self, user_input: dict[str, object] | None) -> SubentryFlowResult:
        """Shared logic for user and reconfigure steps."""
        errors: dict[str, str] = {}
        subentry = self._get_subentry()

        if user_input is not None:
            name = as_str(user_input.get(CONF_NAME))
            if self._validate_name(name, errors):
                config: dict[str, object] = {CONF_ELEMENT_TYPE: ELEMENT_TYPE, CONF_NAME: name}
                if subentry is not None:
                    return self.async_update_and_abort(self._get_entry(), subentry, title=str(name), data=config)
                return self.async_create_entry(title=str(name), data=config)

        schema = self._build_schema()
        if subentry is not None:
            schema = self.add_suggested_values_to_schema(schema, dict(subentry.data))

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
