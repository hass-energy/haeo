"""Tests for finding the errors, aborts, and steps a flow can show."""

from homeassistant.config_entries import ConfigSubentryFlow, SubentryFlowResult

from custom_components.haeo.flows.element_flow import ElementFlowMixin
from custom_components.haeo.translations.tests.flow_messages import FlowMessages, flow_messages

STEP_DETAILS = "details"


class NameOnlyFlow(ElementFlowMixin, ConfigSubentryFlow):
    """A flow that validates its name but never an endpoint."""

    async def async_step_user(self, user_input: dict[str, object] | None = None) -> SubentryFlowResult:
        """Validate the name and show the form."""
        errors: dict[str, str] = {}
        if user_input is not None:
            self._validate_name(None, errors)
        return self.async_show_form(step_id=STEP_DETAILS, errors=errors)


class EndpointFlow(NameOnlyFlow):
    """A flow that also validates its endpoint and can finish a reconfigure."""

    async def async_step_reconfigure(
        self,
        user_input: dict[str, object] | None = None,  # noqa: ARG002 (required by ConfigSubentryFlow interface)
    ) -> SubentryFlowResult:
        """Validate the endpoint, then save."""
        errors: dict[str, str] = {}
        self._validate_endpoint(None, "connection", errors)
        if errors:
            errors["base"] = "endpoint_rejected"
            return self.async_show_form(step_id="user", errors=errors)
        return self.async_update_and_abort(self._get_entry(), self._get_reconfigure_subentry())


def test_inherited_helpers_count_only_when_a_step_reaches_them() -> None:
    """An error returned by a shared helper the flow never calls is not one the flow shows."""
    assert flow_messages(NameOnlyFlow) == FlowMessages(
        errors={"missing_name", "name_exists"}, aborts=set(), steps={STEP_DETAILS}
    )


def test_errors_aborts_and_steps_follow_calls_into_shared_and_home_assistant_code() -> None:
    """Errors from shared helpers and abort reasons from Home Assistant's base flow are found."""
    assert flow_messages(EndpointFlow) == FlowMessages(
        errors={"missing_name", "name_exists", "invalid_endpoint", "endpoint_rejected"},
        aborts={"reconfigure_successful"},
        steps={STEP_DETAILS, "user"},
    )
