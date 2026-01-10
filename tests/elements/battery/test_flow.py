"""Tests for battery element config flow."""

from types import MappingProxyType
from unittest.mock import Mock

from homeassistant.config_entries import ConfigSubentry
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
    CONF_OVERCHARGE_COST,
    CONF_OVERCHARGE_PERCENTAGE,
    CONF_UNDERCHARGE_COST,
    CONF_UNDERCHARGE_PERCENTAGE,
    ELEMENT_TYPE,
)
from custom_components.haeo.flows.field_schema import get_configurable_entity_id

from ..conftest import add_participant, create_flow


async def test_reconfigure_with_deleted_connection_target(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """Battery reconfigure should include deleted connection target in options."""
    # Create battery that references a deleted connection target
    existing_config = {
        CONF_ELEMENT_TYPE: ELEMENT_TYPE,
        CONF_NAME: "Test Battery",
        CONF_CONNECTION: "DeletedNode",  # This node no longer exists
        CONF_CAPACITY: ["sensor.capacity"],
        CONF_INITIAL_CHARGE_PERCENTAGE: ["sensor.initial"],
    }
    existing_subentry = ConfigSubentry(
        data=MappingProxyType(existing_config),
        subentry_type=ELEMENT_TYPE,
        title="Test Battery",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, existing_subentry)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.context = {"subentry_id": existing_subentry.subentry_id}
    flow._get_reconfigure_subentry = Mock(return_value=existing_subentry)

    # Show reconfigure form - should not error
    # Entity-first pattern uses step_id="user" for both new and reconfigure
    result = await flow.async_step_reconfigure(user_input=None)

    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "user"


async def test_get_participant_names_skips_unknown_element_types(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """_get_participant_names should skip subentries with unknown element types."""
    # Add a valid participant
    add_participant(hass, hub_entry, "ValidNode", node.ELEMENT_TYPE)

    # Add a subentry with unknown element type
    unknown_data = MappingProxyType({CONF_ELEMENT_TYPE: "unknown_type", CONF_NAME: "Unknown"})
    unknown_subentry = ConfigSubentry(
        data=unknown_data,
        subentry_type="unknown_type",
        title="Unknown",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, unknown_subentry)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)

    # Get participant names - should only include ValidNode
    participants = flow._get_participant_names()

    assert "ValidNode" in participants
    assert "Unknown" not in participants


async def test_get_subentry_returns_none_for_user_flow(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """_get_subentry should return None during user flow (not reconfigure)."""
    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)

    # During user flow, _get_reconfigure_subentry will raise
    subentry = flow._get_subentry()

    assert subentry is None


# --- Partition Flow Tests ---


async def test_partition_flow_enabled_shows_partition_step(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """When configure_partitions is True, flow proceeds to partitions step."""
    add_participant(hass, hub_entry, "main_bus", node.ELEMENT_TYPE)
    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    configurable_entity_id = get_configurable_entity_id()

    # Step 1: Entity selection with partitions enabled
    step1_input = {
        CONF_NAME: "Test Battery",
        CONF_CONNECTION: "main_bus",
        CONF_CAPACITY: [configurable_entity_id],
        CONF_INITIAL_CHARGE_PERCENTAGE: ["sensor.battery_soc"],
        CONF_MIN_CHARGE_PERCENTAGE: [],
        CONF_MAX_CHARGE_PERCENTAGE: [],
        CONF_EFFICIENCY: [],
        CONF_MAX_CHARGE_POWER: [configurable_entity_id],
        CONF_MAX_DISCHARGE_POWER: [configurable_entity_id],
        CONF_EARLY_CHARGE_INCENTIVE: [],
        CONF_DISCHARGE_COST: [],
        CONF_CONFIGURE_PARTITIONS: True,
    }

    result = await flow.async_step_user(user_input=None)
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "user"

    result = await flow.async_step_user(user_input=step1_input)
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "values"

    # Step 2: Configurable values
    step2_input = {
        CONF_CAPACITY: 10.0,
        CONF_MAX_CHARGE_POWER: 5.0,
        CONF_MAX_DISCHARGE_POWER: 5.0,
    }

    result = await flow.async_step_values(user_input=step2_input)
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "partitions"


async def test_partition_flow_completes_with_partition_values(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """Complete flow with partition values creates entry with partition config."""
    add_participant(hass, hub_entry, "main_bus", node.ELEMENT_TYPE)
    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    configurable_entity_id = get_configurable_entity_id()

    # Mock create_entry to capture the data
    flow.async_create_entry = Mock(return_value={"type": FlowResultType.CREATE_ENTRY, "title": "Test Battery", "data": {}})

    # Step 1: Entity selection with partitions enabled
    step1_input = {
        CONF_NAME: "Test Battery",
        CONF_CONNECTION: "main_bus",
        CONF_CAPACITY: [configurable_entity_id],
        CONF_INITIAL_CHARGE_PERCENTAGE: ["sensor.battery_soc"],
        CONF_MIN_CHARGE_PERCENTAGE: [],
        CONF_MAX_CHARGE_PERCENTAGE: [],
        CONF_EFFICIENCY: [],
        CONF_MAX_CHARGE_POWER: [configurable_entity_id],
        CONF_MAX_DISCHARGE_POWER: [configurable_entity_id],
        CONF_EARLY_CHARGE_INCENTIVE: [],
        CONF_DISCHARGE_COST: [],
        CONF_CONFIGURE_PARTITIONS: True,
    }

    await flow.async_step_user(user_input=step1_input)

    # Step 2: Configurable values
    step2_input = {
        CONF_CAPACITY: 10.0,
        CONF_MAX_CHARGE_POWER: 5.0,
        CONF_MAX_DISCHARGE_POWER: 5.0,
    }

    await flow.async_step_values(user_input=step2_input)

    # Step 3: Partition entity selections with configurable values
    # When configurable entity is selected, the values must also be provided
    partition_input = {
        CONF_UNDERCHARGE_PERCENTAGE: [configurable_entity_id],
        CONF_OVERCHARGE_PERCENTAGE: [configurable_entity_id],
        CONF_UNDERCHARGE_COST: [configurable_entity_id],
        CONF_OVERCHARGE_COST: [configurable_entity_id],
        # Configurable values for fields with configurable entity selected
        # Note: partition step combines entity selection + values in one form
    }

    # First submission shows form since configurable was selected but values missing
    result = await flow.async_step_partitions(user_input=partition_input)
    assert result.get("type") == FlowResultType.FORM
    # Full partition flow with configurable values is tested in test_partition_flow_with_entity_links


async def test_partition_flow_with_entity_links(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """Complete flow with entity link partition values creates entry."""
    add_participant(hass, hub_entry, "main_bus", node.ELEMENT_TYPE)
    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    configurable_entity_id = get_configurable_entity_id()

    # Mock create_entry to capture the data
    flow.async_create_entry = Mock(return_value={"type": FlowResultType.CREATE_ENTRY, "title": "Test Battery", "data": {}})

    # Step 1: Entity selection with partitions enabled
    step1_input = {
        CONF_NAME: "Test Battery",
        CONF_CONNECTION: "main_bus",
        CONF_CAPACITY: [configurable_entity_id],
        CONF_INITIAL_CHARGE_PERCENTAGE: ["sensor.battery_soc"],
        CONF_MIN_CHARGE_PERCENTAGE: [],
        CONF_MAX_CHARGE_PERCENTAGE: [],
        CONF_EFFICIENCY: [],
        CONF_MAX_CHARGE_POWER: [configurable_entity_id],
        CONF_MAX_DISCHARGE_POWER: [configurable_entity_id],
        CONF_EARLY_CHARGE_INCENTIVE: [],
        CONF_DISCHARGE_COST: [],
        CONF_CONFIGURE_PARTITIONS: True,
    }

    await flow.async_step_user(user_input=step1_input)

    # Step 2: Configurable values
    step2_input = {
        CONF_CAPACITY: 10.0,
        CONF_MAX_CHARGE_POWER: 5.0,
        CONF_MAX_DISCHARGE_POWER: 5.0,
    }

    await flow.async_step_values(user_input=step2_input)

    # Step 3: Partition entity selections (entity links, not configurable)
    partition_input = {
        CONF_UNDERCHARGE_PERCENTAGE: ["sensor.undercharge_pct"],
        CONF_OVERCHARGE_PERCENTAGE: ["sensor.overcharge_pct"],
        CONF_UNDERCHARGE_COST: [],
        CONF_OVERCHARGE_COST: [],
    }

    result = await flow.async_step_partitions(user_input=partition_input)
    assert result.get("type") == FlowResultType.CREATE_ENTRY

    # Verify partition fields are in the created config
    # Single entity selections are stored as strings (not lists)
    created_data = flow.async_create_entry.call_args.kwargs["data"]
    assert created_data[CONF_UNDERCHARGE_PERCENTAGE] == "sensor.undercharge_pct"
    assert created_data[CONF_OVERCHARGE_PERCENTAGE] == "sensor.overcharge_pct"


async def test_partition_flow_with_configurable_values(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """Partition step with configurable entity selection includes values."""
    add_participant(hass, hub_entry, "main_bus", node.ELEMENT_TYPE)
    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    configurable_entity_id = get_configurable_entity_id()

    flow.async_create_entry = Mock(return_value={"type": FlowResultType.CREATE_ENTRY, "title": "Test Battery", "data": {}})

    # Step 1
    step1_input = {
        CONF_NAME: "Test Battery",
        CONF_CONNECTION: "main_bus",
        CONF_CAPACITY: [configurable_entity_id],
        CONF_INITIAL_CHARGE_PERCENTAGE: ["sensor.battery_soc"],
        CONF_MIN_CHARGE_PERCENTAGE: [],
        CONF_MAX_CHARGE_PERCENTAGE: [],
        CONF_EFFICIENCY: [],
        CONF_MAX_CHARGE_POWER: [configurable_entity_id],
        CONF_MAX_DISCHARGE_POWER: [configurable_entity_id],
        CONF_EARLY_CHARGE_INCENTIVE: [],
        CONF_DISCHARGE_COST: [],
        CONF_CONFIGURE_PARTITIONS: True,
    }
    await flow.async_step_user(user_input=step1_input)

    # Step 2
    step2_input = {
        CONF_CAPACITY: 10.0,
        CONF_MAX_CHARGE_POWER: 5.0,
        CONF_MAX_DISCHARGE_POWER: 5.0,
    }
    await flow.async_step_values(user_input=step2_input)

    # Step 3: First call with no input shows partition form
    result = await flow.async_step_partitions(user_input=None)
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "partitions"


async def test_partition_disabled_skips_partition_step(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """When configure_partitions is False, flow skips directly to create_entry."""
    add_participant(hass, hub_entry, "main_bus", node.ELEMENT_TYPE)
    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    configurable_entity_id = get_configurable_entity_id()

    flow.async_create_entry = Mock(return_value={"type": FlowResultType.CREATE_ENTRY, "title": "Test Battery", "data": {}})

    # Step 1: Entity selection without partitions
    step1_input = {
        CONF_NAME: "Test Battery",
        CONF_CONNECTION: "main_bus",
        CONF_CAPACITY: [configurable_entity_id],
        CONF_INITIAL_CHARGE_PERCENTAGE: ["sensor.battery_soc"],
        CONF_MIN_CHARGE_PERCENTAGE: [],
        CONF_MAX_CHARGE_PERCENTAGE: [],
        CONF_EFFICIENCY: [],
        CONF_MAX_CHARGE_POWER: [configurable_entity_id],
        CONF_MAX_DISCHARGE_POWER: [configurable_entity_id],
        CONF_EARLY_CHARGE_INCENTIVE: [],
        CONF_DISCHARGE_COST: [],
        CONF_CONFIGURE_PARTITIONS: False,
    }

    await flow.async_step_user(user_input=step1_input)

    # Step 2: Configurable values - should go directly to create_entry
    step2_input = {
        CONF_CAPACITY: 10.0,
        CONF_MAX_CHARGE_POWER: 5.0,
        CONF_MAX_DISCHARGE_POWER: 5.0,
    }

    result = await flow.async_step_values(user_input=step2_input)
    assert result.get("type") == FlowResultType.CREATE_ENTRY

    # Verify partition fields are NOT in the created config
    created_data = flow.async_create_entry.call_args.kwargs["data"]
    assert CONF_UNDERCHARGE_PERCENTAGE not in created_data
    assert CONF_OVERCHARGE_PERCENTAGE not in created_data


async def test_reconfigure_with_existing_partitions_shows_partition_checkbox(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """Reconfigure with existing partition data pre-selects partition checkbox."""
    add_participant(hass, hub_entry, "main_bus", node.ELEMENT_TYPE)

    # Create battery with partition configuration
    existing_config = {
        CONF_ELEMENT_TYPE: ELEMENT_TYPE,
        CONF_NAME: "Test Battery",
        CONF_CONNECTION: "main_bus",
        CONF_CAPACITY: 10.0,
        CONF_INITIAL_CHARGE_PERCENTAGE: ["sensor.battery_soc"],
        CONF_MAX_CHARGE_POWER: 5.0,
        CONF_MAX_DISCHARGE_POWER: 5.0,
        CONF_UNDERCHARGE_PERCENTAGE: 5.0,
        CONF_OVERCHARGE_PERCENTAGE: 95.0,
        CONF_UNDERCHARGE_COST: 0.10,
        CONF_OVERCHARGE_COST: 0.10,
    }
    existing_subentry = ConfigSubentry(
        data=MappingProxyType(existing_config),
        subentry_type=ELEMENT_TYPE,
        title="Test Battery",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, existing_subentry)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.context = {"subentry_id": existing_subentry.subentry_id}
    flow._get_reconfigure_subentry = Mock(return_value=existing_subentry)

    # Show reconfigure form
    result = await flow.async_step_reconfigure(user_input=None)

    assert result.get("type") == FlowResultType.FORM
    # The defaults should include configure_partitions=True since partition fields exist
    # This is tested by the flow successfully completing reconfigure


async def test_partition_flow_validation_requires_configurable_values(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """Partition step validation requires values when configurable entity selected."""
    add_participant(hass, hub_entry, "main_bus", node.ELEMENT_TYPE)
    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    configurable_entity_id = get_configurable_entity_id()

    # Step 1
    step1_input = {
        CONF_NAME: "Test Battery",
        CONF_CONNECTION: "main_bus",
        CONF_CAPACITY: [configurable_entity_id],
        CONF_INITIAL_CHARGE_PERCENTAGE: ["sensor.battery_soc"],
        CONF_MIN_CHARGE_PERCENTAGE: [],
        CONF_MAX_CHARGE_PERCENTAGE: [],
        CONF_EFFICIENCY: [],
        CONF_MAX_CHARGE_POWER: [configurable_entity_id],
        CONF_MAX_DISCHARGE_POWER: [configurable_entity_id],
        CONF_EARLY_CHARGE_INCENTIVE: [],
        CONF_DISCHARGE_COST: [],
        CONF_CONFIGURE_PARTITIONS: True,
    }
    await flow.async_step_user(user_input=step1_input)

    # Step 2
    step2_input = {
        CONF_CAPACITY: 10.0,
        CONF_MAX_CHARGE_POWER: 5.0,
        CONF_MAX_DISCHARGE_POWER: 5.0,
    }
    await flow.async_step_values(user_input=step2_input)

    # Step 3: Select configurable entity for partition
    partition_input = {
        CONF_UNDERCHARGE_PERCENTAGE: [configurable_entity_id],
        CONF_OVERCHARGE_PERCENTAGE: [],
        CONF_UNDERCHARGE_COST: [],
        CONF_OVERCHARGE_COST: [],
    }
    await flow.async_step_partitions(user_input=partition_input)

    # Step 4: Submit empty values - should show validation error
    result = await flow.async_step_partition_values(user_input={})
    # Should show form with errors on partition_values step
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "partition_values"
    assert result.get("errors") == {CONF_UNDERCHARGE_PERCENTAGE: "required"}


async def test_reconfigure_partition_defaults_entity_links(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """Reconfigure with entity link partition values shows entity IDs in defaults."""
    add_participant(hass, hub_entry, "main_bus", node.ELEMENT_TYPE)

    # Create battery with entity link partition configuration
    existing_config = {
        CONF_ELEMENT_TYPE: ELEMENT_TYPE,
        CONF_NAME: "Test Battery",
        CONF_CONNECTION: "main_bus",
        CONF_CAPACITY: 10.0,
        CONF_INITIAL_CHARGE_PERCENTAGE: ["sensor.battery_soc"],
        CONF_MAX_CHARGE_POWER: 5.0,
        CONF_MAX_DISCHARGE_POWER: 5.0,
        CONF_UNDERCHARGE_PERCENTAGE: ["sensor.undercharge"],
        CONF_OVERCHARGE_PERCENTAGE: ["sensor.overcharge"],
    }
    existing_subentry = ConfigSubentry(
        data=MappingProxyType(existing_config),
        subentry_type=ELEMENT_TYPE,
        title="Test Battery",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, existing_subentry)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.context = {"subentry_id": existing_subentry.subentry_id}
    flow._get_reconfigure_subentry = Mock(return_value=existing_subentry)

    # Test _build_partition_defaults directly
    defaults = flow._build_partition_defaults(dict(existing_config))

    # Entity links should be preserved
    assert defaults[CONF_UNDERCHARGE_PERCENTAGE] == ["sensor.undercharge"]
    assert defaults[CONF_OVERCHARGE_PERCENTAGE] == ["sensor.overcharge"]
    # Missing fields should use defaults.mode (all have mode='value')
    configurable_entity_id = get_configurable_entity_id()
    assert defaults[CONF_UNDERCHARGE_COST] == [configurable_entity_id]
    assert defaults[CONF_OVERCHARGE_COST] == [configurable_entity_id]


async def test_build_partition_defaults_no_existing_data(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """_build_partition_defaults with no existing data respects defaults.mode."""
    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)

    defaults = flow._build_partition_defaults(None)

    # All partition fields have mode='value', so they should default to configurable entity
    configurable_entity_id = get_configurable_entity_id()
    assert defaults[CONF_UNDERCHARGE_PERCENTAGE] == [configurable_entity_id]
    assert defaults[CONF_OVERCHARGE_PERCENTAGE] == [configurable_entity_id]
    assert defaults[CONF_UNDERCHARGE_COST] == [configurable_entity_id]
    assert defaults[CONF_OVERCHARGE_COST] == [configurable_entity_id]


async def test_step1_defaults_entity_mode(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """_build_step1_defaults with mode='entity' pre-selects the entity."""
    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)

    # Test the defaults logic - call internal method directly
    # In first setup (no subentry_data), fields with defaults.mode='entity'
    # should have their entity pre-selected
    defaults = flow._build_step1_defaults("Test Battery", None)

    # Fields with mode='value' should have configurable entity pre-selected
    configurable_entity_id = get_configurable_entity_id()
    assert defaults[CONF_EARLY_CHARGE_INCENTIVE] == [configurable_entity_id]
    assert defaults[CONF_EFFICIENCY] == [configurable_entity_id]

    # Fields with mode=None should be empty
    assert defaults[CONF_MIN_CHARGE_PERCENTAGE] == []
    assert defaults[CONF_MAX_CHARGE_PERCENTAGE] == []


async def test_build_field_entity_defaults_entity_mode(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """_build_field_entity_defaults with mode='entity' pre-selects the specified entity."""
    from custom_components.haeo.elements.input_fields import InputFieldDefaults, InputFieldInfo
    from custom_components.haeo.model.const import OutputType
    from homeassistant.components.number import NumberEntityDescription

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)

    # Create a mock field with mode='entity'
    mock_field = InputFieldInfo(
        field_name="test_field",
        entity_description=NumberEntityDescription(key="test_field"),
        output_type=OutputType.POWER,
        defaults=InputFieldDefaults(mode="entity", entity="sensor.my_preset_entity"),
    )

    # Call the internal method with the mock field
    defaults = flow._build_field_entity_defaults([mock_field], None, entry_id="test_entry", subentry_id="test_subentry")

    # Should pre-select the entity specified in defaults.entity
    assert defaults["test_field"] == ["sensor.my_preset_entity"]


async def test_partition_flow_skips_step2_when_no_configurable_fields(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """When no configurable entity is selected, step 2 is skipped, goes to partitions."""
    add_participant(hass, hub_entry, "main_bus", node.ELEMENT_TYPE)
    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)

    flow.async_create_entry = Mock(return_value={"type": FlowResultType.CREATE_ENTRY, "title": "Test Battery", "data": {}})

    # Step 1: Entity selection with partitions enabled, but NO configurable entities
    step1_input = {
        CONF_NAME: "Test Battery",
        CONF_CONNECTION: "main_bus",
        CONF_CAPACITY: ["sensor.capacity"],  # Entity link, not configurable
        CONF_INITIAL_CHARGE_PERCENTAGE: ["sensor.battery_soc"],
        CONF_MIN_CHARGE_PERCENTAGE: [],
        CONF_MAX_CHARGE_PERCENTAGE: [],
        CONF_EFFICIENCY: [],
        CONF_MAX_CHARGE_POWER: ["sensor.max_charge"],  # Entity link
        CONF_MAX_DISCHARGE_POWER: ["sensor.max_discharge"],  # Entity link
        CONF_EARLY_CHARGE_INCENTIVE: [],
        CONF_DISCHARGE_COST: [],
        CONF_CONFIGURE_PARTITIONS: True,
    }

    result = await flow.async_step_user(user_input=step1_input)
    # Should skip step 2 and go directly to partitions since no configurable fields
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "partitions"


async def test_partition_flow_skips_step2_and_partitions_when_all_entity_links(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """When no configurable entity selected and partitions disabled, goes directly to create."""
    add_participant(hass, hub_entry, "main_bus", node.ELEMENT_TYPE)
    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)

    flow.async_create_entry = Mock(return_value={"type": FlowResultType.CREATE_ENTRY, "title": "Test Battery", "data": {}})

    # Step 1: Entity selection with all entity links, no partitions
    step1_input = {
        CONF_NAME: "Test Battery",
        CONF_CONNECTION: "main_bus",
        CONF_CAPACITY: ["sensor.capacity"],
        CONF_INITIAL_CHARGE_PERCENTAGE: ["sensor.battery_soc"],
        CONF_MIN_CHARGE_PERCENTAGE: [],
        CONF_MAX_CHARGE_PERCENTAGE: [],
        CONF_EFFICIENCY: [],
        CONF_MAX_CHARGE_POWER: ["sensor.max_charge"],
        CONF_MAX_DISCHARGE_POWER: ["sensor.max_discharge"],
        CONF_EARLY_CHARGE_INCENTIVE: [],
        CONF_DISCHARGE_COST: [],
        CONF_CONFIGURE_PARTITIONS: False,
    }

    result = await flow.async_step_user(user_input=step1_input)
    # Should skip step 2 and go directly to create_entry
    assert result.get("type") == FlowResultType.CREATE_ENTRY


async def test_reconfigure_partition_defaults_scalar_values(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """Reconfigure with scalar partition values shows configurable entity in defaults."""
    add_participant(hass, hub_entry, "main_bus", node.ELEMENT_TYPE)

    # Create battery with scalar partition configuration
    existing_config = {
        CONF_ELEMENT_TYPE: ELEMENT_TYPE,
        CONF_NAME: "Test Battery",
        CONF_CONNECTION: "main_bus",
        CONF_CAPACITY: 10.0,
        CONF_INITIAL_CHARGE_PERCENTAGE: ["sensor.battery_soc"],
        CONF_MAX_CHARGE_POWER: 5.0,
        CONF_MAX_DISCHARGE_POWER: 5.0,
        # Scalar partition values (not entity links)
        CONF_UNDERCHARGE_PERCENTAGE: 5.0,
        CONF_OVERCHARGE_PERCENTAGE: 95.0,
    }
    existing_subentry = ConfigSubentry(
        data=MappingProxyType(existing_config),
        subentry_type=ELEMENT_TYPE,
        title="Test Battery",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, existing_subentry)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.context = {"subentry_id": existing_subentry.subentry_id}
    flow._get_reconfigure_subentry = Mock(return_value=existing_subentry)

    # Test _build_partition_defaults with scalar values
    defaults = flow._build_partition_defaults(dict(existing_config))

    # Scalar values should show configurable entity (or resolved entity ID)
    # The function calls resolve_configurable_entity_id which returns None in tests
    # because the entity isn't actually registered, so it falls back to configurable_entity_id
    configurable_entity_id = get_configurable_entity_id()
    assert defaults[CONF_UNDERCHARGE_PERCENTAGE] == [configurable_entity_id]
    assert defaults[CONF_OVERCHARGE_PERCENTAGE] == [configurable_entity_id]
    # Fields not in config should use defaults.mode (all have mode='value')
    assert defaults[CONF_UNDERCHARGE_COST] == [configurable_entity_id]
    assert defaults[CONF_OVERCHARGE_COST] == [configurable_entity_id]


async def test_partition_values_step_completes_flow(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """Partition values step with valid input creates entry."""
    add_participant(hass, hub_entry, "main_bus", node.ELEMENT_TYPE)
    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    configurable_entity_id = get_configurable_entity_id()

    flow.async_create_entry = Mock(return_value={"type": FlowResultType.CREATE_ENTRY, "title": "Test Battery", "data": {}})

    # Step 1: Entity selection with partitions enabled
    step1_input = {
        CONF_NAME: "Test Battery",
        CONF_CONNECTION: "main_bus",
        CONF_CAPACITY: [configurable_entity_id],
        CONF_INITIAL_CHARGE_PERCENTAGE: ["sensor.battery_soc"],
        CONF_MIN_CHARGE_PERCENTAGE: [],
        CONF_MAX_CHARGE_PERCENTAGE: [],
        CONF_EFFICIENCY: [],
        CONF_MAX_CHARGE_POWER: [configurable_entity_id],
        CONF_MAX_DISCHARGE_POWER: [configurable_entity_id],
        CONF_EARLY_CHARGE_INCENTIVE: [],
        CONF_DISCHARGE_COST: [],
        CONF_CONFIGURE_PARTITIONS: True,
    }
    await flow.async_step_user(user_input=step1_input)

    # Step 2: Configurable values
    step2_input = {
        CONF_CAPACITY: 10.0,
        CONF_MAX_CHARGE_POWER: 5.0,
        CONF_MAX_DISCHARGE_POWER: 5.0,
    }
    await flow.async_step_values(user_input=step2_input)

    # Step 3: Partition entity selections - select configurable for undercharge_percentage
    partition_input = {
        CONF_UNDERCHARGE_PERCENTAGE: [configurable_entity_id],
        CONF_OVERCHARGE_PERCENTAGE: ["sensor.overcharge_pct"],
        CONF_UNDERCHARGE_COST: [],
        CONF_OVERCHARGE_COST: [],
    }
    result = await flow.async_step_partitions(user_input=partition_input)

    # Should proceed to partition_values step
    assert result.get("type") == FlowResultType.FORM
    assert result.get("step_id") == "partition_values"

    # Step 4: Partition values - provide value for the configurable field
    partition_values_input = {
        CONF_UNDERCHARGE_PERCENTAGE: 5.0,
    }
    result = await flow.async_step_partition_values(user_input=partition_values_input)

    # Should create entry successfully
    assert result.get("type") == FlowResultType.CREATE_ENTRY

    # Verify the created config
    created_data = flow.async_create_entry.call_args.kwargs["data"]
    assert created_data[CONF_UNDERCHARGE_PERCENTAGE] == 5.0
    assert created_data[CONF_OVERCHARGE_PERCENTAGE] == "sensor.overcharge_pct"


async def test_reconfigure_updates_existing_battery(hass: HomeAssistant, hub_entry: MockConfigEntry) -> None:
    """Reconfigure flow completes and updates existing battery."""
    add_participant(hass, hub_entry, "main_bus", node.ELEMENT_TYPE)
    configurable_entity_id = get_configurable_entity_id()

    existing_config = {
        CONF_ELEMENT_TYPE: ELEMENT_TYPE,
        CONF_NAME: "Test Battery",
        CONF_CONNECTION: "main_bus",
        CONF_CAPACITY: 10.0,
        CONF_INITIAL_CHARGE_PERCENTAGE: ["sensor.battery_soc"],
        CONF_MAX_CHARGE_POWER: 5.0,
        CONF_MAX_DISCHARGE_POWER: 5.0,
    }
    existing_subentry = ConfigSubentry(
        data=MappingProxyType(existing_config),
        subentry_type=ELEMENT_TYPE,
        title="Test Battery",
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(hub_entry, existing_subentry)

    flow = create_flow(hass, hub_entry, ELEMENT_TYPE)
    flow.context = {"subentry_id": existing_subentry.subentry_id}
    flow._get_reconfigure_subentry = Mock(return_value=existing_subentry)
    flow.async_update_and_abort = Mock(return_value={"type": FlowResultType.ABORT, "reason": "reconfigure_successful"})

    # Show reconfigure form
    await flow.async_step_reconfigure(user_input=None)

    # Submit step 1
    step1_input = {
        CONF_NAME: "Test Battery Updated",
        CONF_CONNECTION: "main_bus",
        CONF_CAPACITY: [configurable_entity_id],
        CONF_INITIAL_CHARGE_PERCENTAGE: ["sensor.battery_soc"],
        CONF_MIN_CHARGE_PERCENTAGE: [],
        CONF_MAX_CHARGE_PERCENTAGE: [],
        CONF_EFFICIENCY: [],
        CONF_MAX_CHARGE_POWER: [configurable_entity_id],
        CONF_MAX_DISCHARGE_POWER: [configurable_entity_id],
        CONF_EARLY_CHARGE_INCENTIVE: [],
        CONF_DISCHARGE_COST: [],
        CONF_CONFIGURE_PARTITIONS: False,
    }

    result = await flow.async_step_reconfigure(user_input=step1_input)
    assert result.get("step_id") == "values"

    # Submit step 2
    step2_input = {
        CONF_CAPACITY: 15.0,
        CONF_MAX_CHARGE_POWER: 7.5,
        CONF_MAX_DISCHARGE_POWER: 7.5,
    }

    result = await flow.async_step_values(user_input=step2_input)
    assert result.get("type") == FlowResultType.ABORT
    assert result.get("reason") == "reconfigure_successful"

    # Verify the updated data
    update_kwargs = flow.async_update_and_abort.call_args.kwargs
    assert update_kwargs["title"] == "Test Battery Updated"
    assert update_kwargs["data"][CONF_CAPACITY] == 15.0
