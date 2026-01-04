"""Node element configuration flows."""

from typing import Any, cast

from homeassistant.config_entries import ConfigSubentryFlow, SubentryFlowResult
from homeassistant.helpers.selector import BooleanSelector, BooleanSelectorConfig, TextSelector, TextSelectorConfig
from homeassistant.helpers.translation import async_get_translations
import voluptuous as vol

from custom_components.haeo.const import CONF_ELEMENT_TYPE, CONF_NAME, DOMAIN
from custom_components.haeo.flows.element_flow import ElementFlowMixin

from .schema import CONF_IS_SINK, CONF_IS_SOURCE, DEFAULTS, ELEMENT_TYPE, NodeConfigSchema


def _build_schema() -> vol.Schema:
    """Build the voluptuous schema for node configuration."""
    return vol.Schema(
        {
            vol.Required(CONF_NAME): vol.All(
                vol.Coerce(str),
                vol.Strip,
                vol.Length(min=1, msg="Name cannot be empty"),
                TextSelector(TextSelectorConfig()),
            ),
            vol.Optional(CONF_IS_SOURCE): vol.All(
                vol.Coerce(bool),
                BooleanSelector(BooleanSelectorConfig()),
            ),
            vol.Optional(CONF_IS_SINK): vol.All(
                vol.Coerce(bool),
                BooleanSelector(BooleanSelectorConfig()),
            ),
        }
    )


class NodeSubentryFlowHandler(ElementFlowMixin, ConfigSubentryFlow):
    """Handle node element configuration flows."""

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle adding a new node element."""
        errors: dict[str, str] = {}

        if user_input is not None:
            name = user_input.get(CONF_NAME)
            if self._validate_name(name, errors):
                config = cast("NodeConfigSchema", {CONF_ELEMENT_TYPE: ELEMENT_TYPE, **user_input})
                return self.async_create_entry(title=name, data=config)

        # Get default name from translations
        translations = await async_get_translations(
            self.hass, self.hass.config.language, "config_subentries", integrations=[DOMAIN]
        )
        default_name = translations.get(f"component.{DOMAIN}.config_subentries.{ELEMENT_TYPE}.flow_title", "Node")

        schema = _build_schema()
        defaults = {CONF_NAME: default_name, **DEFAULTS}
        schema = self.add_suggested_values_to_schema(schema, defaults)

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle reconfiguring an existing node element."""
        errors: dict[str, str] = {}
        subentry = self._get_reconfigure_subentry()

        if user_input is not None:
            name = user_input.get(CONF_NAME)
            if self._validate_name(name, errors):
                config = cast("NodeConfigSchema", {CONF_ELEMENT_TYPE: ELEMENT_TYPE, **user_input})
                return self.async_update_and_abort(
                    self._get_entry(),
                    subentry,
                    title=str(name),
                    data=config,
                )

        schema = _build_schema()
        schema = self.add_suggested_values_to_schema(schema, subentry.data)

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=schema,
            errors=errors,
        )
