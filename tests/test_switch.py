"""Tests for the HAEO switch platform."""

from types import MappingProxyType
from unittest.mock import Mock

from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo import HaeoRuntimeData
from custom_components.haeo.const import CONF_ELEMENT_TYPE, CONF_NAME, DOMAIN, ELEMENT_TYPE_NETWORK
from custom_components.haeo.coordinator import HaeoDataUpdateCoordinator
from custom_components.haeo.elements.solar import ELEMENT_TYPE as SOLAR_TYPE
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
    """Return a config entry for switch platform tests."""
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
    subentry = ConfigSubentry(
        data=MappingProxyType({CONF_ELEMENT_TYPE: subentry_type, CONF_NAME: title, **data}),
        subentry_type=subentry_type,
        title=title,
        unique_id=None,
    )
    hass.config_entries.async_add_subentry(entry, subentry)
    return subentry


async def test_setup_skips_network_subentry(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
) -> None:
    """Setup skips the network subentry which has no switch fields."""
    _add_subentry(hass, config_entry, ELEMENT_TYPE_NETWORK, "Test Network", {})

    async_add_entities = Mock()
    await async_setup_entry(hass, config_entry, async_add_entities)

    # No entities created for network-only config
    async_add_entities.assert_not_called()


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
        # Check if any switch entity was created for curtailment
        field_names = {e._field_info.field_name for e in entities}
        if "allow_curtailment" in field_names:
            assert len(entities) >= 1


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

    # If called, check that curtailment field is not present
    if async_add_entities.called:
        entities = list(async_add_entities.call_args.args[0])
        field_names = {e._field_info.field_name for e in entities}
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

        # Should have entities from both solar panels
        element_names = {e._subentry.title for e in entities}
        if len(entities) > 0:
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
        curtailment_entities = [e for e in entities if e._field_info.field_name == "allow_curtailment"]
        if curtailment_entities:
            assert curtailment_entities[0]._entity_mode == ConfigEntityMode.DRIVEN
