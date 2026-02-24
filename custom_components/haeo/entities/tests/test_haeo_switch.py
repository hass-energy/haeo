"""Tests for the HAEO switch input entity."""

import logging
from datetime import timedelta
from types import MappingProxyType
from typing import Any
from unittest.mock import Mock

from homeassistant.components.switch import SwitchEntityDescription
from homeassistant.config_entries import ConfigSubentry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import EntityPlatform
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.const import CONF_RECORD_FORECASTS, DOMAIN
from custom_components.haeo.core.const import CONF_NAME
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.schema import as_connection_target, as_constant_value, as_entity_value, as_none_value
from custom_components.haeo.core.schema.elements.solar import (
    CONF_FORECAST,
    CONF_PRICE_SOURCE_TARGET,
    SECTION_CURTAILMENT,
    SECTION_FORECAST,
    SECTION_PRICING,
)
from custom_components.haeo.core.schema.sections import CONF_CONNECTION
from custom_components.haeo.elements.input_fields import InputFieldDefaults, InputFieldInfo
from custom_components.haeo.entities.haeo_number import ConfigEntityMode
from custom_components.haeo.entities.haeo_switch import FORECAST_UNRECORDED_ATTRIBUTES, HaeoInputSwitch
from custom_components.haeo.flows import HUB_SECTION_ADVANCED, HUB_SECTION_COMMON, HUB_SECTION_TIERS
from custom_components.haeo.horizon import HorizonManager

# --- Fixtures ---


@pytest.fixture
def config_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Return a config entry for switch entity tests."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Network",
        data={
            HUB_SECTION_COMMON: {CONF_NAME: "Test Network"},
            HUB_SECTION_TIERS: {
                "tier_1_count": 2,
                "tier_1_duration": 5,
                "tier_2_count": 0,
                "tier_2_duration": 15,
                "tier_3_count": 0,
                "tier_3_duration": 30,
                "tier_4_count": 0,
                "tier_4_duration": 60,
            },
            HUB_SECTION_ADVANCED: {},
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

    def schema_value(value: Any) -> Any:
        if value is None:
            return as_none_value()
        if isinstance(value, bool):
            return as_constant_value(value)
        if isinstance(value, (int, float)):
            return as_constant_value(float(value))
        if isinstance(value, str):
            return as_entity_value([value])
        if isinstance(value, list) and all(isinstance(item, str) for item in value):
            return as_entity_value(value)
        msg = f"Unsupported schema value {value!r}"
        raise TypeError(msg)

    return ConfigSubentry(
        data=MappingProxyType(
            {
                "element_type": "solar",
                CONF_NAME: name,
                CONF_CONNECTION: as_connection_target("Switchboard"),
                SECTION_FORECAST: {
                    CONF_FORECAST: as_entity_value(["sensor.solar_forecast"]),
                },
                SECTION_PRICING: {
                    CONF_PRICE_SOURCE_TARGET: as_constant_value(0.0),
                },
                SECTION_CURTAILMENT: {key: schema_value(value) for key, value in data.items()},
            }
        ),
        subentry_type="solar",
        title=name,
        unique_id=None,
    )


async def _add_entity_to_hass(hass: HomeAssistant, entity: Entity) -> None:
    """Add entity to Home Assistant via a real EntityPlatform."""
    platform = EntityPlatform(
        hass=hass,
        logger=logging.getLogger(__name__),
        domain="switch",
        platform_name=DOMAIN,
        platform=None,
        scan_interval=timedelta(seconds=30),
        entity_namespace=None,
    )
    await platform.async_add_entities([entity])
    await hass.async_block_till_done()


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


async def test_editable_mode_with_raw_boolean(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    curtailment_field_info: InputFieldInfo[SwitchEntityDescription],
    horizon_manager: Mock,
) -> None:
    """Switch entity handles raw boolean config values."""
    subentry = ConfigSubentry(
        data=MappingProxyType(
            {
                "element_type": "solar",
                CONF_NAME: "Raw Bool",
                CONF_CONNECTION: as_connection_target("Switchboard"),
                SECTION_FORECAST: {CONF_FORECAST: as_entity_value(["sensor.solar_forecast"])},
                SECTION_PRICING: {CONF_PRICE_SOURCE_TARGET: as_constant_value(0.0)},
                SECTION_CURTAILMENT: {curtailment_field_info.field_name: True},
            }
        ),
        subentry_type="solar",
        title="Raw Bool",
        unique_id=None,
    )
    config_entry.runtime_data = None

    entity = HaeoInputSwitch(
        config_entry=config_entry,
        subentry=subentry,
        field_info=curtailment_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )

    assert entity._entity_mode == ConfigEntityMode.EDITABLE
    assert entity.is_on is True


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
        config_entry=config_entry,
        subentry=subentry,
        field_info=curtailment_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )
    await _add_entity_to_hass(hass, entity)
    hass.config_entries.async_update_subentry = Mock()

    await entity.async_turn_on()

    assert entity.is_on is True
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
        config_entry=config_entry,
        subentry=subentry,
        field_info=curtailment_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )
    await _add_entity_to_hass(hass, entity)
    hass.config_entries.async_update_subentry = Mock()

    await entity.async_turn_off()

    assert entity.is_on is False
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


async def test_driven_mode_inert_after_added_to_hass(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    curtailment_field_info: InputFieldInfo[SwitchEntityDescription],
    horizon_manager: Mock,
) -> None:
    """DRIVEN entity remains inert after async_added_to_hass, even when source state exists."""
    hass.states.async_set("input_boolean.curtail", "on")

    subentry = _create_subentry("Test Solar", {"allow_curtailment": "input_boolean.curtail"})
    config_entry.runtime_data = None

    entity = HaeoInputSwitch(
        config_entry=config_entry,
        subentry=subentry,
        field_info=curtailment_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )

    await _add_entity_to_hass(hass, entity)

    assert entity.is_on is None


async def test_driven_mode_receives_value_via_update_display(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    curtailment_field_info: InputFieldInfo[SwitchEntityDescription],
    horizon_manager: Mock,
) -> None:
    """DRIVEN entity receives its value from update_display()."""
    subentry = _create_subentry("Test Solar", {"allow_curtailment": "input_boolean.curtail"})
    config_entry.runtime_data = None

    entity = HaeoInputSwitch(
        config_entry=config_entry,
        subentry=subentry,
        field_info=curtailment_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )

    assert entity.is_on is None

    entity.async_write_ha_state = Mock()
    entity.update_display(False, [0.0, 300.0, 600.0])

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
        config_entry=config_entry,
        subentry=subentry,
        field_info=curtailment_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )

    expected_unique_id = (
        f"{config_entry.entry_id}_{subentry.subentry_id}_curtailment.{curtailment_field_info.field_name}"
    )
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
        config_entry=config_entry,
        subentry=subentry,
        field_info=curtailment_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )

    # Field has no translation_key, so it uses field_name
    assert entity.entity_description.translation_key == "allow_curtailment"


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
        config_entry=config_entry,
        subentry=subentry,
        field_info=curtailment_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )

    await _add_entity_to_hass(hass, entity)

    # Should use config value directly
    assert entity.is_on is True


async def test_editable_applies_default_in_init(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    horizon_manager: Mock,
) -> None:
    """Editable entity applies defaults in __init__ when config value is None."""
    field_info = InputFieldInfo(
        field_name="allow_curtailment",
        entity_description=SwitchEntityDescription(
            key="allow_curtailment",
            translation_key="allow_curtailment",
        ),
        output_type=OutputType.STATUS,
        defaults=InputFieldDefaults(mode="value", value=True),
    )
    subentry = _create_subentry("Test Solar", {"allow_curtailment": None})
    config_entry.runtime_data = None

    entity = HaeoInputSwitch(
        config_entry=config_entry,
        subentry=subentry,
        field_info=field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )

    assert entity.is_on is True


async def test_async_added_to_hass_driven_starts_inert(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    curtailment_field_info: InputFieldInfo[SwitchEntityDescription],
    horizon_manager: Mock,
) -> None:
    """DRIVEN entity starts inert after async_added_to_hass."""
    hass.states.async_set("input_boolean.curtail", "on")
    subentry = _create_subentry("Test Solar", {"allow_curtailment": "input_boolean.curtail"})
    config_entry.runtime_data = None

    entity = HaeoInputSwitch(
        config_entry=config_entry,
        subentry=subentry,
        field_info=curtailment_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )

    await _add_entity_to_hass(hass, entity)

    assert entity.is_on is None


# --- Tests for entity mode ---


async def test_entity_mode_property_returns_mode(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    curtailment_field_info: InputFieldInfo[SwitchEntityDescription],
    horizon_manager: Mock,
) -> None:
    """entity_mode property returns the correct mode."""
    # Test EDITABLE mode
    subentry_editable = _create_subentry("Test Solar", {"allow_curtailment": True})
    config_entry.runtime_data = None

    entity_editable = HaeoInputSwitch(
        config_entry=config_entry,
        subentry=subentry_editable,
        field_info=curtailment_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )
    assert entity_editable.entity_mode == ConfigEntityMode.EDITABLE

    # Test DRIVEN mode
    subentry_driven = _create_subentry("Test Solar", {"allow_curtailment": "input_boolean.curtail"})
    entity_driven = HaeoInputSwitch(
        config_entry=config_entry,
        subentry=subentry_driven,
        field_info=curtailment_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )
    assert entity_driven.entity_mode == ConfigEntityMode.DRIVEN


# --- Tests for defaults ---


async def test_editable_mode_uses_defaults_value_when_none(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    horizon_manager: Mock,
) -> None:
    """Switch entity uses defaults.value in __init__ when config value is None."""

    field_info: InputFieldInfo[SwitchEntityDescription] = InputFieldInfo(
        field_name="optional_toggle",
        entity_description=SwitchEntityDescription(
            key="optional_toggle",
            translation_key="optional_toggle",
        ),
        output_type=OutputType.STATUS,
        defaults=InputFieldDefaults(value=True),
    )

    subentry = _create_subentry("Test Solar", {"optional_toggle": None})
    config_entry.runtime_data = None

    entity = HaeoInputSwitch(
        config_entry=config_entry,
        subentry=subentry,
        field_info=field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )

    assert entity.is_on is True


# --- Tests for update_display ---


async def test_update_display_sets_value_and_forecast(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    curtailment_field_info: InputFieldInfo[SwitchEntityDescription],
    horizon_manager: Mock,
) -> None:
    """update_display updates is_on and generates forecast entries."""
    subentry = _create_subentry("Test Solar", {"allow_curtailment": "input_boolean.curtail"})
    config_entry.runtime_data = None

    entity = HaeoInputSwitch(
        config_entry=config_entry,
        subentry=subentry,
        field_info=curtailment_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )
    entity.async_write_ha_state = Mock()

    entity.update_display(True, [100.0, 400.0, 700.0])

    assert entity.is_on is True
    attrs = entity.extra_state_attributes
    assert attrs is not None
    forecast = attrs["forecast"]
    assert len(forecast) == 3
    assert all(point["value"] is True for point in forecast)
    assert [point["time"].timestamp() for point in forecast] == [100.0, 400.0, 700.0]
    entity.async_write_ha_state.assert_called_once()


async def test_update_display_with_false_value(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    device_entry: Mock,
    curtailment_field_info: InputFieldInfo[SwitchEntityDescription],
    horizon_manager: Mock,
) -> None:
    """update_display with False generates correct forecast timestamps."""
    subentry = _create_subentry("Test Solar", {"allow_curtailment": True})
    config_entry.runtime_data = None

    entity = HaeoInputSwitch(
        config_entry=config_entry,
        subentry=subentry,
        field_info=curtailment_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )
    entity.async_write_ha_state = Mock()

    entity.update_display(False, [0.0, 300.0, 600.0])

    assert entity.is_on is False
    attrs = entity.extra_state_attributes
    assert attrs is not None
    forecast = attrs["forecast"]
    assert len(forecast) == 3
    assert all(point["value"] is False for point in forecast)
    assert [point["time"].timestamp() for point in forecast] == [0.0, 300.0, 600.0]


# --- Recorder Filtering Tests ---


@pytest.mark.parametrize(
    ("record_forecasts", "expect_unrecorded"),
    [
        (False, True),  # Default: forecasts are excluded from recorder
        (True, False),  # When enabled: forecasts are recorded
    ],
)
async def test_unrecorded_attributes_based_on_config(
    hass: HomeAssistant,
    device_entry: Mock,
    curtailment_field_info: InputFieldInfo[SwitchEntityDescription],
    horizon_manager: Mock,
    record_forecasts: bool,
    expect_unrecorded: bool,
) -> None:
    """Switch entity applies recorder filtering based on record_forecasts config."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Network",
        data={
            "name": "Test Network",
            CONF_RECORD_FORECASTS: record_forecasts,
            "tier_1_count": 2,
            "tier_1_duration": 5,
            "tier_2_count": 0,
            "tier_2_duration": 15,
            "tier_3_count": 0,
            "tier_3_duration": 30,
            "tier_4_count": 0,
            "tier_4_duration": 60,
        },
        entry_id="test_entry",
    )
    entry.add_to_hass(hass)
    subentry = _create_subentry("Test Solar", {"curtailment": True})
    entry.runtime_data = None

    entity = HaeoInputSwitch(
        config_entry=entry,
        subentry=subentry,
        field_info=curtailment_field_info,
        device_entry=device_entry,
        horizon_manager=horizon_manager,
    )

    entity._state_info = {"unrecorded_attributes": frozenset()}
    entity._apply_recorder_attribute_filtering()
    if expect_unrecorded:
        assert entity._state_info["unrecorded_attributes"] == FORECAST_UNRECORDED_ATTRIBUTES
    else:
        assert entity._state_info["unrecorded_attributes"] == frozenset()
