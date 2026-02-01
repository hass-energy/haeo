"""Tests for battery element config flow."""

from types import MappingProxyType
from typing import Any
from unittest.mock import Mock

from homeassistant.config_entries import SOURCE_RECONFIGURE, ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.const import CONF_ELEMENT_TYPE, CONF_NAME
from custom_components.haeo.elements import node
from custom_components.haeo.elements.battery import (
    CONF_CAPACITY,
    CONF_CONFIGURE_PARTITIONS,
    CONF_CONNECTION,
    CONF_DISCHARGE_COST,
    CONF_EARLY_CHARGE_INCENTIVE,
    CONF_EFFICIENCY,
    CONF_INITIAL_CHARGE_PERCENTAGE,
    CONF_MAX_CHARGE_PERCENTAGE,
    CONF_MAX_CHARGE_POWER,
    CONF_MAX_DISCHARGE_POWER,
    CONF_MIN_CHARGE_PERCENTAGE,
    CONF_PARTITION_COST,
    CONF_PARTITION_PERCENTAGE,
    ELEMENT_TYPE,
    SECTION_ADVANCED,
    SECTION_BASIC,
    SECTION_LIMITS,
    SECTION_OVERCHARGE,
    SECTION_PRICING,
    SECTION_STORAGE,
    SECTION_UNDERCHARGE,
)

from ..conftest import add_participant, create_flow


def _wrap_main_input(user_input: dict[str, Any]) -> dict[str, Any]:
    """Wrap battery user input into sectioned form data."""
    return {
        SECTION_BASIC: {
            key: user_input[key]
            for key in (
                CONF_NAME,
                CONF_CONNECTION,
            )
            if key in user_input
        },
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
                CONF_MAX_CHARGE_POWER,
                CONF_MAX_DISCHARGE_POWER,
            )
            if key in user_input
        },
        SECTION_PRICING: {
            key: user_input[key]
            for key in (
                CONF_EARLY_CHARGE_INCENTIVE,
                CONF_DISCHARGE_COST,
            )
            if key in user_input
        },
        SECTION_ADVANCED: {
            key: user_input[key]
            for key in (
                CONF_EFFICIENCY,
                CONF_CONFIGURE_PARTITIONS,
            )
            if key in user_input
        },
    }


def _wrap_partition_input(
    undercharge_input: dict[str, Any],
    overcharge_input: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Wrap partition inputs into sectioned form data."""
    overcharge_input = overcharge_input or {}
    return {
        SECTION_UNDERCHARGE: {key: undercharge_input[key] for key in (CONF_PARTITION_PERCENTAGE, CONF_PARTITION_COST) if key in undercharge_input},
        SECTION_OVERCHARGE: {key: overcharge_input[key] for key in (CONF_PARTITION_PERCENTAGE, CONF_PARTITION_COST) if key in overcharge_input},
    }


async def test_reconfigure_with_deleted_connection_target(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """Battery reconfigure should include deleted connection target in options."""
    existing_config = {
        CONF_ELEMENT_TYPE: ELEMENT_TYPE,
        **_wrap_main_input(
            {
                CONF_NAME: "Test Battery",
                CONF_CONNECTION: "DeletedNode",
                CONF_CAPACITY: 10.0,
                CONF_INITIAL_CHARGE_PERCENTAGE: 50.0,
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

    result = await flow.async_step_reconfigure(user_input=None)

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "user"


async def test_get_participant_names_skips_unknown_element_types(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """_get_participant_names should skip subentries with unknown element types."""
    add_participant(hass, hub_entry, "ValidNode", node.ELEMENT_TYPE)

    unknown_data = MappingProxyType({CONF_ELEMENT_TYPE: "unknown_type", CONF_NAME: "Unknown"})
    unknown_subentry = ConfigSubentry(
        data=unknown_data,
        subentry_type="unknown_type",
        title="Unknown",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, unknown_subentry)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)

    participants = flow._get_participant_names()

    assert "ValidNode" in participants
    assert "Unknown" not in participants


async def test_get_subentry_returns_none_for_user_flow(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """_get_subentry should return None during user flow (not reconfigure)."""
    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)

    subentry = flow._get_subentry()

    assert subentry is None


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
        CONF_EFFICIENCY: 0.95,
        CONF_MAX_CHARGE_POWER: 5.0,
        CONF_MAX_DISCHARGE_POWER: 5.0,
        CONF_EARLY_CHARGE_INCENTIVE: 0.001,
        CONF_DISCHARGE_COST: None,
        CONF_CONFIGURE_PARTITIONS: False,
    }

    result = await flow.async_step_user(user_input=_wrap_main_input(user_input))
    assert result.get("type") == FlowResultType.CREATE_ENTRY

    created_data = flow.async_create_entry.call_args.kwargs["data"]
    assert created_data["storage"][CONF_CAPACITY] == 10.0
    assert created_data["storage"][CONF_INITIAL_CHARGE_PERCENTAGE] == "sensor.battery_soc"
    assert created_data["limits"][CONF_MAX_CHARGE_POWER] == 5.0


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
        CONF_EFFICIENCY: None,
        CONF_MAX_CHARGE_POWER: ["sensor.max_charge"],
        CONF_MAX_DISCHARGE_POWER: ["sensor.max_discharge"],
        CONF_EARLY_CHARGE_INCENTIVE: None,
        CONF_DISCHARGE_COST: None,
        CONF_CONFIGURE_PARTITIONS: False,
    }

    result = await flow.async_step_user(user_input=_wrap_main_input(user_input))
    assert result.get("type") == FlowResultType.CREATE_ENTRY

    created_data = flow.async_create_entry.call_args.kwargs["data"]
    assert created_data["storage"][CONF_CAPACITY] == "sensor.capacity"
    assert created_data["storage"][CONF_INITIAL_CHARGE_PERCENTAGE] == "sensor.battery_soc"
    assert created_data["limits"][CONF_MAX_CHARGE_POWER] == "sensor.max_charge"


async def test_user_step_empty_required_field_shows_error(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """Submitting with empty required choose field should show required error."""
    add_participant(hass, hub_entry, "main_bus", node.ELEMENT_TYPE)
    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)

    user_input = {
        CONF_NAME: "Test Battery",
        CONF_CONNECTION: "main_bus",
        CONF_CAPACITY: [],
        CONF_INITIAL_CHARGE_PERCENTAGE: ["sensor.battery_soc"],
        CONF_MIN_CHARGE_PERCENTAGE: None,
        CONF_MAX_CHARGE_PERCENTAGE: None,
        CONF_EFFICIENCY: None,
        CONF_MAX_CHARGE_POWER: 5.0,
        CONF_MAX_DISCHARGE_POWER: 5.0,
        CONF_EARLY_CHARGE_INCENTIVE: None,
        CONF_DISCHARGE_COST: None,
        CONF_CONFIGURE_PARTITIONS: False,
    }

    result = await flow.async_step_user(user_input=_wrap_main_input(user_input))

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "user"
    assert CONF_CAPACITY in result.get("errors", {})


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
        CONF_EFFICIENCY: 0.95,
        CONF_MAX_CHARGE_POWER: 5.0,
        CONF_MAX_DISCHARGE_POWER: 5.0,
        CONF_EARLY_CHARGE_INCENTIVE: None,
        CONF_DISCHARGE_COST: None,
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
        CONF_EFFICIENCY: None,
        CONF_MAX_CHARGE_POWER: 5.0,
        CONF_MAX_DISCHARGE_POWER: 5.0,
        CONF_EARLY_CHARGE_INCENTIVE: None,
        CONF_DISCHARGE_COST: None,
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

    result = await flow.async_step_partitions(user_input=_wrap_partition_input(partition_input, partition_input_overcharge))
    assert result.get("type") == FlowResultType.CREATE_ENTRY

    created_data = flow.async_create_entry.call_args.kwargs["data"]
    undercharge = created_data[SECTION_UNDERCHARGE]
    overcharge = created_data[SECTION_OVERCHARGE]
    assert undercharge[CONF_PARTITION_PERCENTAGE] == "sensor.undercharge_pct"
    assert overcharge[CONF_PARTITION_PERCENTAGE] == "sensor.overcharge_pct"


async def test_partition_flow_with_constant_values_creates_entry(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
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
        CONF_EFFICIENCY: None,
        CONF_MAX_CHARGE_POWER: 5.0,
        CONF_MAX_DISCHARGE_POWER: 5.0,
        CONF_EARLY_CHARGE_INCENTIVE: None,
        CONF_DISCHARGE_COST: None,
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

    result = await flow.async_step_partitions(user_input=_wrap_partition_input(partition_input, partition_input_overcharge))
    assert result.get("type") == FlowResultType.CREATE_ENTRY

    created_data = flow.async_create_entry.call_args.kwargs["data"]
    undercharge = created_data[SECTION_UNDERCHARGE]
    overcharge = created_data[SECTION_OVERCHARGE]
    assert undercharge[CONF_PARTITION_PERCENTAGE] == 5.0
    assert overcharge[CONF_PARTITION_PERCENTAGE] == 95.0
    assert undercharge[CONF_PARTITION_COST] == 0.10
    assert overcharge[CONF_PARTITION_COST] == 0.10


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
        CONF_EFFICIENCY: None,
        CONF_MAX_CHARGE_POWER: 5.0,
        CONF_MAX_DISCHARGE_POWER: 5.0,
        CONF_EARLY_CHARGE_INCENTIVE: None,
        CONF_DISCHARGE_COST: None,
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
                CONF_CAPACITY: 10.0,
                CONF_INITIAL_CHARGE_PERCENTAGE: 50.0,
                CONF_MAX_CHARGE_POWER: 5.0,
                CONF_MAX_DISCHARGE_POWER: 5.0,
            }
        ),
        **_wrap_partition_input(
            {
                CONF_PARTITION_PERCENTAGE: 5.0,
                CONF_PARTITION_COST: 0.10,
            },
            {
                CONF_PARTITION_PERCENTAGE: 95.0,
                CONF_PARTITION_COST: 0.10,
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
                CONF_CAPACITY: 10.0,
                CONF_INITIAL_CHARGE_PERCENTAGE: 50.0,
                CONF_MAX_CHARGE_POWER: 5.0,
                CONF_MAX_DISCHARGE_POWER: 5.0,
            }
        ),
        **_wrap_partition_input(
            {
                CONF_PARTITION_PERCENTAGE: "sensor.undercharge",
            },
            {
                CONF_PARTITION_PERCENTAGE: "sensor.overcharge",
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

    defaults = flow._build_partition_defaults(dict(existing_config))

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
                CONF_CAPACITY: 10.0,
                CONF_INITIAL_CHARGE_PERCENTAGE: 50.0,
                CONF_MAX_CHARGE_POWER: 5.0,
                CONF_MAX_DISCHARGE_POWER: 5.0,
            }
        ),
        **_wrap_partition_input(
            {
                CONF_PARTITION_PERCENTAGE: 5.0,
            },
            {
                CONF_PARTITION_PERCENTAGE: 95.0,
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

    defaults = flow._build_partition_defaults(dict(existing_config))

    assert defaults[SECTION_UNDERCHARGE][CONF_PARTITION_PERCENTAGE] == 5.0
    assert defaults[SECTION_OVERCHARGE][CONF_PARTITION_PERCENTAGE] == 95.0


async def test_build_partition_defaults_no_existing_data(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """_build_partition_defaults with no existing data uses field defaults."""
    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)

    defaults = flow._build_partition_defaults(None)

    # Partition fields have defaults (mode="value", value=0 or value=100)
    assert defaults.get(SECTION_UNDERCHARGE, {}).get(CONF_PARTITION_PERCENTAGE) == 0
    assert defaults.get(SECTION_OVERCHARGE, {}).get(CONF_PARTITION_PERCENTAGE) == 100
    assert defaults.get(SECTION_UNDERCHARGE, {}).get(CONF_PARTITION_COST) == 0
    assert defaults.get(SECTION_OVERCHARGE, {}).get(CONF_PARTITION_COST) == 0


async def test_defaults_with_scalar_values_shows_constant_choice(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """_build_defaults with scalar values should show constant choice."""
    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)

    existing_data = _wrap_main_input(
        {
            CONF_CAPACITY: 10.0,
            CONF_MAX_CHARGE_POWER: 5.0,
            CONF_EFFICIENCY: 0.95,
        }
    )
    defaults = flow._build_defaults("Test Battery", existing_data)

    assert defaults[SECTION_STORAGE][CONF_CAPACITY] == 10.0
    assert defaults[SECTION_LIMITS][CONF_MAX_CHARGE_POWER] == 5.0
    assert defaults[SECTION_ADVANCED][CONF_EFFICIENCY] == 0.95


async def test_defaults_with_entity_strings_shows_entity_choice(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """_build_defaults with entity strings should show entity choice."""
    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)

    existing_data = _wrap_main_input(
        {
            CONF_CAPACITY: "sensor.capacity",
            CONF_INITIAL_CHARGE_PERCENTAGE: "sensor.soc",
        }
    )
    defaults = flow._build_defaults("Test Battery", existing_data)

    assert defaults[SECTION_STORAGE][CONF_CAPACITY] == ["sensor.capacity"]
    assert defaults[SECTION_STORAGE][CONF_INITIAL_CHARGE_PERCENTAGE] == ["sensor.soc"]


async def test_reconfigure_with_string_entity_id_v010_format(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """Reconfigure with v0.1.0 string entity ID shows entity choice."""
    add_participant(hass, hub_entry, "main_bus", node.ELEMENT_TYPE)

    existing_config = {
        CONF_ELEMENT_TYPE: ELEMENT_TYPE,
        **_wrap_main_input(
            {
                CONF_NAME: "Test Battery",
                CONF_CONNECTION: "main_bus",
                CONF_CAPACITY: "sensor.battery_capacity",
                CONF_INITIAL_CHARGE_PERCENTAGE: "sensor.battery_soc",
                CONF_MAX_CHARGE_POWER: "sensor.charge_power",
                CONF_MAX_DISCHARGE_POWER: "sensor.discharge_power",
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

    result = await flow.async_step_reconfigure(user_input=None)

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "user"

    defaults = flow._build_defaults("Test Battery", dict(existing_subentry.data))

    assert defaults[SECTION_STORAGE][CONF_CAPACITY] == ["sensor.battery_capacity"]
    assert defaults[SECTION_STORAGE][CONF_INITIAL_CHARGE_PERCENTAGE] == ["sensor.battery_soc"]
    assert defaults[SECTION_LIMITS][CONF_MAX_CHARGE_POWER] == ["sensor.charge_power"]
    assert defaults[SECTION_LIMITS][CONF_MAX_DISCHARGE_POWER] == ["sensor.discharge_power"]


async def test_reconfigure_updates_existing_battery(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """Reconfigure flow completes and updates existing battery."""
    add_participant(hass, hub_entry, "main_bus", node.ELEMENT_TYPE)

    existing_config = {
        CONF_ELEMENT_TYPE: ELEMENT_TYPE,
        **_wrap_main_input(
            {
                CONF_NAME: "Test Battery",
                CONF_CONNECTION: "main_bus",
                CONF_CAPACITY: 10.0,
                CONF_INITIAL_CHARGE_PERCENTAGE: 50.0,
                CONF_MAX_CHARGE_POWER: 5.0,
                CONF_MAX_DISCHARGE_POWER: 5.0,
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
        CONF_EFFICIENCY: None,
        CONF_MAX_CHARGE_POWER: 7.5,
        CONF_MAX_DISCHARGE_POWER: 7.5,
        CONF_EARLY_CHARGE_INCENTIVE: None,
        CONF_DISCHARGE_COST: None,
        CONF_CONFIGURE_PARTITIONS: False,
    }

    result = await flow.async_step_reconfigure(user_input=_wrap_main_input(user_input))
    assert result.get("type") == FlowResultType.ABORT
    assert result.get("reason") == "reconfigure_successful"

    update_kwargs = flow.async_update_and_abort.call_args.kwargs
    assert update_kwargs["title"] == "Test Battery Updated"
    assert update_kwargs["data"][SECTION_STORAGE][CONF_CAPACITY] == 15.0
    assert update_kwargs["data"][SECTION_LIMITS][CONF_MAX_CHARGE_POWER] == 7.5


# --- Tests for _is_valid_choose_value ---
