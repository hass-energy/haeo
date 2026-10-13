"""Tests for battery element config flow."""

from collections.abc import Mapping
from types import MappingProxyType
from unittest.mock import Mock

from homeassistant.config_entries import SOURCE_RECONFIGURE, ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from conftest import add_participant
from custom_components.haeo.core.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.core.schema import as_connection_target, as_constant_value, as_entity_value
from custom_components.haeo.core.schema.elements import node
from custom_components.haeo.core.schema.elements.battery import (
    CONF_CAPACITY,
    CONF_COST,
    CONF_DIRECTION,
    CONF_EFFICIENCY_SOURCE_TARGET,
    CONF_EFFICIENCY_TARGET_SOURCE,
    CONF_ENABLED,
    CONF_HOLDING_COST_NAME,
    CONF_HOLDING_COSTS,
    CONF_INITIAL_CHARGE_PERCENTAGE,
    CONF_MAX_CHARGE_PERCENTAGE,
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_MAX_POWER_TARGET_SOURCE,
    CONF_MIN_CHARGE_PERCENTAGE,
    CONF_SALVAGE_VALUE,
    CONF_THRESHOLD,
    ELEMENT_TYPE,
    SECTION_EFFICIENCY,
    SECTION_LIMITS,
    SECTION_POWER_LIMITS,
    SECTION_PRICING,
    SECTION_STORAGE,
)
from custom_components.haeo.core.schema.sections import CONF_CONNECTION
from custom_components.haeo.elements import get_input_fields
from custom_components.haeo.flows.conftest import create_flow


def _wrap_main_input(user_input: Mapping[str, object], *, as_schema: bool = False) -> dict[str, object]:
    """Wrap battery user input into sectioned form data."""
    common = {
        key: user_input[key]
        for key in (
            CONF_NAME,
            CONF_CONNECTION,
        )
        if key in user_input
    }
    connection = common.get(CONF_CONNECTION)
    if as_schema and isinstance(connection, str):
        common[CONF_CONNECTION] = as_connection_target(connection)
    pricing = {key: user_input[key] for key in (CONF_SALVAGE_VALUE,) if key in user_input}
    pricing.setdefault(CONF_SALVAGE_VALUE, 0.0)

    return {
        **common,
        SECTION_STORAGE: {
            key: user_input[key]
            for key in (
                CONF_CAPACITY,
                CONF_INITIAL_CHARGE_PERCENTAGE,
            )
            if key in user_input
        },
        SECTION_LIMITS: {
            key: user_input[key]
            for key in (
                CONF_MIN_CHARGE_PERCENTAGE,
                CONF_MAX_CHARGE_PERCENTAGE,
            )
            if key in user_input
        },
        SECTION_POWER_LIMITS: {
            key: user_input[key]
            for key in (
                CONF_MAX_POWER_SOURCE_TARGET,
                CONF_MAX_POWER_TARGET_SOURCE,
            )
            if key in user_input
        },
        SECTION_PRICING: pricing,
        SECTION_EFFICIENCY: {
            key: user_input[key]
            for key in (CONF_EFFICIENCY_SOURCE_TARGET, CONF_EFFICIENCY_TARGET_SOURCE)
            if key in user_input
        },
    }


def _holding_cost(name: str, direction: str = "below") -> dict[str, object]:
    """Return a stored holding cost."""
    return {
        CONF_HOLDING_COST_NAME: name,
        CONF_ENABLED: True,
        CONF_DIRECTION: direction,
        CONF_THRESHOLD: as_constant_value(20.0),
        CONF_COST: as_constant_value(0.02),
    }


def _add_battery(
    hass: HomeAssistant, hub_entry: MockConfigEntry, holding_costs: list[dict[str, object]]
) -> ConfigSubentry:
    """Add a battery subentry with the given holding costs."""
    add_participant(hass, hub_entry, "main_bus", node.ELEMENT_TYPE)
    data: dict[str, object] = {
        CONF_ELEMENT_TYPE: ELEMENT_TYPE,
        **_wrap_main_input(
            {
                CONF_NAME: "Test Battery",
                CONF_CONNECTION: "main_bus",
                CONF_CAPACITY: as_constant_value(10.0),
                CONF_INITIAL_CHARGE_PERCENTAGE: as_constant_value(50.0),
            },
            as_schema=True,
        ),
    }
    if holding_costs:
        data[CONF_HOLDING_COSTS] = holding_costs
    subentry = ConfigSubentry(
        data=MappingProxyType(data),
        subentry_type=ELEMENT_TYPE,
        title="Test Battery",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, subentry)
    return subentry


def _reconfigure_flow(hass: HomeAssistant, hub_entry: MockConfigEntry, subentry: ConfigSubentry) -> Mock:
    """Create a battery reconfigure flow for the subentry that records its update."""
    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.context = {"subentry_id": subentry.subentry_id, "source": SOURCE_RECONFIGURE}
    flow._get_reconfigure_subentry = Mock(return_value=subentry)
    flow.async_update_and_abort = Mock(return_value={"type": FlowResultType.ABORT, "reason": "reconfigure_successful"})
    return flow


def _saved_holding_costs(flow: Mock) -> object:
    """Return the holding costs the flow saved, or None when it saved none."""
    return flow.async_update_and_abort.call_args.kwargs["data"].get(CONF_HOLDING_COSTS)


async def test_user_step_with_constant_values_creates_entry(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """Submitting with constant values should create entry directly."""
    add_participant(hass, hub_entry, "main_bus", node.ELEMENT_TYPE)
    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)

    flow.async_create_entry = Mock(
        return_value={
            "type": FlowResultType.CREATE_ENTRY,
            "title": "Test Battery",
            "data": {},
        }
    )

    user_input = {
        CONF_NAME: "Test Battery",
        CONF_CONNECTION: "main_bus",
        CONF_CAPACITY: 10.0,
        CONF_INITIAL_CHARGE_PERCENTAGE: ["sensor.battery_soc"],
        CONF_MIN_CHARGE_PERCENTAGE: None,
        CONF_MAX_CHARGE_PERCENTAGE: None,
        CONF_EFFICIENCY_SOURCE_TARGET: 0.95,
        CONF_EFFICIENCY_TARGET_SOURCE: 0.95,
        CONF_MAX_POWER_TARGET_SOURCE: 5.0,
        CONF_MAX_POWER_SOURCE_TARGET: 5.0,
    }

    invalid_input = {**user_input, CONF_CAPACITY: []}
    result = await flow.async_step_user(user_input=_wrap_main_input(invalid_input))
    assert result.get("type") == FlowResultType.FORM
    assert CONF_CAPACITY in result.get("errors", {})

    result = await flow.async_step_user(user_input=_wrap_main_input(user_input))
    assert result.get("type") == FlowResultType.CREATE_ENTRY

    created_data = flow.async_create_entry.call_args.kwargs["data"]
    assert created_data["storage"][CONF_CAPACITY] == as_constant_value(10.0)
    assert created_data["storage"][CONF_INITIAL_CHARGE_PERCENTAGE] == as_entity_value(["sensor.battery_soc"])
    assert created_data["power_limits"][CONF_MAX_POWER_TARGET_SOURCE] == as_constant_value(5.0)


async def test_user_step_with_entity_values_creates_entry(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """Submitting with entity selections should create entry with entity IDs."""
    add_participant(hass, hub_entry, "main_bus", node.ELEMENT_TYPE)
    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)

    flow.async_create_entry = Mock(
        return_value={
            "type": FlowResultType.CREATE_ENTRY,
            "title": "Test Battery",
            "data": {},
        }
    )

    user_input = {
        CONF_NAME: "Test Battery",
        CONF_CONNECTION: "main_bus",
        CONF_CAPACITY: ["sensor.capacity"],
        CONF_INITIAL_CHARGE_PERCENTAGE: ["sensor.battery_soc"],
        CONF_MIN_CHARGE_PERCENTAGE: None,
        CONF_MAX_CHARGE_PERCENTAGE: None,
        CONF_EFFICIENCY_SOURCE_TARGET: None,
        CONF_EFFICIENCY_TARGET_SOURCE: None,
        CONF_MAX_POWER_TARGET_SOURCE: ["sensor.max_charge"],
        CONF_MAX_POWER_SOURCE_TARGET: ["sensor.max_discharge"],
    }

    result = await flow.async_step_user(user_input=_wrap_main_input(user_input))
    assert result.get("type") == FlowResultType.CREATE_ENTRY

    created_data = flow.async_create_entry.call_args.kwargs["data"]
    assert created_data["storage"][CONF_CAPACITY] == as_entity_value(["sensor.capacity"])
    assert created_data["storage"][CONF_INITIAL_CHARGE_PERCENTAGE] == as_entity_value(["sensor.battery_soc"])
    assert created_data["power_limits"][CONF_MAX_POWER_TARGET_SOURCE] == as_entity_value(["sensor.max_charge"])


@pytest.mark.parametrize(
    ("holding_costs", "expected_options"),
    [
        pytest.param([], ["user", "add_holding_cost"], id="without_holding_costs"),
        pytest.param(
            [_holding_cost("Reserve")], ["user", "add_holding_cost", "manage_holding_costs"], id="with_holding_costs"
        ),
    ],
)
async def test_reconfigure_shows_menu(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
    holding_costs: list[dict[str, object]],
    expected_options: list[str],
) -> None:
    """Reconfiguring offers the settings and adding a holding cost, and managing them once there are any."""
    flow = _reconfigure_flow(hass, hub_entry, _add_battery(hass, hub_entry, holding_costs))

    result = await flow.async_step_reconfigure()

    assert result.get("type") == FlowResultType.MENU
    assert result.get("menu_options") == expected_options


async def test_add_holding_cost_appends_to_battery(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """Adding a holding cost keeps the existing ones and stores entity and constant values."""
    flow = _reconfigure_flow(hass, hub_entry, _add_battery(hass, hub_entry, [_holding_cost("Reserve")]))

    result = await flow.async_step_add_holding_cost()
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "add_holding_cost"

    result = await flow.async_step_add_holding_cost(
        {
            CONF_HOLDING_COST_NAME: "Headroom",
            CONF_ENABLED: False,
            CONF_DIRECTION: "above",
            CONF_THRESHOLD: 90.0,
            CONF_COST: ["sensor.headroom_cost"],
        }
    )

    assert result.get("type") == FlowResultType.ABORT
    assert _saved_holding_costs(flow) == [
        _holding_cost("Reserve"),
        {
            CONF_HOLDING_COST_NAME: "Headroom",
            CONF_ENABLED: False,
            CONF_DIRECTION: "above",
            CONF_THRESHOLD: as_constant_value(90.0),
            CONF_COST: as_entity_value(["sensor.headroom_cost"]),
        },
    ]


@pytest.mark.parametrize(
    ("user_input", "expected_errors"),
    [
        pytest.param(
            {CONF_HOLDING_COST_NAME: "", CONF_THRESHOLD: 20.0, CONF_COST: 0.02},
            {CONF_HOLDING_COST_NAME: "missing_name"},
            id="missing_name",
        ),
        pytest.param(
            {CONF_HOLDING_COST_NAME: "Reserve", CONF_THRESHOLD: 20.0, CONF_COST: 0.02},
            {CONF_HOLDING_COST_NAME: "holding_cost_name_exists"},
            id="duplicate_name",
        ),
        pytest.param(
            {CONF_HOLDING_COST_NAME: "Headroom", CONF_THRESHOLD: [], CONF_COST: ""},
            {CONF_THRESHOLD: "required", CONF_COST: "required"},
            id="missing_values",
        ),
    ],
)
async def test_add_holding_cost_rejects_invalid_input(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
    user_input: dict[str, object],
    expected_errors: dict[str, str],
) -> None:
    """Invalid holding costs show the form again with errors and save nothing."""
    flow = _reconfigure_flow(hass, hub_entry, _add_battery(hass, hub_entry, [_holding_cost("Reserve")]))

    result = await flow.async_step_add_holding_cost({CONF_ENABLED: True, CONF_DIRECTION: "below", **user_input})

    assert result.get("type") == FlowResultType.FORM
    assert result.get("errors") == expected_errors
    flow.async_update_and_abort.assert_not_called()


@pytest.mark.parametrize(
    ("currency", "expected_unit"),
    [
        pytest.param("EUR", "€/kWh/h", id="euro"),
        pytest.param("AUD", "$/kWh/h", id="dollar"),
        pytest.param("XYZ", "XYZ/kWh/h", id="unlisted_code"),
    ],
)
async def test_holding_cost_shows_currency_symbol(
    hass: HomeAssistant, hub_entry: MockConfigEntry, currency: str, expected_unit: str
) -> None:
    """The holding cost shows its holding-rate unit in the Home Assistant currency."""
    hass.config.currency = currency
    flow = _reconfigure_flow(hass, hub_entry, _add_battery(hass, hub_entry, []))

    result = await flow.async_step_add_holding_cost()

    cost_selector = next(selector for key, selector in result["data_schema"].schema.items() if key.schema == CONF_COST)
    number_config = cost_selector.config["choices"]["constant"]["selector"]["number"]
    assert number_config["unit_of_measurement"] == expected_unit


@pytest.mark.parametrize(
    ("holding_costs", "expected"),
    [
        pytest.param(
            [_holding_cost("Reserve"), _holding_cost("Headroom", "above")],
            [_holding_cost("Headroom", "above")],
            id="keeps_the_others",
        ),
        pytest.param([_holding_cost("Reserve")], None, id="removes_the_last"),
    ],
)
async def test_manage_holding_costs_deletes(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
    holding_costs: list[dict[str, object]],
    expected: object,
) -> None:
    """Deleting a holding cost keeps the others, and removes the list with the last one."""
    flow = _reconfigure_flow(hass, hub_entry, _add_battery(hass, hub_entry, holding_costs))

    result = await flow.async_step_manage_holding_costs()
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "manage_holding_costs"

    result = await flow.async_step_manage_holding_costs({"holding_cost": "0", "action": "delete"})

    assert result.get("type") == FlowResultType.ABORT
    assert _saved_holding_costs(flow) == expected


async def test_manage_holding_costs_edits(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """Editing a holding cost shows its stored values and replaces it in place."""
    flow = _reconfigure_flow(
        hass,
        hub_entry,
        _add_battery(hass, hub_entry, [_holding_cost("Reserve"), _holding_cost("Headroom", "above")]),
    )

    result = await flow.async_step_manage_holding_costs({"holding_cost": "0", "action": "edit"})
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "edit_holding_cost"
    suggested = {
        key.schema: key.description["suggested_value"]
        for key in result["data_schema"].schema
        if key.description and "suggested_value" in key.description
    }
    assert suggested == {
        CONF_HOLDING_COST_NAME: "Reserve",
        CONF_ENABLED: True,
        CONF_DIRECTION: "below",
        CONF_THRESHOLD: 20.0,
        CONF_COST: 0.02,
    }

    result = await flow.async_step_edit_holding_cost(
        {
            CONF_HOLDING_COST_NAME: "Reserve",
            CONF_ENABLED: True,
            CONF_DIRECTION: "below",
            CONF_THRESHOLD: 30.0,
            CONF_COST: 0.02,
        }
    )

    assert result.get("type") == FlowResultType.ABORT
    assert _saved_holding_costs(flow) == [
        {**_holding_cost("Reserve"), CONF_THRESHOLD: as_constant_value(30.0)},
        _holding_cost("Headroom", "above"),
    ]


@pytest.mark.parametrize(
    ("connection", "add_connection", "config_values", "expected_defaults"),
    [
        pytest.param(
            "main_bus",
            True,
            {
                CONF_NAME: "Test Battery",
                CONF_CONNECTION: "main_bus",
                CONF_CAPACITY: as_entity_value(["sensor.battery_capacity"]),
                CONF_INITIAL_CHARGE_PERCENTAGE: as_entity_value(["sensor.battery_soc"]),
                CONF_MAX_POWER_TARGET_SOURCE: as_entity_value(["sensor.charge_power"]),
                CONF_MAX_POWER_SOURCE_TARGET: as_entity_value(["sensor.discharge_power"]),
            },
            {
                SECTION_STORAGE: {
                    CONF_CAPACITY: ["sensor.battery_capacity"],
                    CONF_INITIAL_CHARGE_PERCENTAGE: ["sensor.battery_soc"],
                },
                SECTION_POWER_LIMITS: {
                    CONF_MAX_POWER_TARGET_SOURCE: ["sensor.charge_power"],
                    CONF_MAX_POWER_SOURCE_TARGET: ["sensor.discharge_power"],
                },
            },
            id="entity_values",
        ),
        pytest.param(
            "DeletedNode",
            False,
            {
                CONF_NAME: "Test Battery",
                CONF_CONNECTION: "DeletedNode",
                CONF_CAPACITY: as_constant_value(10.0),
                CONF_INITIAL_CHARGE_PERCENTAGE: as_constant_value(50.0),
                CONF_MAX_POWER_TARGET_SOURCE: as_constant_value(5.0),
                CONF_EFFICIENCY_SOURCE_TARGET: as_constant_value(0.95),
                CONF_EFFICIENCY_TARGET_SOURCE: as_constant_value(0.95),
            },
            {
                SECTION_STORAGE: {
                    CONF_CAPACITY: 10.0,
                    CONF_INITIAL_CHARGE_PERCENTAGE: 50.0,
                },
                SECTION_POWER_LIMITS: {
                    CONF_MAX_POWER_TARGET_SOURCE: 5.0,
                },
                SECTION_EFFICIENCY: {
                    CONF_EFFICIENCY_SOURCE_TARGET: 0.95,
                    CONF_EFFICIENCY_TARGET_SOURCE: 0.95,
                },
            },
            id="constant_values_deleted_connection",
        ),
    ],
)
async def test_reconfigure_defaults_handle_schema_values(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
    connection: str,
    add_connection: bool,
    config_values: dict[str, object],
    expected_defaults: dict[str, dict[str, object]],
) -> None:
    """Reconfigure defaults reflect schema values and tolerate missing connections."""
    if add_connection:
        add_participant(hass, hub_entry, connection, node.ELEMENT_TYPE)

    existing_config = {
        CONF_ELEMENT_TYPE: ELEMENT_TYPE,
        **_wrap_main_input(config_values, as_schema=True),
    }
    existing_subentry = ConfigSubentry(
        data=MappingProxyType(existing_config),
        subentry_type=ELEMENT_TYPE,
        title="Test Battery",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, existing_subentry)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.context = {
        "subentry_id": existing_subentry.subentry_id,
        "source": SOURCE_RECONFIGURE,
    }
    flow._get_reconfigure_subentry = Mock(return_value=existing_subentry)

    result = await flow.async_step_user(user_input=None)

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "user"

    input_fields = get_input_fields({CONF_ELEMENT_TYPE: ELEMENT_TYPE})
    defaults = flow._build_defaults("Test Battery", input_fields, dict(existing_subentry.data))

    for section, values in expected_defaults.items():
        for key, expected in values.items():
            assert defaults[section][key] == expected


async def test_reconfigure_updates_existing_battery(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """Editing the battery settings updates the battery and keeps its holding costs."""
    flow = _reconfigure_flow(hass, hub_entry, _add_battery(hass, hub_entry, [_holding_cost("Reserve")]))

    result = await flow.async_step_user(user_input=None)
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "user"

    user_input = {
        CONF_NAME: "Test Battery Updated",
        CONF_CONNECTION: "main_bus",
        CONF_CAPACITY: 15.0,
        CONF_INITIAL_CHARGE_PERCENTAGE: ["sensor.battery_soc"],
        CONF_MIN_CHARGE_PERCENTAGE: None,
        CONF_MAX_CHARGE_PERCENTAGE: None,
        CONF_EFFICIENCY_SOURCE_TARGET: None,
        CONF_EFFICIENCY_TARGET_SOURCE: None,
        CONF_MAX_POWER_TARGET_SOURCE: 7.5,
        CONF_MAX_POWER_SOURCE_TARGET: 7.5,
    }

    result = await flow.async_step_user(user_input=_wrap_main_input(user_input))
    assert result.get("type") == FlowResultType.ABORT
    assert result.get("reason") == "reconfigure_successful"

    update_kwargs = flow.async_update_and_abort.call_args.kwargs
    assert update_kwargs["title"] == "Test Battery Updated"
    assert update_kwargs["data"][SECTION_STORAGE][CONF_CAPACITY] == as_constant_value(15.0)
    assert update_kwargs["data"][SECTION_POWER_LIMITS][CONF_MAX_POWER_TARGET_SOURCE] == as_constant_value(7.5)
    assert update_kwargs["data"][CONF_HOLDING_COSTS] == [_holding_cost("Reserve")]


# --- Tests for _is_valid_choose_value ---
