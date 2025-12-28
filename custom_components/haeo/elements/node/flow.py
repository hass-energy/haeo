"""Node element configuration flows."""

from typing import Any, cast

from homeassistant.config_entries import ConfigSubentryFlow, SubentryFlowResult
from homeassistant.helpers.selector import BooleanSelector, BooleanSelectorConfig, TextSelector, TextSelectorConfig
import voluptuous as vol

from custom_components.haeo.const import CONF_ELEMENT_TYPE, CONF_NAME

from .schema import CONF_IS_SINK, CONF_IS_SOURCE, DEFAULT_IS_SINK, DEFAULT_IS_SOURCE, ELEMENT_TYPE, NodeConfigSchema


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
            vol.Optional(CONF_IS_SOURCE, default=DEFAULT_IS_SOURCE): vol.All(
                vol.Coerce(bool),
                BooleanSelector(BooleanSelectorConfig()),
            ),
            vol.Optional(CONF_IS_SINK, default=DEFAULT_IS_SINK): vol.All(
                vol.Coerce(bool),
                BooleanSelector(BooleanSelectorConfig()),
            ),
        }
    )


class NodeSubentryFlowHandler(ConfigSubentryFlow):
    """Handle node element configuration flows."""

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle adding a new node element."""
        errors: dict[str, str] = {}

        if user_input is not None:
            name = user_input.get(CONF_NAME)
            if not name:
                errors[CONF_NAME] = "missing_name"
            elif name in self._get_used_names():
                errors[CONF_NAME] = "name_exists"

            if not errors:
                config = cast("NodeConfigSchema", {CONF_ELEMENT_TYPE: ELEMENT_TYPE, **user_input})
                return self.async_create_entry(title=name, data=config)

        schema = _build_schema()
        schema = self.add_suggested_values_to_schema(
            schema,
            {CONF_IS_SOURCE: DEFAULT_IS_SOURCE, CONF_IS_SINK: DEFAULT_IS_SINK},
        )

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
            if not name:
                errors[CONF_NAME] = "missing_name"
            elif name in self._get_used_names():
                errors[CONF_NAME] = "name_exists"

            if not errors:
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

    def _get_used_names(self) -> set[str]:
        """Return all configured element names excluding the current subentry."""
        current_id = self._get_current_subentry_id()
        return {
            subentry.title for subentry in self._get_entry().subentries.values() if subentry.subentry_id != current_id
        }

    def _get_current_subentry_id(self) -> str | None:
        """Return the active subentry ID when reconfiguring, otherwise None."""
        try:
            return self._get_reconfigure_subentry().subentry_id
        except Exception:
            return None
