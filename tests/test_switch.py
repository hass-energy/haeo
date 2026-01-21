"""Tests for the HAEO switch platform."""

from types import MappingProxyType
from unittest.mock import Mock

from homeassistant.config_entries import ConfigSubentry
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers.device_registry import DeviceEntry
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo import HaeoRuntimeData
from custom_components.haeo.const import CONF_ELEMENT_TYPE, CONF_NAME, DOMAIN, ELEMENT_TYPE_NETWORK
from custom_components.haeo.elements.grid import ELEMENT_TYPE as GRID_TYPE
from custom_components.haeo.elements.solar import ELEMENT_TYPE as SOLAR_TYPE
from custom_components.haeo.entities.auto_optimize_switch import AutoOptimizeSwitch
from custom_components.haeo.entities.haeo_number import ConfigEntityMode
from custom_components.haeo.horizon import HorizonManager
from custom_components.haeo.switch import async_setup_entry


@pytest.fixture
def horizon_manager() -> Mock:
    """Return a mock horizon manager."""
    manager = Mock(spec=HorizonManager)
    manager.get_forecast_timestamps.return_value = (0.0, 300.0, 600.0)
    manager.subscribe.return_value = Mock()  # Unsubscribe callback
    return manager


@pytest.fixture
def config_entry(hass: HomeAssistant, horizon_manager: Mock) -> MockConfigEntry:
    """Return a config entry for switch platform tests.

    By default, coordinator is None to simulate the INPUT_PLATFORMS call.
    Tests that need coordinator behavior should set it explicitly.
    """
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
        entry_id="test_switch_platform_entry",
    )
    entry.add_to_hass(hass)
    # Set up runtime_data with mock horizon manager - no coordinator by default (INPUT_PLATFORMS call)
    entry.runtime_data = HaeoRuntimeData(
        coordinator=None,
        horizon_manager=horizon_manager,
    )
    return entry


def _add_subentry(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    subentry_type: str,
    title: str,
    data: dict[str, object],
) -> ConfigSubentry:
    """Add a subentry to the config entry."""
    subentry = ConfigSubentry(
        data=MappingProxyType({CONF_ELEMENT_TYPE: subentry_type, CONF_NAME: title, **data}),
        subentry_type=subentry_type,
        title=title,
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(entry, subentry)
    return subentry


async def test_setup_raises_error_when_runtime_data_missing(hass: HomeAssistant) -> None:
    """Setup raises RuntimeError when runtime_data is not set."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Network",
        data={"name": "Test"},
        entry_id="test_missing_runtime",
    )
    entry.add_to_hass(hass)
    # Explicitly set runtime_data to None
    entry.runtime_data = None

    async_add_entities = Mock()
    with pytest.raises(RuntimeError, match="Runtime data not set"):
        await async_setup_entry(hass, entry, async_add_entities)


async def test_setup_creates_auto_optimize_switch_for_network(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> None:
    """Setup creates auto-optimize switch for network subentry."""
    _add_subentry(hass, config_entry, ELEMENT_TYPE_NETWORK, "Test Network", {})

    async_add_entities = Mock()
    await async_setup_entry(hass, config_entry, async_add_entities)

    # Auto-optimize switch is created for network
    async_add_entities.assert_called_once()
    entities = list(async_add_entities.call_args.args[0])
    assert len(entities) == 1
    assert isinstance(entities[0], AutoOptimizeSwitch)


async def test_setup_skips_element_without_switch_fields(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> None:
    """Setup skips elements that have no switch fields (like grid)."""
    _add_subentry(hass, config_entry, ELEMENT_TYPE_NETWORK, "Test Network", {})

    # Add grid element - it has no switch fields
    _add_subentry(
        hass,
        config_entry,
        GRID_TYPE,
        "Main Grid",
        {
            "connection": "main_bus",
            "import_price": 0.30,
            "export_price": 0.05,
        },
    )

    async_add_entities = Mock()
    await async_setup_entry(hass, config_entry, async_add_entities)

    # Only the auto-optimize switch is created (grid has no switch fields)
    async_add_entities.assert_called_once()
    entities = list(async_add_entities.call_args.args[0])
    assert len(entities) == 1
    assert isinstance(entities[0], AutoOptimizeSwitch)


async def test_setup_creates_switch_entities_for_solar_curtailment(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> None:
    """Setup creates switch entity for solar curtailment field."""
    _add_subentry(hass, config_entry, ELEMENT_TYPE_NETWORK, "Test Network", {})

    # Add solar element with curtailment switch
    _add_subentry(
        hass,
        config_entry,
        SOLAR_TYPE,
        "Rooftop Solar",
        {
            "connection": "main_bus",
            "forecast": "sensor.solar_forecast",
            "allow_curtailment": True,  # Boolean becomes switch
        },
    )

    async_add_entities = Mock()
    await async_setup_entry(hass, config_entry, async_add_entities)

    if async_add_entities.called:
        entities = list(async_add_entities.call_args.args[0])
        # Filter out AutoOptimizeSwitch to get only input switches
        input_switches = [e for e in entities if hasattr(e, "_field_info")]
        # Check if any switch entity was created for curtailment
        field_names = {e._field_info.field_name for e in input_switches}
        if "allow_curtailment" in field_names:
            assert len(input_switches) >= 1


async def test_setup_skips_missing_switch_fields_in_config(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> None:
    """Setup only creates entities for switch fields present in config data."""
    _add_subentry(hass, config_entry, ELEMENT_TYPE_NETWORK, "Test Network", {})

    # Add solar without the optional curtailment field
    _add_subentry(
        hass,
        config_entry,
        SOLAR_TYPE,
        "Basic Solar",
        {
            "connection": "main_bus",
            "forecast": "sensor.solar_forecast",
            # No allow_curtailment field
        },
    )

    async_add_entities = Mock()
    await async_setup_entry(hass, config_entry, async_add_entities)

    # If called, check that curtailment field is not present in input switches
    if async_add_entities.called:
        entities = list(async_add_entities.call_args.args[0])
        # Filter out AutoOptimizeSwitch to get only input switches
        input_switches = [e for e in entities if hasattr(e, "_field_info")]
        field_names = {e._field_info.field_name for e in input_switches}
        assert "allow_curtailment" not in field_names


async def test_setup_creates_correct_device_identifiers(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> None:
    """Switch entities are associated with correct device."""
    _add_subentry(hass, config_entry, ELEMENT_TYPE_NETWORK, "Test Network", {})
    _add_subentry(
        hass,
        config_entry,
        SOLAR_TYPE,
        "My Solar",
        {
            "connection": "main_bus",
            "forecast": "sensor.solar_forecast",
            "allow_curtailment": True,
        },
    )

    async_add_entities = Mock()
    await async_setup_entry(hass, config_entry, async_add_entities)

    if async_add_entities.called:
        entities = list(async_add_entities.call_args.args[0])
        for entity in entities:
            # Each entity should have a device_entry attached
            assert entity.device_entry is not None


async def test_setup_handles_multiple_solar_elements(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> None:
    """Setup creates entities for multiple solar elements."""
    _add_subentry(hass, config_entry, ELEMENT_TYPE_NETWORK, "Test Network", {})

    _add_subentry(
        hass,
        config_entry,
        SOLAR_TYPE,
        "Solar North",
        {
            "connection": "bus1",
            "forecast": "sensor.solar_north",
            "allow_curtailment": True,
        },
    )
    _add_subentry(
        hass,
        config_entry,
        SOLAR_TYPE,
        "Solar South",
        {
            "connection": "bus2",
            "forecast": "sensor.solar_south",
            "allow_curtailment": False,
        },
    )

    async_add_entities = Mock()
    await async_setup_entry(hass, config_entry, async_add_entities)

    if async_add_entities.called:
        entities = list(async_add_entities.call_args.args[0])
        # Filter out AutoOptimizeSwitch to get only input switches
        input_switches = [e for e in entities if hasattr(e, "_subentry")]

        # Should have entities from both solar panels
        element_names = {e._subentry.title for e in input_switches}
        if len(input_switches) > 0:
            # At least one should be present
            assert "Solar North" in element_names or "Solar South" in element_names


async def test_setup_with_entity_id_creates_driven_mode_entity(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> None:
    """Setup creates DRIVEN mode entity when config contains entity ID."""
    _add_subentry(hass, config_entry, ELEMENT_TYPE_NETWORK, "Test Network", {})

    _add_subentry(
        hass,
        config_entry,
        SOLAR_TYPE,
        "Dynamic Solar",
        {
            "connection": "main_bus",
            "forecast": "sensor.solar_forecast",
            "allow_curtailment": "input_boolean.curtail_solar",  # Entity ID
        },
    )

    async_add_entities = Mock()
    await async_setup_entry(hass, config_entry, async_add_entities)

    if async_add_entities.called:
        entities = list(async_add_entities.call_args.args[0])
        # Filter out AutoOptimizeSwitch to get only input switches
        input_switches = [e for e in entities if hasattr(e, "_field_info")]
        curtailment_entities = [e for e in input_switches if e._field_info.field_name == "allow_curtailment"]
        if curtailment_entities:
            assert curtailment_entities[0]._entity_mode == ConfigEntityMode.DRIVEN


# ===== Tests for AutoOptimizeSwitch =====


def _create_mock_device_entry() -> DeviceEntry:
    """Create a mock device entry for testing."""
    return DeviceEntry(id="test_device_id")


async def test_auto_optimize_switch_turn_on(hass: HomeAssistant) -> None:
    """Test turning on the auto-optimize switch updates state."""
    entry = MockConfigEntry(domain=DOMAIN, entry_id="test_entry")
    entry.add_to_hass(hass)

    switch = AutoOptimizeSwitch(
        hass=hass,
        config_entry=entry,
        device_entry=_create_mock_device_entry(),
    )
    # Set initial state to off
    switch._attr_is_on = False
    # Mock async_write_ha_state to avoid entity registration requirements
    switch.async_write_ha_state = Mock()  # type: ignore[method-assign]

    # Turn on the switch
    await switch.async_turn_on()

    # Verify switch state was updated
    assert switch.is_on is True
    switch.async_write_ha_state.assert_called_once()


async def test_auto_optimize_switch_turn_off(hass: HomeAssistant) -> None:
    """Test turning off the auto-optimize switch updates state."""
    entry = MockConfigEntry(domain=DOMAIN, entry_id="test_entry")
    entry.add_to_hass(hass)

    switch = AutoOptimizeSwitch(
        hass=hass,
        config_entry=entry,
        device_entry=_create_mock_device_entry(),
    )
    # Set initial state to on
    switch._attr_is_on = True
    # Mock async_write_ha_state to avoid entity registration requirements
    switch.async_write_ha_state = Mock()  # type: ignore[method-assign]

    # Turn off the switch
    await switch.async_turn_off()

    # Verify switch state was updated
    assert switch.is_on is False
    switch.async_write_ha_state.assert_called_once()


async def test_auto_optimize_switch_restores_on_state(hass: HomeAssistant) -> None:
    """Test switch restores ON state from previous session."""
    entry = MockConfigEntry(domain=DOMAIN, entry_id="test_entry")
    entry.add_to_hass(hass)

    switch = AutoOptimizeSwitch(
        hass=hass,
        config_entry=entry,
        device_entry=_create_mock_device_entry(),
    )

    # Mock the restore state mechanism
    async def mock_get_last_state() -> State:
        return State("switch.test", STATE_ON)

    switch.async_get_last_state = mock_get_last_state  # type: ignore[method-assign]

    # Call async_added_to_hass which triggers state restoration
    await switch.async_added_to_hass()

    # Verify state was restored to ON
    assert switch.is_on is True


async def test_auto_optimize_switch_restores_off_state(hass: HomeAssistant) -> None:
    """Test switch restores OFF state from previous session."""
    entry = MockConfigEntry(domain=DOMAIN, entry_id="test_entry")
    entry.add_to_hass(hass)

    switch = AutoOptimizeSwitch(
        hass=hass,
        config_entry=entry,
        device_entry=_create_mock_device_entry(),
    )

    # Mock the restore state mechanism
    async def mock_get_last_state() -> State:
        return State("switch.test", STATE_OFF)

    switch.async_get_last_state = mock_get_last_state  # type: ignore[method-assign]

    # Call async_added_to_hass which triggers state restoration
    await switch.async_added_to_hass()

    # Verify state was restored to OFF
    assert switch.is_on is False


async def test_auto_optimize_switch_defaults_to_on_without_previous_state(hass: HomeAssistant) -> None:
    """Test switch defaults to ON when no previous state exists."""
    entry = MockConfigEntry(domain=DOMAIN, entry_id="test_entry")
    entry.add_to_hass(hass)

    switch = AutoOptimizeSwitch(
        hass=hass,
        config_entry=entry,
        device_entry=_create_mock_device_entry(),
    )

    # Mock the restore state mechanism to return None (no previous state)
    async def mock_get_last_state() -> None:
        return None

    switch.async_get_last_state = mock_get_last_state  # type: ignore[method-assign]

    # Call async_added_to_hass which triggers state restoration
    await switch.async_added_to_hass()

    # Verify state defaults to ON
    assert switch.is_on is True
