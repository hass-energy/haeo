"""Tests for entity metadata extraction and compatibility checking."""

from homeassistant.const import UnitOfEnergy, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from custom_components.haeo.core.data.loader.extractors import EntityMetadata
from custom_components.haeo.flows.entity_metadata import extract_entity_metadata


def test_entity_metadata_is_compatible_with_none_unit() -> None:
    """Test that None unit is never compatible."""
    metadata = EntityMetadata(entity_id="sensor.test", unit_of_measurement=None)

    assert not metadata.is_compatible_with("kW")
    assert not metadata.is_compatible_with(UnitOfPower)
    assert not metadata.is_compatible_with(["kW", "W"])


def test_entity_metadata_is_compatible_with_string_constant() -> None:
    """Test compatibility with string constant unit spec."""
    metadata = EntityMetadata(entity_id="sensor.test", unit_of_measurement="kW")

    assert metadata.is_compatible_with("kW")
    assert not metadata.is_compatible_with("W")


def test_entity_metadata_is_compatible_with_enum() -> None:
    """Test compatibility with enum unit spec."""
    metadata = EntityMetadata(entity_id="sensor.power", unit_of_measurement="kW")

    assert metadata.is_compatible_with(UnitOfPower)

    metadata_wrong = EntityMetadata(entity_id="sensor.energy", unit_of_measurement="invalid")
    assert not metadata_wrong.is_compatible_with(UnitOfPower)


def test_entity_metadata_is_compatible_with_tuple_pattern() -> None:
    """Test compatibility with tuple pattern unit spec."""
    metadata = EntityMetadata(entity_id="sensor.price", unit_of_measurement="$/kWh")

    assert metadata.is_compatible_with(("*", "/", "kWh"))
    assert not metadata.is_compatible_with(("*", "/", "MWh"))


def test_entity_metadata_is_compatible_with_list_of_specs() -> None:
    """Test compatibility with list of unit specs."""
    metadata = EntityMetadata(entity_id="sensor.power", unit_of_measurement="kW")

    # Should match if any spec in the list matches
    assert metadata.is_compatible_with(["W", "kW", "MW"])
    assert metadata.is_compatible_with([UnitOfPower, UnitOfEnergy])
    assert not metadata.is_compatible_with(["kWh", "Wh"])


def test_entity_metadata_is_compatible_with_list_of_patterns() -> None:
    """Test compatibility with list containing patterns."""
    metadata = EntityMetadata(entity_id="sensor.price", unit_of_measurement="$/kWh")

    assert metadata.is_compatible_with([("*", "/", "kWh"), ("*", "/", "MWh")])
    assert not metadata.is_compatible_with([("*", "/", "day"), "kWh"])


async def test_extract_entity_metadata_filters_domain(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test that extract_entity_metadata filters to sensor and input_number domains."""
    # Register entities
    entity_registry.async_get_or_create(
        domain="sensor",
        platform="test",
        unique_id="power_sensor",
        suggested_object_id="power",
    )
    entity_registry.async_get_or_create(
        domain="light",
        platform="test",
        unique_id="light_test",
        suggested_object_id="test",
    )
    entity_registry.async_get_or_create(
        domain="input_number",
        platform="test",
        unique_id="input_value",
        suggested_object_id="value",
    )

    # Set states
    hass.states.async_set("sensor.power", "100", {"unit_of_measurement": "kW"})
    hass.states.async_set("input_number.value", "50", {"unit_of_measurement": "%"})

    result = extract_entity_metadata(hass)

    # Should only include sensor and input_number, not light
    assert len(result) == 2
    entity_ids = {meta.entity_id for meta in result}
    assert "sensor.power" in entity_ids
    assert "input_number.value" in entity_ids
    assert "light.test" not in entity_ids


async def test_extract_entity_metadata_skips_none_state(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test that extract_entity_metadata skips entities with None state."""
    # Register entities
    entity_registry.async_get_or_create(
        domain="sensor",
        platform="test",
        unique_id="power_sensor",
        suggested_object_id="power",
    )
    entity_registry.async_get_or_create(
        domain="sensor",
        platform="test",
        unique_id="missing_sensor",
        suggested_object_id="missing",
    )

    # Only set state for sensor.power
    hass.states.async_set("sensor.power", "100", {"unit_of_measurement": "kW"})
    # sensor.missing will have None state

    result = extract_entity_metadata(hass)

    # Should only include entities with valid state
    assert len(result) == 1
    assert result[0].entity_id == "sensor.power"


async def test_extract_entity_metadata_includes_none_unit(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test that extract_entity_metadata includes entities without units for exclusion mask."""
    # Register entities
    entity_registry.async_get_or_create(
        domain="sensor",
        platform="test",
        unique_id="power_sensor",
        suggested_object_id="power",
    )
    entity_registry.async_get_or_create(
        domain="sensor",
        platform="test",
        unique_id="no_unit_sensor",
        suggested_object_id="no_unit",
    )

    # Set state with and without units
    hass.states.async_set("sensor.power", "100", {"unit_of_measurement": "kW"})
    hass.states.async_set("sensor.no_unit", "on", {})  # No unit_of_measurement

    result = extract_entity_metadata(hass)

    # Should include both entities (with and without units) for exclusion mask
    assert len(result) == 2
    entity_map = {meta.entity_id: meta for meta in result}
    assert entity_map["sensor.power"].unit_of_measurement == "kW"
    assert entity_map["sensor.no_unit"].unit_of_measurement is None


async def test_extract_entity_metadata_uses_get_extracted_units(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
) -> None:
    """Test that extract_entity_metadata uses get_extracted_units for unit detection."""
    # Register entity
    entity_registry.async_get_or_create(
        domain="sensor",
        platform="test",
        unique_id="forecast_sensor",
        suggested_object_id="forecast",
    )

    # Set state with forecast data (this would be detected by get_extracted_units)
    hass.states.async_set(
        "sensor.forecast",
        "100",
        {
            "unit_of_measurement": "kW",
            "device_class": "power",
        },
    )

    result = extract_entity_metadata(hass)

    # Should extract unit using get_extracted_units
    assert len(result) == 1
    assert result[0].entity_id == "sensor.forecast"
    assert result[0].unit_of_measurement == "kW"
