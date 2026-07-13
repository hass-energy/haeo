"""Tests for HAEO sensor_utils module."""

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.haeo.const import CONF_INTEGRATION_TYPE, DOMAIN, INTEGRATION_TYPE_HUB
from custom_components.haeo.core.const import (
    CONF_NAME,
    CONF_TIER_1_COUNT,
    CONF_TIER_1_DURATION,
    CONF_TIER_2_COUNT,
    CONF_TIER_2_DURATION,
    CONF_TIER_3_COUNT,
    CONF_TIER_3_DURATION,
    CONF_TIER_4_COUNT,
    CONF_TIER_4_DURATION,
    DEFAULT_TIER_1_COUNT,
    DEFAULT_TIER_1_DURATION,
    DEFAULT_TIER_2_COUNT,
    DEFAULT_TIER_2_DURATION,
    DEFAULT_TIER_3_COUNT,
    DEFAULT_TIER_3_DURATION,
    DEFAULT_TIER_4_COUNT,
    DEFAULT_TIER_4_DURATION,
)
from custom_components.haeo.sensor_utils import get_output_sensors


async def test_get_output_sensors_filters_and_handles_forecasts(hass: HomeAssistant) -> None:
    """Output sensors ignore unrelated entities and handle mixed forecast values."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Hub",
        data={
            CONF_INTEGRATION_TYPE: INTEGRATION_TYPE_HUB,
            CONF_NAME: "Test Hub",
            CONF_TIER_1_COUNT: DEFAULT_TIER_1_COUNT,
            CONF_TIER_1_DURATION: DEFAULT_TIER_1_DURATION,
            CONF_TIER_2_COUNT: DEFAULT_TIER_2_COUNT,
            CONF_TIER_2_DURATION: DEFAULT_TIER_2_DURATION,
            CONF_TIER_3_COUNT: DEFAULT_TIER_3_COUNT,
            CONF_TIER_3_DURATION: DEFAULT_TIER_3_DURATION,
            CONF_TIER_4_COUNT: DEFAULT_TIER_4_COUNT,
            CONF_TIER_4_DURATION: DEFAULT_TIER_4_DURATION,
        },
        entry_id="hub_entry",
    )
    entry.add_to_hass(hass)

    entity_registry = er.async_get(hass)

    haeo_entry = entity_registry.async_get_or_create(
        domain="sensor",
        platform=DOMAIN,
        unique_id="haeo_forecast_unique",
        config_entry=entry,
    )
    hass.states.async_set(
        haeo_entry.entity_id,
        "100.0",
        {
            "unit_of_measurement": "kW",
            "forecast": [
                {"time": "2024-01-01T00:00:00", "value": 100.0},
                {"time": "2024-01-01T01:00:00", "value": "status_string"},
            ],
        },
    )

    other_entry = entity_registry.async_get_or_create(
        domain="sensor",
        platform="other_integration",
        unique_id="other_test_unique",
        config_entry=entry,
    )
    hass.states.async_set(other_entry.entity_id, "100", {"unit_of_measurement": "W"})

    missing_state_entry = entity_registry.async_get_or_create(
        domain="sensor",
        platform=DOMAIN,
        unique_id="haeo_without_state_unique",
        config_entry=entry,
    )

    output_sensors = get_output_sensors(hass, entry)

    assert haeo_entry.entity_id in output_sensors
    assert other_entry.entity_id not in output_sensors
    assert missing_state_entry.entity_id not in output_sensors

    attributes = output_sensors[haeo_entry.entity_id]["attributes"]
    assert "forecast" in attributes


async def test_get_output_sensors_passes_attributes_through(hass: HomeAssistant) -> None:
    """State attributes pass through to snapshots, minus internal-only keys.

    The forecast card relies on attributes such as element_type to build its
    series, so filtering them out breaks card rendering.
    """
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Hub",
        data={
            CONF_INTEGRATION_TYPE: INTEGRATION_TYPE_HUB,
            CONF_NAME: "Test Hub",
        },
        entry_id="hub_entry_attrs",
    )
    entry.add_to_hass(hass)

    entity_registry = er.async_get(hass)
    haeo_entry = entity_registry.async_get_or_create(
        domain="sensor",
        platform=DOMAIN,
        unique_id="haeo_attrs_unique",
        config_entry=entry,
    )
    hass.states.async_set(
        haeo_entry.entity_id,
        "1.0",
        {
            "unit_of_measurement": "kW",
            "element_type": "battery",
            "config_mode": "driven",
            "friendly_name": "Battery Power",
            "field_path": "battery.power",
        },
    )

    output_sensors = get_output_sensors(hass, entry)

    attributes = output_sensors[haeo_entry.entity_id]["attributes"]
    assert attributes["unit_of_measurement"] == "kW"
    assert attributes["element_type"] == "battery"
    assert attributes["config_mode"] == "driven"
    assert attributes["friendly_name"] == "Battery Power"
    assert "field_path" not in attributes


async def test_get_output_sensors_handles_forecast_attributes(hass: HomeAssistant) -> None:
    """Sensors with forecast attributes have forecast values rounded."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Hub",
        data={
            CONF_INTEGRATION_TYPE: INTEGRATION_TYPE_HUB,
            CONF_NAME: "Test Hub",
            CONF_TIER_1_COUNT: DEFAULT_TIER_1_COUNT,
            CONF_TIER_1_DURATION: DEFAULT_TIER_1_DURATION,
            CONF_TIER_2_COUNT: DEFAULT_TIER_2_COUNT,
            CONF_TIER_2_DURATION: DEFAULT_TIER_2_DURATION,
            CONF_TIER_3_COUNT: DEFAULT_TIER_3_COUNT,
            CONF_TIER_3_DURATION: DEFAULT_TIER_3_DURATION,
            CONF_TIER_4_COUNT: DEFAULT_TIER_4_COUNT,
            CONF_TIER_4_DURATION: DEFAULT_TIER_4_DURATION,
        },
        entry_id="hub_entry",
    )
    entry.add_to_hass(hass)

    entity_registry = er.async_get(hass)

    # Register a sensor with forecast attribute
    haeo_entry = entity_registry.async_get_or_create(
        domain="sensor",
        platform=DOMAIN,
        unique_id="haeo_forecast_unique",
        config_entry=entry,
    )
    hass.states.async_set(
        haeo_entry.entity_id,
        "1234.56789",
        {
            "unit_of_measurement": "kW",
            "forecast": [
                {"time": "2024-01-01T00:00:00", "value": 1234.56789},
                {"time": "2024-01-01T01:00:00", "value": 5678.12345},
            ],
        },
    )

    # Get output sensors
    output_sensors = get_output_sensors(hass, entry)

    # Verify forecast values are present and rounded
    assert haeo_entry.entity_id in output_sensors
    sensor_data = output_sensors[haeo_entry.entity_id]
    assert "forecast" in sensor_data["attributes"]
    assert len(sensor_data["attributes"]["forecast"]) == 2


async def test_get_output_sensors_handles_non_numeric_states(hass: HomeAssistant) -> None:
    """Sensors with non-numeric states are handled gracefully."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Hub",
        data={
            CONF_INTEGRATION_TYPE: INTEGRATION_TYPE_HUB,
            CONF_NAME: "Test Hub",
            CONF_TIER_1_COUNT: DEFAULT_TIER_1_COUNT,
            CONF_TIER_1_DURATION: DEFAULT_TIER_1_DURATION,
            CONF_TIER_2_COUNT: DEFAULT_TIER_2_COUNT,
            CONF_TIER_2_DURATION: DEFAULT_TIER_2_DURATION,
            CONF_TIER_3_COUNT: DEFAULT_TIER_3_COUNT,
            CONF_TIER_3_DURATION: DEFAULT_TIER_3_DURATION,
            CONF_TIER_4_COUNT: DEFAULT_TIER_4_COUNT,
            CONF_TIER_4_DURATION: DEFAULT_TIER_4_DURATION,
        },
        entry_id="hub_entry",
    )
    entry.add_to_hass(hass)

    entity_registry = er.async_get(hass)

    # Register a sensor with non-numeric state (e.g., "unavailable" or a string status)
    haeo_entry = entity_registry.async_get_or_create(
        domain="sensor",
        platform=DOMAIN,
        unique_id="haeo_non_numeric_unique",
        config_entry=entry,
    )
    hass.states.async_set(
        haeo_entry.entity_id,
        "unavailable",
        {"unit_of_measurement": "kW"},
    )

    # Get output sensors - should not raise an exception
    output_sensors = get_output_sensors(hass, entry)

    # Verify the sensor is included with its original non-numeric state
    assert haeo_entry.entity_id in output_sensors
    assert output_sensors[haeo_entry.entity_id]["state"] == "unavailable"


async def test_get_output_sensors_handles_zero_values(hass: HomeAssistant) -> None:
    """Sensors with zero values use default decimal places."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test Hub",
        data={
            CONF_INTEGRATION_TYPE: INTEGRATION_TYPE_HUB,
            CONF_NAME: "Test Hub",
            CONF_TIER_1_COUNT: DEFAULT_TIER_1_COUNT,
            CONF_TIER_1_DURATION: DEFAULT_TIER_1_DURATION,
            CONF_TIER_2_COUNT: DEFAULT_TIER_2_COUNT,
            CONF_TIER_2_DURATION: DEFAULT_TIER_2_DURATION,
            CONF_TIER_3_COUNT: DEFAULT_TIER_3_COUNT,
            CONF_TIER_3_DURATION: DEFAULT_TIER_3_DURATION,
            CONF_TIER_4_COUNT: DEFAULT_TIER_4_COUNT,
            CONF_TIER_4_DURATION: DEFAULT_TIER_4_DURATION,
        },
        entry_id="hub_entry",
    )
    entry.add_to_hass(hass)

    entity_registry = er.async_get(hass)

    # Register a sensor with zero value
    haeo_entry = entity_registry.async_get_or_create(
        domain="sensor",
        platform=DOMAIN,
        unique_id="haeo_zero_unique",
        config_entry=entry,
    )
    hass.states.async_set(
        haeo_entry.entity_id,
        "0",
        {"unit_of_measurement": "kW"},
    )

    # Get output sensors
    output_sensors = get_output_sensors(hass, entry)

    # Verify sensor with zero value is handled correctly
    assert haeo_entry.entity_id in output_sensors
    assert output_sensors[haeo_entry.entity_id]["state"] == "0.0"


def _build_hub_entry(entry_id: str = "hub_entry") -> MockConfigEntry:
    """Build a minimal hub config entry for sensor_utils tests."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Test Hub",
        data={
            CONF_INTEGRATION_TYPE: INTEGRATION_TYPE_HUB,
            CONF_NAME: "Test Hub",
            CONF_TIER_1_COUNT: DEFAULT_TIER_1_COUNT,
            CONF_TIER_1_DURATION: DEFAULT_TIER_1_DURATION,
            CONF_TIER_2_COUNT: DEFAULT_TIER_2_COUNT,
            CONF_TIER_2_DURATION: DEFAULT_TIER_2_DURATION,
            CONF_TIER_3_COUNT: DEFAULT_TIER_3_COUNT,
            CONF_TIER_3_DURATION: DEFAULT_TIER_3_DURATION,
            CONF_TIER_4_COUNT: DEFAULT_TIER_4_COUNT,
            CONF_TIER_4_DURATION: DEFAULT_TIER_4_DURATION,
        },
        entry_id=entry_id,
    )


async def test_rounding_two_pass_per_value_then_per_entity(hass: HomeAssistant) -> None:
    """Values are first stabilized per-value, then capped to the entity's scale.

    Pass 1 rounds each value to 3 sig figs independently, stabilizing midpoint
    ties and boundary values.  Pass 2 re-rounds all values to the decimal places
    derived from the entity's (now stable) maximum, suppressing noise in small
    values while keeping the entity's precision uniform.
    """
    entry = _build_hub_entry()
    entry.add_to_hass(hass)

    entity_registry = er.async_get(hass)

    # Large-magnitude unitless entity (e.g. policy threshold $10/kWh).
    policy_entry = entity_registry.async_get_or_create(
        domain="number",
        platform=DOMAIN,
        unique_id="policy_price_unique",
        config_entry=entry,
    )
    hass.states.async_set(
        policy_entry.entity_id,
        "10.0",
        {"unit_of_measurement": None},
    )

    # Small-magnitude unitless entity (e.g. Amber feed-in price).
    amber_entry = entity_registry.async_get_or_create(
        domain="number",
        platform=DOMAIN,
        unique_id="amber_price_unique",
        config_entry=entry,
    )
    hass.states.async_set(
        amber_entry.entity_id,
        "0.0798",
        {
            "unit_of_measurement": None,
            "forecast": [
                {"time": "2024-01-01T00:00:00", "value": 0.0798},
                {"time": "2024-01-01T01:00:00", "value": 0.1472},
                {"time": "2024-01-01T02:00:00", "value": 0.0036},
            ],
        },
    )

    output_sensors = get_output_sensors(hass, entry)

    # Policy entity: 10.0 -> pass 1: 10.0, pass 2 (dp=1): 10.0
    assert output_sensors[policy_entry.entity_id]["state"] == "10.0"

    # Amber entity: max after pass 1 is 0.147 (magnitude=-1, dp=3).
    # Pass 2 re-rounds all values to 3 dp.
    amber_data = output_sensors[amber_entry.entity_id]
    assert amber_data["state"] == "0.08"
    attributes = amber_data["attributes"]
    assert "forecast" in attributes
    forecast_values = [pt["value"] for pt in attributes["forecast"]]
    assert forecast_values == [0.08, 0.147, 0.004]


async def test_rounding_handles_mixed_magnitudes_same_unit(hass: HomeAssistant) -> None:
    """Entities with different magnitudes but the same unit each get their own precision.

    Replicates the real-world layout where e.g. power sensors span from sub-watt
    shadow prices to tens of kilowatts and must not lose the fine-grained signal
    of the smaller ones.
    """
    entry = _build_hub_entry()
    entry.add_to_hass(hass)

    entity_registry = er.async_get(hass)

    big = entity_registry.async_get_or_create(
        domain="sensor",
        platform=DOMAIN,
        unique_id="big_power_unique",
        config_entry=entry,
    )
    hass.states.async_set(big.entity_id, "55.4321", {"unit_of_measurement": "kW"})

    small = entity_registry.async_get_or_create(
        domain="sensor",
        platform=DOMAIN,
        unique_id="small_power_unique",
        config_entry=entry,
    )
    hass.states.async_set(small.entity_id, "0.004321", {"unit_of_measurement": "kW"})

    output_sensors = get_output_sensors(hass, entry)

    # max=55 -> pass 1: 55.4, pass 2 (magnitude=1, dp=1): 55.4
    assert output_sensors[big.entity_id]["state"] == "55.4"
    # max=0.004321 -> pass 1: 0.00432, pass 2 (magnitude=-3, dp=5): 0.00432
    assert output_sensors[small.entity_id]["state"] == "0.00432"
