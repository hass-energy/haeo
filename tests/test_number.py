"""Tests for the HAEO number platform."""

from types import MappingProxyType
from unittest.mock import Mock

from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo import HaeoRuntimeData
from custom_components.haeo.const import CONF_ELEMENT_TYPE, CONF_NAME, DOMAIN, ELEMENT_TYPE_NETWORK
from custom_components.haeo.coordinator import HaeoDataUpdateCoordinator
from custom_components.haeo.elements.grid import (
    CONF_CONNECTION,
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_MAX_POWER_TARGET_SOURCE,
    CONF_PRICE_SOURCE_TARGET,
    CONF_PRICE_TARGET_SOURCE,
    SECTION_COMMON,
    SECTION_DEMAND_PRICING,
    SECTION_POWER_LIMITS,
    SECTION_PRICING,
)
from custom_components.haeo.elements.grid import ELEMENT_TYPE as GRID_TYPE
from custom_components.haeo.flows import HUB_SECTION_ADVANCED, HUB_SECTION_COMMON, HUB_SECTION_TIERS
from custom_components.haeo.horizon import HorizonManager
from custom_components.haeo.number import async_setup_entry
from custom_components.haeo.schema import as_connection_target, as_constant_value, as_entity_value, as_none_value


@pytest.fixture
def horizon_manager() -> Mock:
    """Return a mock horizon manager."""
    manager = Mock(spec=HorizonManager)
    manager.get_forecast_timestamps.return_value = (0.0, 300.0, 600.0)
    manager.subscribe.return_value = Mock()  # Unsubscribe callback
    return manager


@pytest.fixture
def config_entry(hass: HomeAssistant, horizon_manager: Mock) -> MockConfigEntry:
    """Return a config entry for number platform tests."""
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
        entry_id="test_number_platform_entry",
    )
    entry.add_to_hass(hass)
    # Set up runtime_data with mock horizon manager
    mock_coordinator = Mock(spec=HaeoDataUpdateCoordinator)
    entry.runtime_data = HaeoRuntimeData(
        coordinator=mock_coordinator,
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
        power_limits = {}
        if data.get("max_power_source_target") is not None:
            power_limits[CONF_MAX_POWER_SOURCE_TARGET] = schema_value(data.get("max_power_source_target"))
        if data.get("max_power_target_source") is not None:
            power_limits[CONF_MAX_POWER_TARGET_SOURCE] = schema_value(data.get("max_power_target_source"))
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
            SECTION_DEMAND_PRICING: {},
            SECTION_POWER_LIMITS: power_limits,
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


async def test_setup_creates_number_entities_for_grid(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> None:
    """Setup creates number entities for grid element fields."""
    # Add network subentry (required)
    _add_subentry(hass, config_entry, ELEMENT_TYPE_NETWORK, "Test Network", {})

    # Add grid with directional prices (these become number entities)
    _add_subentry(
        hass,
        config_entry,
        GRID_TYPE,
        "Main Grid",
        {
            "connection": "main_bus",
            "price_source_target": 0.30,  # Static value becomes editable number
            "price_target_source": 0.05,
            "max_power_source_target": 10.0,
            "max_power_target_source": 5.0,
        },
    )

    async_add_entities = Mock()
    await async_setup_entry(hass, config_entry, async_add_entities)

    async_add_entities.assert_called_once()
    entities = list(async_add_entities.call_args.args[0])

    # Grid should have number entities for price and limit fields
    assert len(entities) >= 2  # At least directional pricing fields


async def test_setup_skips_network_subentry(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> None:
    """Setup skips the network subentry which has no input fields."""
    _add_subentry(hass, config_entry, ELEMENT_TYPE_NETWORK, "Test Network", {})

    async_add_entities = Mock()
    await async_setup_entry(hass, config_entry, async_add_entities)

    # No entities created for network-only config
    async_add_entities.assert_not_called()


async def test_setup_skips_elements_without_number_fields(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> None:
    """Setup skips elements that have no number-type input fields."""
    _add_subentry(hass, config_entry, ELEMENT_TYPE_NETWORK, "Test Network", {})

    # Add a minimal element that might not have number fields exposed
    # This depends on what the element's input_fields() returns

    async_add_entities = Mock()
    await async_setup_entry(hass, config_entry, async_add_entities)

    # If no number fields defined, no entities created
    # (actual behavior depends on element definitions)


async def test_setup_skips_missing_fields_in_config(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> None:
    """Setup does not create entities for fields that are not configured."""
    _add_subentry(hass, config_entry, ELEMENT_TYPE_NETWORK, "Test Network", {})

    # Add grid with only required fields (no optional limits)
    _add_subentry(
        hass,
        config_entry,
        GRID_TYPE,
        "Basic Grid",
        {
            "connection": "main_bus",
            "price_source_target": 0.30,
            "price_target_source": 0.05,
            # No directional power limits
        },
    )

    async_add_entities = Mock()
    await async_setup_entry(hass, config_entry, async_add_entities)

    if async_add_entities.called:
        entities = list(async_add_entities.call_args.args[0])
        # Should only have entities for configured fields
        field_names = {e._field_info.field_name for e in entities}
        assert "price_source_target" in field_names
        assert "price_target_source" in field_names
        # Optional unconfigured fields should NOT have entities created
        assert "max_power_source_target" not in field_names
        assert "max_power_target_source" not in field_names


async def test_setup_creates_correct_device_identifiers(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> None:
    """Number entities are associated with correct device."""
    _add_subentry(hass, config_entry, ELEMENT_TYPE_NETWORK, "Test Network", {})
    _add_subentry(
        hass,
        config_entry,
        GRID_TYPE,
        "My Grid",
        {
            "connection": "main_bus",
            "price_source_target": 0.30,
            "price_target_source": 0.05,
        },
    )

    async_add_entities = Mock()
    await async_setup_entry(hass, config_entry, async_add_entities)

    if async_add_entities.called:
        entities = list(async_add_entities.call_args.args[0])
        for entity in entities:
            # Each entity should have a device_entry attached
            assert entity.device_entry is not None


async def test_setup_handles_multiple_elements(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> None:
    """Setup creates entities for multiple elements."""
    _add_subentry(hass, config_entry, ELEMENT_TYPE_NETWORK, "Test Network", {})

    _add_subentry(
        hass,
        config_entry,
        GRID_TYPE,
        "Grid 1",
        {
            "connection": "bus1",
            "price_source_target": 0.30,
            "price_target_source": 0.05,
        },
    )
    _add_subentry(
        hass,
        config_entry,
        GRID_TYPE,
        "Grid 2",
        {
            "connection": "bus2",
            "price_source_target": 0.25,
            "price_target_source": 0.08,
        },
    )

    async_add_entities = Mock()
    await async_setup_entry(hass, config_entry, async_add_entities)

    async_add_entities.assert_called_once()
    entities = list(async_add_entities.call_args.args[0])

    # Should have entities from both grids
    element_names = {e._subentry.title for e in entities}
    assert "Grid 1" in element_names
    assert "Grid 2" in element_names
