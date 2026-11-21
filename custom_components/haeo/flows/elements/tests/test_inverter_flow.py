"""Tests for inverter element config flow."""

from types import MappingProxyType
from typing import (
    Any,  # noqa: TID251  # element flows are created from the registry, which a static flow type cannot express
)
from unittest.mock import Mock

from homeassistant.config_entries import SOURCE_RECONFIGURE, ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from conftest import add_participant
from custom_components.haeo.core.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.core.schema import (
    SchemaValue,
    as_connection_target,
    as_constant_value,
    as_entity_value,
    as_none_value,
)
from custom_components.haeo.core.schema.elements import node
from custom_components.haeo.core.schema.elements.inverter import (
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_MAX_POWER_TARGET_SOURCE,
    ELEMENT_TYPE,
    SECTION_EFFICIENCY,
    SECTION_POWER_LIMITS,
)
from custom_components.haeo.core.schema.sections import CONF_CONNECTION
from custom_components.haeo.flows.conftest import create_flow, section_suggested_values

CONF_MAX_POWER_DC_TO_AC = CONF_MAX_POWER_SOURCE_TARGET
CONF_MAX_POWER_AC_TO_DC = CONF_MAX_POWER_TARGET_SOURCE


def _inverter_input(dc_to_ac: SchemaValue, ac_to_dc: SchemaValue) -> dict[str, object]:
    """Build the inverter form's submitted values."""
    return {
        CONF_NAME: "Test Inverter",
        CONF_CONNECTION: "TestNode",
        SECTION_POWER_LIMITS: {CONF_MAX_POWER_DC_TO_AC: dc_to_ac, CONF_MAX_POWER_AC_TO_DC: ac_to_dc},
        SECTION_EFFICIENCY: {},
    }


def _add_inverter(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
    dc_to_ac: SchemaValue,
    ac_to_dc: SchemaValue,
    *,
    connection: str = "TestNode",
) -> ConfigSubentry:
    """Add a stored inverter."""
    subentry = ConfigSubentry(
        data=MappingProxyType(
            {
                CONF_ELEMENT_TYPE: ELEMENT_TYPE,
                **_inverter_input(dc_to_ac, ac_to_dc),
                CONF_CONNECTION: as_connection_target(connection),
            }
        ),
        subentry_type=ELEMENT_TYPE,
        title="Test Inverter",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, subentry)
    return subentry


def _reconfigure_flow(hass: HomeAssistant, hub_entry: MockConfigEntry, subentry: ConfigSubentry) -> Any:
    """Create a flow reconfiguring the given inverter."""
    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.context = {"subentry_id": subentry.subentry_id, "source": SOURCE_RECONFIGURE}
    flow._get_reconfigure_subentry = Mock(return_value=subentry)
    flow.async_update_and_abort = Mock(return_value={"type": FlowResultType.ABORT, "reason": "reconfigure_successful"})
    return flow


@pytest.mark.parametrize(
    ("dc_to_ac", "ac_to_dc", "add_node"),
    [
        pytest.param(
            as_entity_value(["sensor.dc_to_ac_power"]),
            as_entity_value(["sensor.ac_to_dc_power"]),
            True,
            id="entity_values",
        ),
        pytest.param(as_constant_value(10.0), as_constant_value(8.0), True, id="constant_values"),
        pytest.param(
            as_entity_value(["sensor.dc1", "sensor.dc2"]), as_entity_value(["sensor.ac"]), True, id="entity_list"
        ),
        pytest.param(as_constant_value(10.0), as_constant_value(8.0), False, id="deleted_connection"),
    ],
)
async def test_reconfigure_form_opens_with_the_stored_values(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
    dc_to_ac: SchemaValue,
    ac_to_dc: SchemaValue,
    add_node: bool,
) -> None:
    """Reopening an inverter shows its stored values, ignoring subentries of unknown types."""
    if add_node:
        add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)

    unknown_subentry = ConfigSubentry(
        data=MappingProxyType({CONF_ELEMENT_TYPE: "unknown_type", CONF_NAME: "Unknown"}),
        subentry_type="unknown_type",
        title="Unknown",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, unknown_subentry)
    flow = _reconfigure_flow(hass, hub_entry, _add_inverter(hass, hub_entry, dc_to_ac, ac_to_dc))

    assert "Unknown" not in flow._get_participant_names()

    result = await flow.async_step_reconfigure(user_input=None)

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "user"
    assert section_suggested_values(result, SECTION_POWER_LIMITS) == {
        CONF_MAX_POWER_DC_TO_AC: dc_to_ac,
        CONF_MAX_POWER_AC_TO_DC: ac_to_dc,
    }


@pytest.mark.parametrize(
    ("dc_to_ac", "ac_to_dc"),
    [
        pytest.param(as_constant_value(10.0), as_constant_value(8.0), id="constant"),
        pytest.param(as_entity_value(["sensor.dc_power"]), as_entity_value(["sensor.ac_power"]), id="entity"),
    ],
)
async def test_user_step_stores_submitted_values(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
    dc_to_ac: SchemaValue,
    ac_to_dc: SchemaValue,
) -> None:
    """A new inverter stores its power limits as submitted, and a missing limit is reported on its section."""
    add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)
    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.async_create_entry = Mock(
        return_value={"type": FlowResultType.CREATE_ENTRY, "title": "Test Inverter", "data": {}}
    )

    assert flow._get_current_subentry_id() is None

    invalid_result = await flow.async_step_user(user_input=_inverter_input(as_none_value(), ac_to_dc))
    assert invalid_result.get("type") == FlowResultType.FORM
    assert invalid_result.get("step_id") == "user"
    assert invalid_result.get("errors") == {SECTION_POWER_LIMITS: "required"}

    result = await flow.async_step_user(user_input=_inverter_input(dc_to_ac, ac_to_dc))

    assert result.get("type") == FlowResultType.CREATE_ENTRY
    assert flow.async_create_entry.call_args.kwargs["data"][SECTION_POWER_LIMITS] == {
        CONF_MAX_POWER_DC_TO_AC: dc_to_ac,
        CONF_MAX_POWER_AC_TO_DC: ac_to_dc,
    }


async def test_reconfigure_with_constant_updates_entry(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """Reconfiguring an inverter from sensors to constants stores the constants."""
    add_participant(hass, hub_entry, "TestNode", node.ELEMENT_TYPE)
    subentry = _add_inverter(
        hass, hub_entry, as_entity_value(["sensor.dc_power"]), as_entity_value(["sensor.ac_power"])
    )
    flow = _reconfigure_flow(hass, hub_entry, subentry)

    invalid_result = await flow.async_step_reconfigure(
        user_input=_inverter_input(as_none_value(), as_entity_value(["sensor.ac_power"]))
    )
    assert invalid_result.get("type") == FlowResultType.FORM
    assert invalid_result.get("step_id") == "user"
    assert invalid_result.get("errors") == {SECTION_POWER_LIMITS: "required"}

    result = await flow.async_step_reconfigure(
        user_input=_inverter_input(as_constant_value(10.0), as_constant_value(8.0))
    )

    assert result.get("type") == FlowResultType.ABORT
    assert result.get("reason") == "reconfigure_successful"
    assert flow.async_update_and_abort.call_args.kwargs["data"][SECTION_POWER_LIMITS] == {
        CONF_MAX_POWER_DC_TO_AC: as_constant_value(10.0),
        CONF_MAX_POWER_AC_TO_DC: as_constant_value(8.0),
    }
