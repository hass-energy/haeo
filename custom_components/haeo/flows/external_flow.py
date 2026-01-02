"""Base classes for external step config flows.

This module provides a mixin and base handler for config flows that redirect
to the React webapp using Home Assistant's external step pattern.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from homeassistant.config_entries import ConfigSubentryFlow, SubentryFlowResult

from custom_components.haeo.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.flows.element_flow import ElementFlowMixin
from custom_components.haeo.flows.external import get_element_external_url

if TYPE_CHECKING:
    from custom_components.haeo.elements.input_fields import InputFieldInfo


class ExternalSubentryFlowHandler(ElementFlowMixin, ConfigSubentryFlow):
    """Base handler for element flows using external step pattern.

    Subclasses must define:
    - ELEMENT_TYPE: The element type string (e.g., "battery")
    - CONFIG_SCHEMA: The TypedDict schema class for the element config
    - INPUT_FIELDS: Tuple of InputFieldInfo for the element

    The flow redirects to the React webapp which collects all configuration
    in a single form, then submits back via websocket.
    """

    # Subclasses must override these
    ELEMENT_TYPE: ClassVar[str]
    CONFIG_SCHEMA: ClassVar[type]
    INPUT_FIELDS: ClassVar[tuple[InputFieldInfo[Any], ...]]

    # External step pattern doesn't use multi-step
    has_value_source_step: ClassVar[bool] = False

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle the user step - redirect to React webapp or process submission.

        First call (user_input=None): Redirect to React webapp.
        Callback (user_input provided): Validate and create entry.
        """
        if user_input is None:
            # Redirect to React webapp
            url = get_element_external_url(
                self.hass,
                flow_id=self.flow_id,
                entry_id=self._get_entry().entry_id,
                subentry_type=self.ELEMENT_TYPE,
            )
            return self.async_external_step(step_id="user", url=url)

        # Process submission from React webapp
        return await self._process_user_input(user_input)

    async def async_step_finish(self, _user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle the finish step after external step is done."""
        # This step is called after async_external_step_done
        # The actual data processing happens in the callback to async_step_user
        # when the React app submits via config_entries/flow websocket command
        return self.async_abort(reason="external_step_complete")

    async def _process_user_input(self, user_input: dict[str, Any]) -> SubentryFlowResult:
        """Process and validate user input from React webapp.

        Args:
            user_input: Complete configuration from React webapp.

        Returns:
            Entry creation result or error.

        """
        errors: dict[str, str] = {}

        # Validate name
        name = user_input.get(CONF_NAME)
        if not self._validate_name(name, errors):
            # Return external step done with error - webapp will show error
            return self.async_abort(reason="validation_failed")

        # Build config with element type
        config: dict[str, Any] = {
            CONF_ELEMENT_TYPE: self.ELEMENT_TYPE,
            **user_input,
        }

        return self.async_create_entry(
            title=str(name),
            data=config,
        )

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> SubentryFlowResult:
        """Handle reconfiguration - redirect to React webapp with existing data.

        First call (user_input=None): Redirect to React webapp.
        Callback (user_input provided): Validate and update entry.
        """
        subentry = self._get_reconfigure_subentry()

        if user_input is None:
            # Redirect to React webapp with subentry ID
            url = get_element_external_url(
                self.hass,
                flow_id=self.flow_id,
                entry_id=self._get_entry().entry_id,
                subentry_type=self.ELEMENT_TYPE,
                subentry_id=subentry.subentry_id,
            )
            return self.async_external_step(step_id="reconfigure", url=url)

        # Process submission from React webapp
        return await self._process_reconfigure_input(user_input, subentry)

    async def _process_reconfigure_input(
        self,
        user_input: dict[str, Any],
        subentry: Any,  # ConfigSubentry
    ) -> SubentryFlowResult:
        """Process and validate reconfigure input from React webapp.

        Args:
            user_input: Updated configuration from React webapp.
            subentry: The subentry being reconfigured.

        Returns:
            Entry update result or error.

        """
        errors: dict[str, str] = {}

        # Validate name
        name = user_input.get(CONF_NAME)
        if not self._validate_name(name, errors):
            return self.async_abort(reason="validation_failed")

        # Build config with element type
        config: dict[str, Any] = {
            CONF_ELEMENT_TYPE: self.ELEMENT_TYPE,
            **user_input,
        }

        return self.async_update_and_abort(
            self._get_entry(),
            subentry,
            title=str(name),
            data=config,
        )


__all__ = ["ExternalSubentryFlowHandler"]
