"""Tests for HAEO input entities (number and switch platforms)."""

from collections.abc import Callable
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Any
from unittest.mock import AsyncMock, Mock

from homeassistant.components.number import NumberDeviceClass
from homeassistant.config_entries import ConfigSubentry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.const import CONF_ELEMENT_TYPE, CONF_NAME, DOMAIN
from custom_components.haeo.coordinator import CoordinatorData, ElementData
from custom_components.haeo.elements.battery import ELEMENT_TYPE as BATTERY_TYPE
from custom_components.haeo.elements.solar import ELEMENT_TYPE as SOLAR_TYPE
from custom_components.haeo.entities.haeo_number import HaeoInputNumber
from custom_components.haeo.entities.haeo_switch import HaeoInputSwitch
from custom_components.haeo.entities.mode import ConfigEntityMode
from custom_components.haeo.model.const import OUTPUT_TYPE_BOOLEAN, OUTPUT_TYPE_ENERGY
from custom_components.haeo.number import async_setup_entry as async_setup_number_entry
from custom_components.haeo.schema.input_fields import InputEntityType, InputFieldInfo
from custom_components.haeo.switch import async_setup_entry as async_setup_switch_entry


class _DummyCoordinator:
    """Minimal coordinator stub for input entity tests."""

    def __init__(self) -> None:
        self.data: CoordinatorData | None = None
        self._listeners: list[Callable[[], None]] = []

    def async_add_listener(
        self, update_callback: Callable[[], None], _context: object | None = None
    ) -> Callable[[], None]:
        """Register a listener and return an unsubscribe callback."""
        self._listeners.append(update_callback)
        return lambda: self._listeners.remove(update_callback) if update_callback in self._listeners else None

    async def async_request_refresh(self) -> None:
        """Mock refresh request."""


@pytest.fixture
def coordinator() -> Any:
    """Return a minimal coordinator stub.

    Uses Any return type because we modify attributes in tests.
    The _DummyCoordinator implements the interface needed by HaeoInputNumber/HaeoInputSwitch.
    """
    return _DummyCoordinator()


@pytest.fixture
def config_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Return a config entry with battery and solar subentries."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Network",
        data={"name": "Test Network", "horizon_hours": 1, "period_minutes": 5},
        entry_id="test_entry",
    )
    entry.add_to_hass(hass)

    # Battery subentry with editable capacity (no sensor entity ID)
    battery_subentry = ConfigSubentry(
        data=MappingProxyType(
            {
                CONF_ELEMENT_TYPE: BATTERY_TYPE,
                CONF_NAME: "Test Battery",
                "capacity": 13.5,  # Static value = Editable mode
                "efficiency": 0.95,
            }
        ),
        subentry_type=BATTERY_TYPE,
        title="Test Battery",
        unique_id=None,
        subentry_id="battery_sub",
    )
    hass.config_entries.async_add_subentry(entry, battery_subentry)

    # Battery with driven capacity (sensor entity ID provided)
    battery_driven_subentry = ConfigSubentry(
        data=MappingProxyType(
            {
                CONF_ELEMENT_TYPE: BATTERY_TYPE,
                CONF_NAME: "Driven Battery",
                "capacity": "sensor.battery_capacity",  # Entity ID = Driven mode
            }
        ),
        subentry_type=BATTERY_TYPE,
        title="Driven Battery",
        unique_id=None,
        subentry_id="battery_driven_sub",
    )
    hass.config_entries.async_add_subentry(entry, battery_driven_subentry)

    # Solar subentry with curtailment switch
    solar_subentry = ConfigSubentry(
        data=MappingProxyType(
            {
                CONF_ELEMENT_TYPE: SOLAR_TYPE,
                CONF_NAME: "Test Solar",
                "forecast": "sensor.solar_forecast",
                "curtailment": True,  # Static boolean = Editable mode
            }
        ),
        subentry_type=SOLAR_TYPE,
        title="Test Solar",
        unique_id=None,
        subentry_id="solar_sub",
    )
    hass.config_entries.async_add_subentry(entry, solar_subentry)

    return entry


@pytest.fixture
def battery_subentry(config_entry: MockConfigEntry) -> ConfigSubentry:
    """Return the battery subentry from config_entry."""
    for subentry in config_entry.subentries.values():
        if subentry.title == "Test Battery":
            return subentry
    msg = "Battery subentry not found"
    raise ValueError(msg)


@pytest.fixture
def capacity_field_info() -> InputFieldInfo:
    """Return field info for battery capacity."""
    return InputFieldInfo(
        field_name="capacity",
        entity_type=InputEntityType.NUMBER,
        output_type=OUTPUT_TYPE_ENERGY,
        unit="kWh",
        min_value=0.0,
        max_value=None,
        step=0.001,
        device_class=NumberDeviceClass.ENERGY,
        translation_key="battery_capacity",
    )


@pytest.fixture
def curtailment_field_info() -> InputFieldInfo:
    """Return field info for solar curtailment switch."""
    return InputFieldInfo(
        field_name="curtailment",
        entity_type=InputEntityType.SWITCH,
        output_type=OUTPUT_TYPE_BOOLEAN,
        translation_key="solar_curtailment",
    )


def _create_mock_device_entry(config_entry: MockConfigEntry, subentry: ConfigSubentry) -> Mock:
    """Create a mock DeviceEntry with identifiers matching the expected pattern."""
    device_entry = Mock()
    device_id = subentry.subentry_id
    device_entry.identifiers = {(DOMAIN, f"{config_entry.entry_id}_{device_id}")}
    return device_entry


class TestHaeoInputNumberEditable:
    """Test HaeoInputNumber in Editable mode."""

    async def test_init_editable_mode_with_static_value(
        self,
        hass: HomeAssistant,
        coordinator: Any,
        config_entry: MockConfigEntry,
        battery_subentry: ConfigSubentry,
        capacity_field_info: InputFieldInfo,
    ) -> None:
        """Input number initializes in Editable mode with static config value."""
        entity = HaeoInputNumber(
            hass=hass,
            coordinator=coordinator,
            config_entry=config_entry,
            subentry=battery_subentry,
            field_info=capacity_field_info,
            device_entry=_create_mock_device_entry(config_entry, battery_subentry),
        )

        assert entity._entity_mode == ConfigEntityMode.EDITABLE
        assert entity._attr_native_value == 13.5
        assert entity._source_entity_ids == []
        assert entity._attr_entity_category == EntityCategory.CONFIG
        assert entity._attr_native_unit_of_measurement == "kWh"
        assert entity._attr_device_class == NumberDeviceClass.ENERGY

    async def test_extra_attributes_editable(
        self,
        hass: HomeAssistant,
        coordinator: Any,
        config_entry: MockConfigEntry,
        battery_subentry: ConfigSubentry,
        capacity_field_info: InputFieldInfo,
    ) -> None:
        """Extra state attributes include config_mode and element info."""
        entity = HaeoInputNumber(
            hass=hass,
            coordinator=coordinator,
            config_entry=config_entry,
            subentry=battery_subentry,
            field_info=capacity_field_info,
            device_entry=_create_mock_device_entry(config_entry, battery_subentry),
        )

        attrs = entity._attr_extra_state_attributes
        assert attrs["config_mode"] == "editable"
        assert attrs["element_name"] == "Test Battery"
        assert attrs["element_type"] == BATTERY_TYPE
        assert attrs["output_name"] == "capacity"
        assert attrs["output_type"] == OUTPUT_TYPE_ENERGY
        assert "source_entities" not in attrs

    async def test_set_value_editable_mode(
        self,
        hass: HomeAssistant,
        coordinator: Any,
        config_entry: MockConfigEntry,
        battery_subentry: ConfigSubentry,
        capacity_field_info: InputFieldInfo,
    ) -> None:
        """Setting value in Editable mode updates state and triggers refresh."""
        entity = HaeoInputNumber(
            hass=hass,
            coordinator=coordinator,
            config_entry=config_entry,
            subentry=battery_subentry,
            field_info=capacity_field_info,
            device_entry=_create_mock_device_entry(config_entry, battery_subentry),
        )

        # Mock async_write_ha_state to avoid registration issues
        entity.async_write_ha_state = Mock()
        coordinator.async_request_refresh = AsyncMock()

        await entity.async_set_native_value(20.0)

        assert entity._attr_native_value == 20.0
        entity.async_write_ha_state.assert_called_once()
        coordinator.async_request_refresh.assert_awaited_once()

    async def test_get_current_value(
        self,
        hass: HomeAssistant,
        coordinator: Any,
        config_entry: MockConfigEntry,
        battery_subentry: ConfigSubentry,
        capacity_field_info: InputFieldInfo,
    ) -> None:
        """get_current_value returns the current native value."""
        entity = HaeoInputNumber(
            hass=hass,
            coordinator=coordinator,
            config_entry=config_entry,
            subentry=battery_subentry,
            field_info=capacity_field_info,
            device_entry=_create_mock_device_entry(config_entry, battery_subentry),
        )

        assert entity.get_current_value() == 13.5


class TestHaeoInputNumberDriven:
    """Test HaeoInputNumber in Driven mode."""

    async def test_init_driven_mode_with_entity_id(
        self,
        hass: HomeAssistant,
        coordinator: Any,
        config_entry: MockConfigEntry,
        capacity_field_info: InputFieldInfo,
    ) -> None:
        """Input number initializes in Driven mode when config has entity ID."""
        # Get the driven battery subentry
        driven_subentry = None
        for subentry in config_entry.subentries.values():
            if subentry.title == "Driven Battery":
                driven_subentry = subentry
                break
        assert driven_subentry is not None

        entity = HaeoInputNumber(
            hass=hass,
            coordinator=coordinator,
            config_entry=config_entry,
            subentry=driven_subentry,
            field_info=capacity_field_info,
            device_entry=_create_mock_device_entry(config_entry, driven_subentry),
        )

        assert entity._entity_mode == ConfigEntityMode.DRIVEN
        assert entity._attr_native_value is None
        assert entity._source_entity_ids == ["sensor.battery_capacity"]

    async def test_extra_attributes_driven_includes_source_entities(
        self,
        hass: HomeAssistant,
        coordinator: Any,
        config_entry: MockConfigEntry,
        capacity_field_info: InputFieldInfo,
    ) -> None:
        """Extra state attributes in Driven mode include source_entities."""
        driven_subentry = None
        for subentry in config_entry.subentries.values():
            if subentry.title == "Driven Battery":
                driven_subentry = subentry
                break
        assert driven_subentry is not None

        entity = HaeoInputNumber(
            hass=hass,
            coordinator=coordinator,
            config_entry=config_entry,
            subentry=driven_subentry,
            field_info=capacity_field_info,
            device_entry=_create_mock_device_entry(config_entry, driven_subentry),
        )

        attrs = entity._attr_extra_state_attributes
        assert attrs["config_mode"] == "driven"
        assert attrs["source_entities"] == ["sensor.battery_capacity"]

    async def test_set_value_driven_mode_ignored(
        self,
        hass: HomeAssistant,
        coordinator: Any,
        config_entry: MockConfigEntry,
        capacity_field_info: InputFieldInfo,
    ) -> None:
        """Setting value in Driven mode is ignored."""
        driven_subentry = None
        for subentry in config_entry.subentries.values():
            if subentry.title == "Driven Battery":
                driven_subentry = subentry
                break
        assert driven_subentry is not None

        entity = HaeoInputNumber(
            hass=hass,
            coordinator=coordinator,
            config_entry=config_entry,
            subentry=driven_subentry,
            field_info=capacity_field_info,
            device_entry=_create_mock_device_entry(config_entry, driven_subentry),
        )

        entity.async_write_ha_state = Mock()
        coordinator.async_request_refresh = AsyncMock()

        await entity.async_set_native_value(99.0)

        # Value should not change in Driven mode
        assert entity._attr_native_value is None
        entity.async_write_ha_state.assert_not_called()
        coordinator.async_request_refresh.assert_not_awaited()


class TestHaeoInputNumberCoordinatorUpdates:
    """Test coordinator update handling for HaeoInputNumber."""

    async def test_coordinator_update_builds_forecast(
        self,
        hass: HomeAssistant,
        coordinator: Any,
        config_entry: MockConfigEntry,
        battery_subentry: ConfigSubentry,
        capacity_field_info: InputFieldInfo,
    ) -> None:
        """Coordinator update builds forecast from loaded config values."""
        entity = HaeoInputNumber(
            hass=hass,
            coordinator=coordinator,
            config_entry=config_entry,
            subentry=battery_subentry,
            field_info=capacity_field_info,
            device_entry=_create_mock_device_entry(config_entry, battery_subentry),
        )

        entity.async_write_ha_state = Mock()

        # Simulate coordinator with loaded config - provide all required BatteryConfigData fields
        now = datetime.now(tz=UTC).timestamp()
        coordinator.data = CoordinatorData(
            elements={
                "Test Battery": ElementData(
                    inputs={
                        "element_type": "battery",
                        "name": "Test Battery",
                        "connection": "dc_bus",
                        "capacity": [13.5, 13.5, 13.5],
                        "initial_charge_percentage": [50.0, 50.0, 50.0],
                        "min_charge_percentage": 10.0,
                        "max_charge_percentage": 90.0,
                        "efficiency": 95.0,
                    },  # type: ignore[typeddict-item]
                    outputs={},
                )
            },
            forecast_timestamps=(now, now + 300, now + 600),
        )

        entity._handle_coordinator_update()

        # Should have forecast in attributes
        attrs = entity._attr_extra_state_attributes
        assert "forecast" in attrs
        assert len(attrs["forecast"]) == 3
        assert attrs["forecast"][0]["value"] == 13.5

    async def test_coordinator_update_driven_updates_state(
        self,
        hass: HomeAssistant,
        coordinator: Any,
        config_entry: MockConfigEntry,
        capacity_field_info: InputFieldInfo,
    ) -> None:
        """Coordinator update in Driven mode updates state from first loaded value."""
        driven_subentry = None
        for subentry in config_entry.subentries.values():
            if subentry.title == "Driven Battery":
                driven_subentry = subentry
                break
        assert driven_subentry is not None

        entity = HaeoInputNumber(
            hass=hass,
            coordinator=coordinator,
            config_entry=config_entry,
            subentry=driven_subentry,
            field_info=capacity_field_info,
            device_entry=_create_mock_device_entry(config_entry, driven_subentry),
        )

        entity.async_write_ha_state = Mock()

        # Initial value should be None in Driven mode
        assert entity._attr_native_value is None

        # Simulate coordinator update with loaded values - provide all required BatteryConfigData fields
        now = datetime.now(tz=UTC).timestamp()
        coordinator.data = CoordinatorData(
            elements={
                "Driven Battery": ElementData(
                    inputs={
                        "element_type": "battery",
                        "name": "Driven Battery",
                        "connection": "dc_bus",
                        "capacity": [15.0, 15.0],
                        "initial_charge_percentage": [50.0, 50.0],
                        "min_charge_percentage": 10.0,
                        "max_charge_percentage": 90.0,
                        "efficiency": 95.0,
                    },  # type: ignore[typeddict-item]
                    outputs={},
                )
            },
            forecast_timestamps=(now, now + 300),
        )

        entity._handle_coordinator_update()

        # State should now be set from first loaded value
        assert entity._attr_native_value == 15.0

    async def test_coordinator_update_editable_preserves_state(
        self,
        hass: HomeAssistant,
        coordinator: Any,
        config_entry: MockConfigEntry,
        battery_subentry: ConfigSubentry,
        capacity_field_info: InputFieldInfo,
    ) -> None:
        """Coordinator update in Editable mode preserves user's state value."""
        entity = HaeoInputNumber(
            hass=hass,
            coordinator=coordinator,
            config_entry=config_entry,
            subentry=battery_subentry,
            field_info=capacity_field_info,
            device_entry=_create_mock_device_entry(config_entry, battery_subentry),
        )

        entity.async_write_ha_state = Mock()

        # User sets a value
        entity._attr_native_value = 20.0

        # Simulate coordinator update with different loaded values - provide all required BatteryConfigData fields
        now = datetime.now(tz=UTC).timestamp()
        coordinator.data = CoordinatorData(
            elements={
                "Test Battery": ElementData(
                    inputs={
                        "element_type": "battery",
                        "name": "Test Battery",
                        "connection": "dc_bus",
                        "capacity": [13.5, 13.5],
                        "initial_charge_percentage": [50.0, 50.0],
                        "min_charge_percentage": 10.0,
                        "max_charge_percentage": 90.0,
                        "efficiency": 95.0,
                    },  # type: ignore[typeddict-item]
                    outputs={},
                )
            },
            forecast_timestamps=(now, now + 300),
        )

        entity._handle_coordinator_update()

        # State should still be user's value
        assert entity._attr_native_value == 20.0


class TestHaeoInputSwitch:
    """Test HaeoInputSwitch entity."""

    async def test_init_editable_mode(
        self,
        hass: HomeAssistant,
        coordinator: Any,
        config_entry: MockConfigEntry,
        curtailment_field_info: InputFieldInfo,
    ) -> None:
        """Input switch initializes in Editable mode with static boolean."""
        solar_subentry = None
        for subentry in config_entry.subentries.values():
            if subentry.title == "Test Solar":
                solar_subentry = subentry
                break
        assert solar_subentry is not None

        entity = HaeoInputSwitch(
            hass=hass,
            coordinator=coordinator,
            config_entry=config_entry,
            subentry=solar_subentry,
            field_info=curtailment_field_info,
            device_entry=_create_mock_device_entry(config_entry, solar_subentry),
        )

        assert entity._entity_mode == ConfigEntityMode.EDITABLE
        assert entity._attr_is_on is True
        assert entity._attr_entity_category == EntityCategory.CONFIG

    async def test_extra_attributes(
        self,
        hass: HomeAssistant,
        coordinator: Any,
        config_entry: MockConfigEntry,
        curtailment_field_info: InputFieldInfo,
    ) -> None:
        """Extra state attributes include config_mode and element info."""
        solar_subentry = None
        for subentry in config_entry.subentries.values():
            if subentry.title == "Test Solar":
                solar_subentry = subentry
                break
        assert solar_subentry is not None

        entity = HaeoInputSwitch(
            hass=hass,
            coordinator=coordinator,
            config_entry=config_entry,
            subentry=solar_subentry,
            field_info=curtailment_field_info,
            device_entry=_create_mock_device_entry(config_entry, solar_subentry),
        )

        attrs = entity._attr_extra_state_attributes
        assert attrs["config_mode"] == "editable"
        assert attrs["element_name"] == "Test Solar"
        assert attrs["element_type"] == SOLAR_TYPE
        assert attrs["output_name"] == "curtailment"

    async def test_turn_on(
        self,
        hass: HomeAssistant,
        coordinator: Any,
        config_entry: MockConfigEntry,
        curtailment_field_info: InputFieldInfo,
    ) -> None:
        """Turning switch on updates state and triggers refresh."""
        solar_subentry = None
        for subentry in config_entry.subentries.values():
            if subentry.title == "Test Solar":
                solar_subentry = subentry
                break
        assert solar_subentry is not None

        # Create with initial off state
        modified_subentry = ConfigSubentry(
            data=MappingProxyType(
                {
                    **dict(solar_subentry.data),
                    "curtailment": False,
                }
            ),
            subentry_type=solar_subentry.subentry_type,
            title=solar_subentry.title,
            unique_id=None,
            subentry_id=solar_subentry.subentry_id,
        )

        entity = HaeoInputSwitch(
            hass=hass,
            coordinator=coordinator,
            config_entry=config_entry,
            subentry=modified_subentry,
            field_info=curtailment_field_info,
            device_entry=_create_mock_device_entry(config_entry, solar_subentry),
        )

        entity.async_write_ha_state = Mock()
        coordinator.async_request_refresh = AsyncMock()

        assert entity._attr_is_on is False

        await entity.async_turn_on()

        assert entity._attr_is_on is True
        entity.async_write_ha_state.assert_called_once()
        coordinator.async_request_refresh.assert_awaited_once()

    async def test_turn_off(
        self,
        hass: HomeAssistant,
        coordinator: Any,
        config_entry: MockConfigEntry,
        curtailment_field_info: InputFieldInfo,
    ) -> None:
        """Turning switch off updates state and triggers refresh."""
        solar_subentry = None
        for subentry in config_entry.subentries.values():
            if subentry.title == "Test Solar":
                solar_subentry = subentry
                break
        assert solar_subentry is not None

        entity = HaeoInputSwitch(
            hass=hass,
            coordinator=coordinator,
            config_entry=config_entry,
            subentry=solar_subentry,
            field_info=curtailment_field_info,
            device_entry=_create_mock_device_entry(config_entry, solar_subentry),
        )

        entity.async_write_ha_state = Mock()
        coordinator.async_request_refresh = AsyncMock()

        assert entity._attr_is_on is True

        await entity.async_turn_off()

        assert entity._attr_is_on is False
        entity.async_write_ha_state.assert_called_once()
        coordinator.async_request_refresh.assert_awaited_once()

    async def test_get_current_value(
        self,
        hass: HomeAssistant,
        coordinator: Any,
        config_entry: MockConfigEntry,
        curtailment_field_info: InputFieldInfo,
    ) -> None:
        """get_current_value returns the current boolean state."""
        solar_subentry = None
        for subentry in config_entry.subentries.values():
            if subentry.title == "Test Solar":
                solar_subentry = subentry
                break
        assert solar_subentry is not None

        entity = HaeoInputSwitch(
            hass=hass,
            coordinator=coordinator,
            config_entry=config_entry,
            subentry=solar_subentry,
            field_info=curtailment_field_info,
            device_entry=_create_mock_device_entry(config_entry, solar_subentry),
        )

        assert entity.get_current_value() is True


class TestPlatformSetup:
    """Test platform setup functions."""

    async def test_number_platform_setup_creates_entities(
        self,
        hass: HomeAssistant,
        config_entry: MockConfigEntry,
    ) -> None:
        """Number platform setup creates input number entities."""
        # Set up coordinator on config entry
        coordinator = _DummyCoordinator()
        config_entry.runtime_data = coordinator

        async_add_entities = Mock()

        await async_setup_number_entry(hass, config_entry, async_add_entities)

        # Should have called add_entities with some entities
        async_add_entities.assert_called_once()
        entities = list(async_add_entities.call_args.args[0])
        assert len(entities) > 0
        assert all(isinstance(e, HaeoInputNumber) for e in entities)

    async def test_switch_platform_setup_creates_entities(
        self,
        hass: HomeAssistant,
        config_entry: MockConfigEntry,
    ) -> None:
        """Switch platform setup creates input switch entities."""
        coordinator = _DummyCoordinator()
        config_entry.runtime_data = coordinator

        async_add_entities = Mock()

        await async_setup_switch_entry(hass, config_entry, async_add_entities)

        async_add_entities.assert_called_once()
        entities = list(async_add_entities.call_args.args[0])
        # Solar has curtailment switch
        assert any(isinstance(e, HaeoInputSwitch) for e in entities)

    async def test_platform_setup_no_coordinator(
        self,
        hass: HomeAssistant,
        config_entry: MockConfigEntry,
    ) -> None:
        """Platform setup handles missing coordinator gracefully."""
        config_entry.runtime_data = None

        async_add_entities = Mock()

        await async_setup_number_entry(hass, config_entry, async_add_entities)

        # Should not create entities without coordinator
        async_add_entities.assert_not_called()
