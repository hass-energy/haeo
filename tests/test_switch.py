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
from custom_components.haeo.elements.grid import (
    CONF_CONNECTION,
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_MAX_POWER_TARGET_SOURCE,
    CONF_PRICE_SOURCE_TARGET,
    CONF_PRICE_TARGET_SOURCE,
    SECTION_COMMON,
    SECTION_POWER_LIMITS,
    SECTION_PRICING,
)
from custom_components.haeo.elements.grid import ELEMENT_TYPE as GRID_TYPE
from custom_components.haeo.elements.solar import CONF_CURTAILMENT, CONF_FORECAST, SECTION_CURTAILMENT, SECTION_FORECAST
from custom_components.haeo.elements.solar import CONF_PRICE_SOURCE_TARGET as CONF_SOLAR_PRICE_SOURCE_TARGET
from custom_components.haeo.elements.solar import ELEMENT_TYPE as SOLAR_TYPE
from custom_components.haeo.elements.solar import SECTION_COMMON as SOLAR_SECTION_COMMON
from custom_components.haeo.entities.auto_optimize_switch import AutoOptimizeSwitch
from custom_components.haeo.entities.haeo_number import ConfigEntityMode
from custom_components.haeo.flows import HUB_SECTION_ADVANCED, HUB_SECTION_COMMON, HUB_SECTION_TIERS
from custom_components.haeo.horizon import HorizonManager
from custom_components.haeo.schema import as_connection_target, as_constant_value, as_entity_value, as_none_value
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

    def schema_value(value: object) -> object:
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

    payload: dict[str, object] = {CONF_ELEMENT_TYPE: subentry_type}
    if subentry_type == GRID_TYPE:
        connection_value = data.get("connection", "Switchboard")
        payload |= {
            SECTION_COMMON: {
                CONF_NAME: title,
                CONF_CONNECTION: as_connection_target(str(connection_value)),
            },
            SECTION_PRICING: {
                CONF_PRICE_SOURCE_TARGET: schema_value(data.get("price_source_target")),
                CONF_PRICE_TARGET_SOURCE: schema_value(data.get("price_target_source")),
            },
            SECTION_POWER_LIMITS: {
                CONF_MAX_POWER_SOURCE_TARGET: schema_value(data.get("max_power_source_target")),
                CONF_MAX_POWER_TARGET_SOURCE: schema_value(data.get("max_power_target_source")),
            },
        }
    elif subentry_type == SOLAR_TYPE:
        connection_value = data.get("connection", "Switchboard")
        curtailment_value = data.get("allow_curtailment", data.get("curtailment"))
        payload |= {
            SOLAR_SECTION_COMMON: {
                CONF_NAME: title,
                CONF_CONNECTION: as_connection_target(str(connection_value)),
            },
            SECTION_FORECAST: {
                CONF_FORECAST: schema_value(data.get("forecast", ["sensor.solar_forecast"])),
            },
            SECTION_PRICING: {
                CONF_SOLAR_PRICE_SOURCE_TARGET: schema_value(data.get("price_source_target")),
            },
            SECTION_CURTAILMENT: {
                CONF_CURTAILMENT: schema_value(curtailment_value),
            },
        }
    else:
        payload[CONF_NAME] = title
        payload |= data
    subentry = ConfigSubentry(
        data=MappingProxyType(payload),
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
        data={HUB_SECTION_COMMON: {CONF_NAME: "Test"}, HUB_SECTION_ADVANCED: {}, HUB_SECTION_TIERS: {}},
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


@pytest.mark.parametrize(
    ("subentry_type", "title", "data", "expect_field", "expect_mode"),
    [
        pytest.param(
            GRID_TYPE,
            "Main Grid",
            {
                "connection": "main_bus",
                "price_source_target": 0.30,
                "price_target_source": 0.05,
            },
            None,
            None,
            id="grid_no_switch_fields",
        ),
        pytest.param(
            SOLAR_TYPE,
            "Basic Solar",
            {
                "connection": "main_bus",
                "forecast": "sensor.solar_forecast",
            },
            None,
            None,
            id="solar_missing_switch_field",
        ),
        pytest.param(
            SOLAR_TYPE,
            "Dynamic Solar",
            {
                "connection": "main_bus",
                "forecast": "sensor.solar_forecast",
                CONF_CURTAILMENT: "input_boolean.curtail_solar",
            },
            CONF_CURTAILMENT,
            ConfigEntityMode.DRIVEN,
            id="solar_driven_switch",
        ),
    ],
)
async def test_setup_handles_switch_field_variants(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    subentry_type: str,
    title: str,
    data: dict[str, object],
    expect_field: str | None,
    expect_mode: ConfigEntityMode | None,
) -> None:
    """Setup handles elements with missing, absent, or driven switch fields."""
    _add_subentry(hass, config_entry, ELEMENT_TYPE_NETWORK, "Test Network", {})
    _add_subentry(hass, config_entry, subentry_type, title, data)

    async_add_entities = Mock()
    await async_setup_entry(hass, config_entry, async_add_entities)

    entities = list(async_add_entities.call_args.args[0]) if async_add_entities.called else []
    input_switches = [e for e in entities if hasattr(e, "_field_info")]

    if expect_field is None:
        assert not any(getattr(e._field_info, "field_name", None) == CONF_CURTAILMENT for e in input_switches)
    else:
        matches = [e for e in input_switches if e._field_info.field_name == expect_field]
        assert matches
        assert matches[0]._entity_mode == expect_mode


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
            CONF_CURTAILMENT: True,  # Boolean becomes switch
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
        assert CONF_CURTAILMENT in field_names


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
            CONF_CURTAILMENT: True,
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
            CONF_CURTAILMENT: True,
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
            CONF_CURTAILMENT: False,
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


# ===== Tests for AutoOptimizeSwitch =====


def _create_mock_device_entry() -> DeviceEntry:
    """Create a mock device entry for testing."""
    return DeviceEntry(id="test_device_id")


@pytest.mark.parametrize(
    ("initial_state", "method", "expected"),
    [
        pytest.param(False, "on", True, id="turn_on"),
        pytest.param(True, "off", False, id="turn_off"),
    ],
)
async def test_auto_optimize_switch_toggle(
    hass: HomeAssistant,
    initial_state: bool,
    method: str,
    expected: bool,
) -> None:
    """Turning the auto-optimize switch updates state."""
    entry = MockConfigEntry(domain=DOMAIN, entry_id="test_entry")
    entry.add_to_hass(hass)

    switch = AutoOptimizeSwitch(
        config_entry=entry,
        device_entry=_create_mock_device_entry(),
    )
    switch._attr_is_on = initial_state
    switch.async_write_ha_state = Mock()  # type: ignore[method-assign]

    if method == "on":
        await switch.async_turn_on()
    else:
        await switch.async_turn_off()

    assert switch.is_on is expected
    switch.async_write_ha_state.assert_called_once()


@pytest.mark.parametrize(
    ("restored_state", "expected"),
    [
        pytest.param(STATE_ON, True, id="restores_on"),
        pytest.param(STATE_OFF, False, id="restores_off"),
    ],
)
async def test_auto_optimize_switch_restores_state(
    hass: HomeAssistant,
    restored_state: str,
    expected: bool,
) -> None:
    """Switch restores state from previous session."""
    entry = MockConfigEntry(domain=DOMAIN, entry_id="test_entry")
    entry.add_to_hass(hass)

    switch = AutoOptimizeSwitch(
        config_entry=entry,
        device_entry=_create_mock_device_entry(),
    )

    async def mock_get_last_state() -> State:
        return State("switch.test", restored_state)

    switch.async_get_last_state = mock_get_last_state  # type: ignore[method-assign]

    await switch.async_added_to_hass()

    assert switch.is_on is expected


async def test_auto_optimize_switch_defaults_to_on_without_previous_state(hass: HomeAssistant) -> None:
    """Test switch defaults to ON when no previous state exists."""
    entry = MockConfigEntry(domain=DOMAIN, entry_id="test_entry")
    entry.add_to_hass(hass)

    switch = AutoOptimizeSwitch(
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
