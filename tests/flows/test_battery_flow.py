"""Tests for battery element config flow."""

from types import MappingProxyType
from typing import Any, cast
from unittest.mock import Mock

from homeassistant.config_entries import SOURCE_RECONFIGURE, ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.core.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.core.schema import as_connection_target, as_constant_value, as_entity_value
from custom_components.haeo.core.schema.elements import node
from custom_components.haeo.core.schema.elements.battery import (
    CONF_CAPACITY,
    CONF_CONFIGURE_PARTITIONS,
    CONF_EFFICIENCY_SOURCE_TARGET,
    CONF_EFFICIENCY_TARGET_SOURCE,
    CONF_INITIAL_CHARGE_PERCENTAGE,
    CONF_MAX_CHARGE_PERCENTAGE,
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_MAX_POWER_TARGET_SOURCE,
    CONF_MIN_CHARGE_PERCENTAGE,
    CONF_PARTITION_COST,
    CONF_PARTITION_PERCENTAGE,
    CONF_PRICE_SOURCE_TARGET,
    CONF_PRICE_TARGET_SOURCE,
    CONF_SALVAGE_VALUE,
    ELEMENT_TYPE,
    SECTION_EFFICIENCY,
    SECTION_LIMITS,
    SECTION_OVERCHARGE,
    SECTION_PARTITIONING,
    SECTION_POWER_LIMITS,
    SECTION_PRICING,
    SECTION_STORAGE,
    SECTION_UNDERCHARGE,
)
from custom_components.haeo.core.schema.sections import CONF_CONNECTION
from custom_components.haeo.elements import get_input_fields
from tests.conftest import add_participant

from .conftest import create_flow


def _wrap_main_input(user_input: dict[str, Any], *, as_schema: bool = False) -> dict[str, Any]:
    """Wrap battery user input into sectioned form data."""
    common = {
        key: user_input[key]
        for key in (
            CONF_NAME,
            CONF_CONNECTION,
        )
        if key in user_input
    }
    has_schema_values = any(isinstance(value, dict) and "type" in value for value in user_input.values())
    if (as_schema or has_schema_values) and isinstance(common.get(CONF_CONNECTION), str):
        common[CONF_CONNECTION] = as_connection_target(common[CONF_CONNECTION])
    pricing = {
        key: user_input[key]
        for key in (
            CONF_PRICE_SOURCE_TARGET,
            CONF_PRICE_TARGET_SOURCE,
            CONF_SALVAGE_VALUE,
        )
        if key in user_input
    }
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
        SECTION_PARTITIONING: {key: user_input[key] for key in (CONF_CONFIGURE_PARTITIONS,) if key in user_input},
    }


def _wrap_partition_input(
    undercharge_input: dict[str, Any],
    overcharge_input: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Wrap partition inputs into sectioned form data."""
    overcharge_input = overcharge_input or {}
    return {
        SECTION_UNDERCHARGE: {
            key: undercharge_input[key]
            for key in (CONF_PARTITION_PERCENTAGE, CONF_PARTITION_COST)
            if key in undercharge_input
        },
        SECTION_OVERCHARGE: {
            key: overcharge_input[key]
            for key in (CONF_PARTITION_PERCENTAGE, CONF_PARTITION_COST)
            if key in overcharge_input
        },
    }


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
        CONF_PRICE_TARGET_SOURCE: 0.001,
        CONF_PRICE_SOURCE_TARGET: None,
        CONF_CONFIGURE_PARTITIONS: False,
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
        CONF_PRICE_TARGET_SOURCE: None,
        CONF_PRICE_SOURCE_TARGET: None,
        CONF_CONFIGURE_PARTITIONS: False,
    }

    result = await flow.async_step_user(user_input=_wrap_main_input(user_input))
    assert result.get("type") == FlowResultType.CREATE_ENTRY

    created_data = flow.async_create_entry.call_args.kwargs["data"]
    assert created_data["storage"][CONF_CAPACITY] == as_entity_value(["sensor.capacity"])
    assert created_data["storage"][CONF_INITIAL_CHARGE_PERCENTAGE] == as_entity_value(["sensor.battery_soc"])
    assert created_data["power_limits"][CONF_MAX_POWER_TARGET_SOURCE] == as_entity_value(["sensor.max_charge"])


async def test_partition_flow_enabled_shows_partition_step(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """When configure_partitions is True, flow proceeds to partitions step."""
    add_participant(hass, hub_entry, "main_bus", node.ELEMENT_TYPE)
    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)

    step1_input = {
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
        CONF_PRICE_TARGET_SOURCE: None,
        CONF_PRICE_SOURCE_TARGET: None,
        CONF_CONFIGURE_PARTITIONS: True,
    }

    result = await flow.async_step_user(user_input=None)
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "user"

    result = await flow.async_step_user(user_input=_wrap_main_input(step1_input))
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "partitions"


async def test_partition_flow_with_entity_links_creates_entry(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """Complete flow with entity link partition values creates entry."""
    add_participant(hass, hub_entry, "main_bus", node.ELEMENT_TYPE)
    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)

    flow.async_create_entry = Mock(
        return_value={
            "type": FlowResultType.CREATE_ENTRY,
            "title": "Test Battery",
            "data": {},
        }
    )

    step1_input = {
        CONF_NAME: "Test Battery",
        CONF_CONNECTION: "main_bus",
        CONF_CAPACITY: 10.0,
        CONF_INITIAL_CHARGE_PERCENTAGE: ["sensor.battery_soc"],
        CONF_MIN_CHARGE_PERCENTAGE: None,
        CONF_MAX_CHARGE_PERCENTAGE: None,
        CONF_EFFICIENCY_SOURCE_TARGET: None,
        CONF_EFFICIENCY_TARGET_SOURCE: None,
        CONF_MAX_POWER_TARGET_SOURCE: 5.0,
        CONF_MAX_POWER_SOURCE_TARGET: 5.0,
        CONF_PRICE_TARGET_SOURCE: None,
        CONF_PRICE_SOURCE_TARGET: None,
        CONF_CONFIGURE_PARTITIONS: True,
    }

    await flow.async_step_user(user_input=_wrap_main_input(step1_input))

    partition_input = {
        CONF_PARTITION_PERCENTAGE: ["sensor.undercharge_pct"],
        CONF_PARTITION_COST: None,
    }
    partition_input_overcharge = {
        CONF_PARTITION_PERCENTAGE: ["sensor.overcharge_pct"],
        CONF_PARTITION_COST: None,
    }

    result = await flow.async_step_partitions(
        user_input=_wrap_partition_input(partition_input, partition_input_overcharge)
    )
    assert result.get("type") == FlowResultType.CREATE_ENTRY

    created_data = flow.async_create_entry.call_args.kwargs["data"]
    undercharge = created_data[SECTION_UNDERCHARGE]
    overcharge = created_data[SECTION_OVERCHARGE]
    assert undercharge[CONF_PARTITION_PERCENTAGE] == as_entity_value(["sensor.undercharge_pct"])
    assert overcharge[CONF_PARTITION_PERCENTAGE] == as_entity_value(["sensor.overcharge_pct"])


async def test_partition_flow_with_constant_values_creates_entry(
    hass: HomeAssistant, hub_entry: MockConfigEntry
) -> None:
    """Complete flow with constant partition values creates entry."""
    add_participant(hass, hub_entry, "main_bus", node.ELEMENT_TYPE)
    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)

    flow.async_create_entry = Mock(
        return_value={
            "type": FlowResultType.CREATE_ENTRY,
            "title": "Test Battery",
            "data": {},
        }
    )

    step1_input = {
        CONF_NAME: "Test Battery",
        CONF_CONNECTION: "main_bus",
        CONF_CAPACITY: 10.0,
        CONF_INITIAL_CHARGE_PERCENTAGE: ["sensor.battery_soc"],
        CONF_MIN_CHARGE_PERCENTAGE: None,
        CONF_MAX_CHARGE_PERCENTAGE: None,
        CONF_EFFICIENCY_SOURCE_TARGET: None,
        CONF_EFFICIENCY_TARGET_SOURCE: None,
        CONF_MAX_POWER_TARGET_SOURCE: 5.0,
        CONF_MAX_POWER_SOURCE_TARGET: 5.0,
        CONF_PRICE_TARGET_SOURCE: None,
        CONF_PRICE_SOURCE_TARGET: None,
        CONF_CONFIGURE_PARTITIONS: True,
    }
    await flow.async_step_user(user_input=_wrap_main_input(step1_input))

    partition_input = {
        CONF_PARTITION_PERCENTAGE: 5.0,
        CONF_PARTITION_COST: 0.10,
    }
    partition_input_overcharge = {
        CONF_PARTITION_PERCENTAGE: 95.0,
        CONF_PARTITION_COST: 0.10,
    }

    result = await flow.async_step_partitions(
        user_input=_wrap_partition_input(partition_input, partition_input_overcharge)
    )
    assert result.get("type") == FlowResultType.CREATE_ENTRY

    created_data = flow.async_create_entry.call_args.kwargs["data"]
    undercharge = created_data[SECTION_UNDERCHARGE]
    overcharge = created_data[SECTION_OVERCHARGE]
    assert undercharge[CONF_PARTITION_PERCENTAGE] == as_constant_value(5.0)
    assert overcharge[CONF_PARTITION_PERCENTAGE] == as_constant_value(95.0)
    assert undercharge[CONF_PARTITION_COST] == as_constant_value(0.10)
    assert overcharge[CONF_PARTITION_COST] == as_constant_value(0.10)


async def test_build_config_normalizes_connection_target_and_partitions(
    hass: HomeAssistant,
    hub_entry: MockConfigEntry,
) -> None:
    """_build_config should normalize connection targets and include partitions."""
    add_participant(hass, hub_entry, "main_bus", node.ELEMENT_TYPE)
    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)

    main_input = _wrap_main_input(
        {
            CONF_NAME: "Test Battery",
            CONF_CONNECTION: "main_bus",
            CONF_CAPACITY: 10.0,
            CONF_INITIAL_CHARGE_PERCENTAGE: 50.0,
            CONF_CONFIGURE_PARTITIONS: True,
        },
        as_schema=True,
    )
    partition_input = _wrap_partition_input(
        {
            CONF_PARTITION_PERCENTAGE: 5.0,
            CONF_PARTITION_COST: 0.10,
        },
        {
            CONF_PARTITION_PERCENTAGE: 95.0,
            CONF_PARTITION_COST: 0.10,
        },
    )

    config = flow._build_config(main_input, partition_input)

    assert config[CONF_CONNECTION] == as_connection_target("main_bus")
    assert config[SECTION_UNDERCHARGE][CONF_PARTITION_PERCENTAGE] == as_constant_value(5.0)
    assert config[SECTION_OVERCHARGE][CONF_PARTITION_PERCENTAGE] == as_constant_value(95.0)


async def test_partition_disabled_skips_partition_step(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """When configure_partitions is False, flow skips directly to create_entry."""
    add_participant(hass, hub_entry, "main_bus", node.ELEMENT_TYPE)
    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)

    flow.async_create_entry = Mock(
        return_value={
            "type": FlowResultType.CREATE_ENTRY,
            "title": "Test Battery",
            "data": {},
        }
    )

    step1_input = {
        CONF_NAME: "Test Battery",
        CONF_CONNECTION: "main_bus",
        CONF_CAPACITY: 10.0,
        CONF_INITIAL_CHARGE_PERCENTAGE: ["sensor.battery_soc"],
        CONF_MIN_CHARGE_PERCENTAGE: None,
        CONF_MAX_CHARGE_PERCENTAGE: None,
        CONF_EFFICIENCY_SOURCE_TARGET: None,
        CONF_EFFICIENCY_TARGET_SOURCE: None,
        CONF_MAX_POWER_TARGET_SOURCE: 5.0,
        CONF_MAX_POWER_SOURCE_TARGET: 5.0,
        CONF_PRICE_TARGET_SOURCE: None,
        CONF_PRICE_SOURCE_TARGET: None,
        CONF_CONFIGURE_PARTITIONS: False,
    }

    result = await flow.async_step_user(user_input=_wrap_main_input(step1_input))
    assert result.get("type") == FlowResultType.CREATE_ENTRY

    created_data = flow.async_create_entry.call_args.kwargs["data"]
    assert SECTION_UNDERCHARGE not in created_data
    assert SECTION_OVERCHARGE not in created_data


async def test_reconfigure_with_existing_partitions_shows_form(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """Reconfigure with existing partition data shows form."""
    add_participant(hass, hub_entry, "main_bus", node.ELEMENT_TYPE)

    existing_config = {
        CONF_ELEMENT_TYPE: ELEMENT_TYPE,
        **_wrap_main_input(
            {
                CONF_NAME: "Test Battery",
                CONF_CONNECTION: "main_bus",
                CONF_CAPACITY: as_constant_value(10.0),
                CONF_INITIAL_CHARGE_PERCENTAGE: as_constant_value(50.0),
                CONF_MAX_POWER_TARGET_SOURCE: as_constant_value(5.0),
                CONF_MAX_POWER_SOURCE_TARGET: as_constant_value(5.0),
            }
        ),
        **_wrap_partition_input(
            {
                CONF_PARTITION_PERCENTAGE: as_constant_value(5.0),
                CONF_PARTITION_COST: as_constant_value(0.10),
            },
            {
                CONF_PARTITION_PERCENTAGE: as_constant_value(95.0),
                CONF_PARTITION_COST: as_constant_value(0.10),
            },
        ),
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

    result = await flow.async_step_reconfigure(user_input=None)

    assert result.get("type") == FlowResultType.FORM


async def test_reconfigure_partition_defaults_entity_links(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """Reconfigure with entity link partition values shows entity choice."""
    add_participant(hass, hub_entry, "main_bus", node.ELEMENT_TYPE)

    existing_config = {
        CONF_ELEMENT_TYPE: ELEMENT_TYPE,
        **_wrap_main_input(
            {
                CONF_NAME: "Test Battery",
                CONF_CONNECTION: "main_bus",
                CONF_CAPACITY: as_constant_value(10.0),
                CONF_INITIAL_CHARGE_PERCENTAGE: as_constant_value(50.0),
                CONF_MAX_POWER_TARGET_SOURCE: as_constant_value(5.0),
                CONF_MAX_POWER_SOURCE_TARGET: as_constant_value(5.0),
            }
        ),
        **_wrap_partition_input(
            {
                CONF_PARTITION_PERCENTAGE: as_entity_value(["sensor.undercharge"]),
            },
            {
                CONF_PARTITION_PERCENTAGE: as_entity_value(["sensor.overcharge"]),
            },
        ),
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

    input_fields = get_input_fields(cast("Any", {CONF_ELEMENT_TYPE: ELEMENT_TYPE}))
    defaults = flow._build_partition_defaults(input_fields, dict(existing_config))

    assert defaults[SECTION_UNDERCHARGE][CONF_PARTITION_PERCENTAGE] == ["sensor.undercharge"]
    assert defaults[SECTION_OVERCHARGE][CONF_PARTITION_PERCENTAGE] == ["sensor.overcharge"]


async def test_reconfigure_partition_defaults_scalar_values(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """Reconfigure with scalar partition values shows constant choice."""
    add_participant(hass, hub_entry, "main_bus", node.ELEMENT_TYPE)

    existing_config = {
        CONF_ELEMENT_TYPE: ELEMENT_TYPE,
        **_wrap_main_input(
            {
                CONF_NAME: "Test Battery",
                CONF_CONNECTION: "main_bus",
                CONF_CAPACITY: as_constant_value(10.0),
                CONF_INITIAL_CHARGE_PERCENTAGE: as_constant_value(50.0),
                CONF_MAX_POWER_TARGET_SOURCE: as_constant_value(5.0),
                CONF_MAX_POWER_SOURCE_TARGET: as_constant_value(5.0),
            }
        ),
        **_wrap_partition_input(
            {
                CONF_PARTITION_PERCENTAGE: as_constant_value(5.0),
            },
            {
                CONF_PARTITION_PERCENTAGE: as_constant_value(95.0),
            },
        ),
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

    input_fields = get_input_fields(cast("Any", {CONF_ELEMENT_TYPE: ELEMENT_TYPE}))
    defaults = flow._build_partition_defaults(input_fields, dict(existing_config))

    assert defaults[SECTION_UNDERCHARGE][CONF_PARTITION_PERCENTAGE] == 5.0
    assert defaults[SECTION_OVERCHARGE][CONF_PARTITION_PERCENTAGE] == 95.0


async def test_build_partition_defaults_no_existing_data(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """_build_partition_defaults with no existing data uses field defaults."""
    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)

    input_fields = get_input_fields(cast("Any", {CONF_ELEMENT_TYPE: ELEMENT_TYPE}))
    defaults = flow._build_partition_defaults(input_fields, None)

    # Partition fields have defaults (mode="value", value=0 or value=100)
    assert defaults.get(SECTION_UNDERCHARGE, {}).get(CONF_PARTITION_PERCENTAGE) == 0
    assert defaults.get(SECTION_OVERCHARGE, {}).get(CONF_PARTITION_PERCENTAGE) == 100
    assert defaults.get(SECTION_UNDERCHARGE, {}).get(CONF_PARTITION_COST) == 0
    assert defaults.get(SECTION_OVERCHARGE, {}).get(CONF_PARTITION_COST) == 0


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
    config_values: dict[str, Any],
    expected_defaults: dict[str, dict[str, Any]],
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

    result = await flow.async_step_reconfigure(user_input=None)

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "user"

    input_fields = get_input_fields(cast("Any", {CONF_ELEMENT_TYPE: ELEMENT_TYPE}))
    defaults = flow._build_defaults("Test Battery", input_fields, dict(existing_subentry.data))

    for section, values in expected_defaults.items():
        for key, expected in values.items():
            assert defaults[section][key] == expected


async def test_reconfigure_updates_existing_battery(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """Reconfigure flow completes and updates existing battery."""
    add_participant(hass, hub_entry, "main_bus", node.ELEMENT_TYPE)

    existing_config = {
        CONF_ELEMENT_TYPE: ELEMENT_TYPE,
        **_wrap_main_input(
            {
                CONF_NAME: "Test Battery",
                CONF_CONNECTION: "main_bus",
                CONF_CAPACITY: as_constant_value(10.0),
                CONF_INITIAL_CHARGE_PERCENTAGE: as_constant_value(50.0),
                CONF_MAX_POWER_TARGET_SOURCE: as_constant_value(5.0),
                CONF_MAX_POWER_SOURCE_TARGET: as_constant_value(5.0),
            }
        ),
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
    flow.async_update_and_abort = Mock(return_value={"type": FlowResultType.ABORT, "reason": "reconfigure_successful"})

    await flow.async_step_reconfigure(user_input=None)

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
        CONF_PRICE_TARGET_SOURCE: None,
        CONF_PRICE_SOURCE_TARGET: None,
        CONF_CONFIGURE_PARTITIONS: False,
    }

    result = await flow.async_step_reconfigure(user_input=_wrap_main_input(user_input))
    assert result.get("type") == FlowResultType.ABORT
    assert result.get("reason") == "reconfigure_successful"

    update_kwargs = flow.async_update_and_abort.call_args.kwargs
    assert update_kwargs["title"] == "Test Battery Updated"
    assert update_kwargs["data"][SECTION_STORAGE][CONF_CAPACITY] == as_constant_value(15.0)
    assert update_kwargs["data"][SECTION_POWER_LIMITS][CONF_MAX_POWER_TARGET_SOURCE] == as_constant_value(7.5)


# --- Tests for _is_valid_choose_value ---
