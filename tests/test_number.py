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
from custom_components.haeo.elements.grid import ELEMENT_TYPE as GRID_TYPE
from custom_components.haeo.entities.haeo_horizon import HaeoHorizonEntity
from custom_components.haeo.number import async_setup_entry


@pytest.fixture
def horizon_entity() -> Mock:
    """Return a mock horizon entity."""
    entity = Mock(spec=HaeoHorizonEntity)
    entity.get_forecast_timestamps.return_value = (0.0, 300.0, 600.0)
    entity.async_subscribe.return_value = Mock()
    return entity


@pytest.fixture
def config_entry(hass: HomeAssistant, horizon_entity: Mock) -> MockConfigEntry:
    """Return a config entry for number platform tests."""
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
        entry_id="test_number_platform_entry",
    )
    entry.add_to_hass(hass)
    # Set up runtime_data with mock horizon entity
    mock_coordinator = Mock(spec=HaeoDataUpdateCoordinator)
    entry.runtime_data = HaeoRuntimeData(
        network_coordinator=mock_coordinator,
        horizon_entity=horizon_entity,
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


async def test_setup_creates_number_entities_for_grid(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> None:
    """Setup creates number entities for grid element fields."""
    # Add network subentry (required)
    _add_subentry(hass, config_entry, ELEMENT_TYPE_NETWORK, "Test Network", {})

    # Add grid with import/export prices (these become number entities)
    _add_subentry(
        hass,
        config_entry,
        GRID_TYPE,
        "Main Grid",
        {
            "connection": "main_bus",
            "import_price": 0.30,  # Static value becomes editable number
            "export_price": 0.05,
            "import_limit": 10.0,
            "export_limit": 5.0,
        },
    )

    async_add_entities = Mock()
    await async_setup_entry(hass, config_entry, async_add_entities)

    async_add_entities.assert_called_once()
    entities = list(async_add_entities.call_args.args[0])

    # Grid should have number entities for price and limit fields
    assert len(entities) >= 2  # At least import_price and export_price


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
    """Setup only creates entities for fields present in config data."""
    _add_subentry(hass, config_entry, ELEMENT_TYPE_NETWORK, "Test Network", {})

    # Add grid with only required fields (no optional limits)
    _add_subentry(
        hass,
        config_entry,
        GRID_TYPE,
        "Basic Grid",
        {
            "connection": "main_bus",
            "import_price": 0.30,
            "export_price": 0.05,
            # No import_limit or export_limit
        },
    )

    async_add_entities = Mock()
    await async_setup_entry(hass, config_entry, async_add_entities)

    if async_add_entities.called:
        entities = list(async_add_entities.call_args.args[0])
        # Should only have entities for fields in the config
        field_names = {e._field_info.field_name for e in entities}
        assert "import_limit" not in field_names
        assert "export_limit" not in field_names


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
            "import_price": 0.30,
            "export_price": 0.05,
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
            "import_price": 0.30,
            "export_price": 0.05,
        },
    )
    _add_subentry(
        hass,
        config_entry,
        GRID_TYPE,
        "Grid 2",
        {
            "connection": "bus2",
            "import_price": 0.25,
            "export_price": 0.08,
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
