"""Tests for the HAEO switch input entity."""

from types import MappingProxyType
from typing import Any
from unittest.mock import Mock

from homeassistant.components.switch import SwitchEntityDescription
from homeassistant.config_entries import ConfigSubentry
from homeassistant.const import STATE_OFF, STATE_ON, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntry
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.const import CONF_NAME, DOMAIN
from custom_components.haeo.elements.input_fields import InputFieldInfo
from custom_components.haeo.entities.haeo_number import ConfigEntityMode
from custom_components.haeo.entities.haeo_switch import HaeoInputSwitch
from custom_components.haeo.horizon import HorizonManager
from custom_components.haeo.model.const import OutputType

# --- Fixtures ---


@pytest.fixture
def config_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Return a config entry for switch entity tests."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Network",
        data={
            "name": "Test Network",
            "tier_1_count": 2,
            "tier_1_duration": 5,
            "tier_2_count": 0,
            "tier_2_duration": 15,
            "tier_3_count": 0,
            "tier_3_duration": 30,
            "tier_4_count": 0,
            "tier_4_duration": 60,
        },
        entry_id="test_switch_entry",
    )
    entry.add_to_hass(hass)
    return entry


@pytest.fixture
def device_entry() -> Mock:
    """Return a mock device entry."""
    device = Mock(spec=DeviceEntry)
    device.id = "mock-switch-device-id"
    return device


@pytest.fixture
def horizon_manager() -> Mock:
    """Return a mock horizon manager."""
    manager = Mock(spec=HorizonManager)
    # Return timestamps for 2 periods starting now
    manager.get_forecast_timestamps.return_value = (0.0, 300.0, 600.0)
    # Subscribe returns an unsubscribe function
    manager.subscribe.return_value = Mock()
    return manager


@pytest.fixture
def curtailment_field_info() -> InputFieldInfo[SwitchEntityDescription]:
    """Return a sample InputFieldInfo for a boolean curtailment field."""
    return InputFieldInfo(
        field_name="allow_curtailment",
        entity_description=SwitchEntityDescription(
            key="allow_curtailment",
            translation_key="allow_curtailment",
        ),
        output_type=OutputType.STATUS,
    )


def _create_subentry(name: str, data: dict[str, Any]) -> ConfigSubentry:
    """Create a ConfigSubentry with the given data."""
    return ConfigSubentry(
        data=MappingProxyType({CONF_NAME: name, "element_type": "solar", **data}),
        subentry_type="solar",
        title=name,
        unique_id=None,
    )


# --- Tests for EDITABLE mode ---


async def test_editable_mode_with_true_value(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    curtailment_field_info: InputFieldInfo[SwitchEntityDescription],
    horizon_manager: Mock,
) -> None:
    """Switch entity in EDITABLE mode initializes with True config value."""
    subentry = _create_subentry("Test Solar", {"allow_curtailment": True})
    config_entry.runtime_data = None

    entity = HaeoInputSwitch(
        hass=hass,
        config_entry=config_entry,
        subentry=subentry,
        field_info=curtailment_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )

    assert entity._entity_mode == ConfigEntityMode.EDITABLE
    assert entity._source_entity_id is None
    assert entity.is_on is True

    attrs = entity.extra_state_attributes
    assert attrs is not None
    assert attrs["config_mode"] == "editable"
    assert attrs["element_name"] == "Test Solar"
    assert attrs["element_type"] == "solar"
    assert attrs["field_name"] == "allow_curtailment"


async def test_editable_mode_with_false_value(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    curtailment_field_info: InputFieldInfo[SwitchEntityDescription],
    horizon_manager: Mock,
) -> None:
    """Switch entity in EDITABLE mode initializes with False config value."""
    subentry = _create_subentry("Test Solar", {"allow_curtailment": False})
    config_entry.runtime_data = None

    entity = HaeoInputSwitch(
        hass=hass,
        config_entry=config_entry,
        subentry=subentry,
        field_info=curtailment_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )

    assert entity._entity_mode == ConfigEntityMode.EDITABLE
    assert entity.is_on is False


async def test_editable_mode_with_none_value(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    curtailment_field_info: InputFieldInfo[SwitchEntityDescription],
    horizon_manager: Mock,
) -> None:
    """Switch entity in EDITABLE mode handles None for optional fields."""
    subentry = _create_subentry("Test Solar", {"allow_curtailment": None})
    config_entry.runtime_data = None

    entity = HaeoInputSwitch(
        hass=hass,
        config_entry=config_entry,
        subentry=subentry,
        field_info=curtailment_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )

    assert entity._entity_mode == ConfigEntityMode.EDITABLE
    assert entity.is_on is None


async def test_editable_mode_turn_on(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    curtailment_field_info: InputFieldInfo[SwitchEntityDescription],
    horizon_manager: Mock,
) -> None:
    """Switch entity in EDITABLE mode turns on when user requests."""
    subentry = _create_subentry("Test Solar", {"allow_curtailment": False})
    config_entry.runtime_data = None

    entity = HaeoInputSwitch(
        hass=hass,
        config_entry=config_entry,
        subentry=subentry,
        field_info=curtailment_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )
    entity.async_write_ha_state = Mock()
    hass.config_entries.async_update_subentry = Mock()

    await entity.async_turn_on()

    assert entity.is_on is True
    entity.async_write_ha_state.assert_called_once()
    # Value should be persisted to config entry
    hass.config_entries.async_update_subentry.assert_called_once()


async def test_editable_mode_turn_off(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    curtailment_field_info: InputFieldInfo[SwitchEntityDescription],
    horizon_manager: Mock,
) -> None:
    """Switch entity in EDITABLE mode turns off when user requests."""
    subentry = _create_subentry("Test Solar", {"allow_curtailment": True})
    config_entry.runtime_data = None

    entity = HaeoInputSwitch(
        hass=hass,
        config_entry=config_entry,
        subentry=subentry,
        field_info=curtailment_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )
    entity.async_write_ha_state = Mock()
    hass.config_entries.async_update_subentry = Mock()

    await entity.async_turn_off()

    assert entity.is_on is False
    entity.async_write_ha_state.assert_called_once()
    # Value should be persisted to config entry
    hass.config_entries.async_update_subentry.assert_called_once()


# --- Tests for DRIVEN mode ---


async def test_driven_mode_with_entity_id(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    curtailment_field_info: InputFieldInfo[SwitchEntityDescription],
    horizon_manager: Mock,
) -> None:
    """Switch entity in DRIVEN mode tracks source entity."""
    subentry = _create_subentry("Test Solar", {"allow_curtailment": "input_boolean.allow_curtailment"})
    config_entry.runtime_data = None

    entity = HaeoInputSwitch(
        hass=hass,
        config_entry=config_entry,
        subentry=subentry,
        field_info=curtailment_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )

    assert entity._entity_mode == ConfigEntityMode.DRIVEN
    assert entity._source_entity_id == "input_boolean.allow_curtailment"
    assert entity.is_on is None  # Not loaded yet

    attrs = entity.extra_state_attributes
    assert attrs is not None
    assert attrs["config_mode"] == "driven"
    assert attrs["source_entity"] == "input_boolean.allow_curtailment"


async def test_driven_mode_ignores_turn_on(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    curtailment_field_info: InputFieldInfo[SwitchEntityDescription],
    horizon_manager: Mock,
) -> None:
    """Switch entity in DRIVEN mode ignores turn on requests."""
    subentry = _create_subentry("Test Solar", {"allow_curtailment": "input_boolean.curtail"})
    config_entry.runtime_data = None

    entity = HaeoInputSwitch(
        hass=hass,
        config_entry=config_entry,
        subentry=subentry,
        field_info=curtailment_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )
    entity._attr_is_on = False  # Simulate loaded state
    entity.async_write_ha_state = Mock()

    await entity.async_turn_on()

    # Value should NOT change in driven mode
    assert entity.is_on is False
    entity.async_write_ha_state.assert_called_once()


async def test_driven_mode_ignores_turn_off(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    curtailment_field_info: InputFieldInfo[SwitchEntityDescription],
    horizon_manager: Mock,
) -> None:
    """Switch entity in DRIVEN mode ignores turn off requests."""
    subentry = _create_subentry("Test Solar", {"allow_curtailment": "input_boolean.curtail"})
    config_entry.runtime_data = None

    entity = HaeoInputSwitch(
        hass=hass,
        config_entry=config_entry,
        subentry=subentry,
        field_info=curtailment_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )
    entity._attr_is_on = True  # Simulate loaded state
    entity.async_write_ha_state = Mock()

    await entity.async_turn_off()

    # Value should NOT change in driven mode
    assert entity.is_on is True
    entity.async_write_ha_state.assert_called_once()


async def test_driven_mode_loads_source_state(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    curtailment_field_info: InputFieldInfo[SwitchEntityDescription],
    horizon_manager: Mock,
) -> None:
    """Switch entity in DRIVEN mode loads initial state from source entity."""
    # Set up source entity state
    hass.states.async_set("input_boolean.curtail", STATE_ON)

    subentry = _create_subentry("Test Solar", {"allow_curtailment": "input_boolean.curtail"})
    config_entry.runtime_data = None

    entity = HaeoInputSwitch(
        hass=hass,
        config_entry=config_entry,
        subentry=subentry,
        field_info=curtailment_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )

    # Call the internal load method
    entity._load_source_state()

    assert entity.is_on is True


async def test_driven_mode_loads_off_state(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    curtailment_field_info: InputFieldInfo[SwitchEntityDescription],
    horizon_manager: Mock,
) -> None:
    """Switch entity in DRIVEN mode loads OFF state from source entity."""
    # Set up source entity state
    hass.states.async_set("input_boolean.curtail", STATE_OFF)

    subentry = _create_subentry("Test Solar", {"allow_curtailment": "input_boolean.curtail"})
    config_entry.runtime_data = None

    entity = HaeoInputSwitch(
        hass=hass,
        config_entry=config_entry,
        subentry=subentry,
        field_info=curtailment_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )

    entity._load_source_state()

    assert entity.is_on is False


# --- Tests for unique ID generation ---


async def test_unique_id_includes_all_components(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    curtailment_field_info: InputFieldInfo[SwitchEntityDescription],
    horizon_manager: Mock,
) -> None:
    """Unique ID includes entry_id, subentry_id, and field_name."""
    subentry = _create_subentry("Test Solar", {"allow_curtailment": True})
    config_entry.runtime_data = None

    entity = HaeoInputSwitch(
        hass=hass,
        config_entry=config_entry,
        subentry=subentry,
        field_info=curtailment_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )

    expected_unique_id = f"{config_entry.entry_id}_{subentry.subentry_id}_{curtailment_field_info.field_name}"
    assert entity.unique_id == expected_unique_id


# --- Tests for entity attributes ---


async def test_entity_has_correct_category(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    curtailment_field_info: InputFieldInfo[SwitchEntityDescription],
    horizon_manager: Mock,
) -> None:
    """Entity should be CONFIG category."""
    subentry = _create_subentry("Test Solar", {"allow_curtailment": True})
    config_entry.runtime_data = None

    entity = HaeoInputSwitch(
        hass=hass,
        config_entry=config_entry,
        subentry=subentry,
        field_info=curtailment_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )

    assert entity.entity_category == EntityCategory.CONFIG


async def test_entity_does_not_poll(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    curtailment_field_info: InputFieldInfo[SwitchEntityDescription],
    horizon_manager: Mock,
) -> None:
    """Entity should not poll."""
    subentry = _create_subentry("Test Solar", {"allow_curtailment": True})
    config_entry.runtime_data = None

    entity = HaeoInputSwitch(
        hass=hass,
        config_entry=config_entry,
        subentry=subentry,
        field_info=curtailment_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )

    assert entity.should_poll is False


async def test_translation_key_from_field_info(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    horizon_manager: Mock,
) -> None:
    """Translation key is derived from field info."""
    field_info: InputFieldInfo[SwitchEntityDescription] = InputFieldInfo(
        field_name="enable_export",
        entity_description=SwitchEntityDescription(
            key="enable_export",
            translation_key="custom_translation",
        ),
        output_type=OutputType.STATUS,
    )
    subentry = _create_subentry("Test", {"enable_export": True})
    config_entry.runtime_data = None

    entity = HaeoInputSwitch(
        hass=hass,
        config_entry=config_entry,
        subentry=subentry,
        field_info=field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )

    assert entity.entity_description.translation_key == "custom_translation"


async def test_translation_key_defaults_to_field_name(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    curtailment_field_info: InputFieldInfo[SwitchEntityDescription],
    horizon_manager: Mock,
) -> None:
    """Translation key defaults to field_name when not specified."""
    subentry = _create_subentry("Test", {"allow_curtailment": True})
    config_entry.runtime_data = None

    entity = HaeoInputSwitch(
        hass=hass,
        config_entry=config_entry,
        subentry=subentry,
        field_info=curtailment_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )

    # Field has no translation_key, so it uses field_name
    assert entity.entity_description.translation_key == "allow_curtailment"


# --- Tests for horizon_start and get_values properties ---


async def test_horizon_start_returns_first_timestamp(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    curtailment_field_info: InputFieldInfo[SwitchEntityDescription],
    horizon_manager: Mock,
) -> None:
    """horizon_start returns the first forecast timestamp."""
    subentry = _create_subentry("Test Solar", {"allow_curtailment": True})
    config_entry.runtime_data = None

    entity = HaeoInputSwitch(
        hass=hass,
        config_entry=config_entry,
        subentry=subentry,
        field_info=curtailment_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )

    # Update forecast manually to simulate loaded state
    entity._update_forecast()

    # horizon_start should return the first timestamp
    assert entity.horizon_start == 0.0


async def test_horizon_start_returns_none_without_forecast(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    curtailment_field_info: InputFieldInfo[SwitchEntityDescription],
    horizon_manager: Mock,
) -> None:
    """horizon_start returns None when forecast is not set."""
    subentry = _create_subentry("Test Solar", {"allow_curtailment": True})
    config_entry.runtime_data = None

    entity = HaeoInputSwitch(
        hass=hass,
        config_entry=config_entry,
        subentry=subentry,
        field_info=curtailment_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )

    # Clear forecast
    entity._attr_extra_state_attributes = {}

    assert entity.horizon_start is None


async def test_get_values_returns_forecast_values(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    curtailment_field_info: InputFieldInfo[SwitchEntityDescription],
    horizon_manager: Mock,
) -> None:
    """get_values returns tuple of forecast values."""
    subentry = _create_subentry("Test Solar", {"allow_curtailment": True})
    config_entry.runtime_data = None

    entity = HaeoInputSwitch(
        hass=hass,
        config_entry=config_entry,
        subentry=subentry,
        field_info=curtailment_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )

    # Simulate entity being added to HA (enables get_values to return data)
    entity._added_to_hass = True

    # Update forecast
    entity._update_forecast()

    values = entity.get_values()
    assert values is not None
    # All values should be True (the switch is on)
    assert all(v is True for v in values)
    # Should have 3 values (one per timestamp)
    assert len(values) == 3


async def test_get_values_returns_none_without_forecast(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    curtailment_field_info: InputFieldInfo[SwitchEntityDescription],
    horizon_manager: Mock,
) -> None:
    """get_values returns None when forecast is not set."""
    subentry = _create_subentry("Test Solar", {"allow_curtailment": True})
    config_entry.runtime_data = None

    entity = HaeoInputSwitch(
        hass=hass,
        config_entry=config_entry,
        subentry=subentry,
        field_info=curtailment_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )

    # Simulate entity being added to HA
    entity._added_to_hass = True

    # Clear forecast
    entity._attr_extra_state_attributes = {}

    assert entity.get_values() is None


# --- Tests for lifecycle methods ---


async def test_async_added_to_hass_editable_uses_config_value(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    curtailment_field_info: InputFieldInfo[SwitchEntityDescription],
    horizon_manager: Mock,
) -> None:
    """async_added_to_hass uses config value in EDITABLE mode (no restore needed)."""
    subentry = _create_subentry("Test Solar", {"allow_curtailment": True})
    config_entry.runtime_data = None

    entity = HaeoInputSwitch(
        hass=hass,
        config_entry=config_entry,
        subentry=subentry,
        field_info=curtailment_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )

    await entity.async_added_to_hass()

    # Should use config value directly
    assert entity.is_on is True


async def test_async_added_to_hass_driven_subscribes_to_source(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    curtailment_field_info: InputFieldInfo[SwitchEntityDescription],
    horizon_manager: Mock,
) -> None:
    """async_added_to_hass subscribes to source entity in DRIVEN mode."""
    hass.states.async_set("input_boolean.curtail", STATE_ON)
    subentry = _create_subentry("Test Solar", {"allow_curtailment": "input_boolean.curtail"})
    config_entry.runtime_data = None

    entity = HaeoInputSwitch(
        hass=hass,
        config_entry=config_entry,
        subentry=subentry,
        field_info=curtailment_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )

    await entity.async_added_to_hass()

    # Subscription should be set up
    assert entity._state_unsub is not None
    assert entity._horizon_unsub is not None


async def test_async_will_remove_from_hass_cleans_up(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    curtailment_field_info: InputFieldInfo[SwitchEntityDescription],
    horizon_manager: Mock,
) -> None:
    """async_will_remove_from_hass cleans up subscriptions."""
    hass.states.async_set("input_boolean.curtail", STATE_ON)
    subentry = _create_subentry("Test Solar", {"allow_curtailment": "input_boolean.curtail"})
    config_entry.runtime_data = None

    entity = HaeoInputSwitch(
        hass=hass,
        config_entry=config_entry,
        subentry=subentry,
        field_info=curtailment_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )

    await entity.async_added_to_hass()
    assert entity._state_unsub is not None

    await entity.async_will_remove_from_hass()

    assert entity._state_unsub is None
    assert entity._horizon_unsub is None


# --- Tests for horizon and source state change handlers ---


async def test_handle_horizon_change_editable_updates_forecast(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    curtailment_field_info: InputFieldInfo[SwitchEntityDescription],
    horizon_manager: Mock,
) -> None:
    """_handle_horizon_change updates forecast in EDITABLE mode."""
    subentry = _create_subentry("Test Solar", {"allow_curtailment": True})
    config_entry.runtime_data = None

    entity = HaeoInputSwitch(
        hass=hass,
        config_entry=config_entry,
        subentry=subentry,
        field_info=curtailment_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )
    entity.async_write_ha_state = Mock()

    # Call horizon change handler
    entity._handle_horizon_change()

    entity.async_write_ha_state.assert_called_once()


async def test_handle_horizon_change_driven_reloads_source(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    curtailment_field_info: InputFieldInfo[SwitchEntityDescription],
    horizon_manager: Mock,
) -> None:
    """_handle_horizon_change reloads source state in DRIVEN mode."""
    hass.states.async_set("input_boolean.curtail", STATE_ON)
    subentry = _create_subentry("Test Solar", {"allow_curtailment": "input_boolean.curtail"})
    config_entry.runtime_data = None

    entity = HaeoInputSwitch(
        hass=hass,
        config_entry=config_entry,
        subentry=subentry,
        field_info=curtailment_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )
    entity.async_write_ha_state = Mock()

    # Call horizon change handler
    entity._handle_horizon_change()

    # Should have loaded source state
    assert entity.is_on is True
    entity.async_write_ha_state.assert_called_once()


async def test_handle_source_state_change_updates_switch(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    curtailment_field_info: InputFieldInfo[SwitchEntityDescription],
    horizon_manager: Mock,
) -> None:
    """_handle_source_state_change updates switch state from event."""
    hass.states.async_set("input_boolean.curtail", STATE_OFF)
    subentry = _create_subentry("Test Solar", {"allow_curtailment": "input_boolean.curtail"})
    config_entry.runtime_data = None

    entity = HaeoInputSwitch(
        hass=hass,
        config_entry=config_entry,
        subentry=subentry,
        field_info=curtailment_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )
    entity.async_write_ha_state = Mock()

    # Create a mock event with new state ON
    mock_event = Mock()
    mock_new_state = Mock()
    mock_new_state.state = STATE_ON
    mock_event.data = {"new_state": mock_new_state}

    # Call source state change handler
    entity._handle_source_state_change(mock_event)

    # Should have updated to ON
    assert entity.is_on is True
    entity.async_write_ha_state.assert_called_once()


async def test_handle_source_state_change_ignores_none_state(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    curtailment_field_info: InputFieldInfo[SwitchEntityDescription],
    horizon_manager: Mock,
) -> None:
    """_handle_source_state_change ignores None new_state."""
    hass.states.async_set("input_boolean.curtail", STATE_ON)
    subentry = _create_subentry("Test Solar", {"allow_curtailment": "input_boolean.curtail"})
    config_entry.runtime_data = None

    entity = HaeoInputSwitch(
        hass=hass,
        config_entry=config_entry,
        subentry=subentry,
        field_info=curtailment_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )
    entity._load_source_state()  # Load initial ON state
    entity.async_write_ha_state = Mock()

    # Create a mock event with None new_state (entity deleted)
    mock_event = Mock()
    mock_event.data = {"new_state": None}

    # Call source state change handler
    entity._handle_source_state_change(mock_event)

    # State should not have changed (still ON from initial load)
    assert entity.is_on is True
    entity.async_write_ha_state.assert_not_called()


async def test_load_source_state_with_none_source_entity(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    curtailment_field_info: InputFieldInfo[SwitchEntityDescription],
    horizon_manager: Mock,
) -> None:
    """_load_source_state returns early when source_entity_id is None."""
    subentry = _create_subentry("Test Solar", {"allow_curtailment": True})  # EDITABLE mode
    config_entry.runtime_data = None

    entity = HaeoInputSwitch(
        hass=hass,
        config_entry=config_entry,
        subentry=subentry,
        field_info=curtailment_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )

    # source_entity_id should be None in EDITABLE mode
    assert entity._source_entity_id is None

    # This should return early without error
    entity._load_source_state()

    # State should still be True from config
    assert entity.is_on is True
