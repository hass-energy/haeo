"""Sensor platform for Home Assistant Energy Optimization integration."""

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.haeo.const import (
    ATTR_ENERGY,
    ATTR_POWER,
    DOMAIN,
    SENSOR_TYPE_ENERGY,
    SENSOR_TYPE_POWER,
    SENSOR_TYPE_SOC,
)
from custom_components.haeo.coordinator import HaeoDataUpdateCoordinator
from custom_components.haeo.sensors.energy import HaeoEnergySensor
from custom_components.haeo.sensors.optimization import (
    HaeoOptimizationCostSensor,
    HaeoOptimizationDurationSensor,
    HaeoOptimizationStatusSensor,
)
from custom_components.haeo.sensors.power import HaeoPowerSensor
from custom_components.haeo.sensors.soc import HaeoSOCSensor
from custom_components.haeo.sensors.types import DataSource

_LOGGER = logging.getLogger(__name__)


async def async_register_devices(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Register devices with the device registry."""
    device_registry_client = device_registry.async_get(hass)

    # Register the main network device
    device_registry_client.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        identifiers={(DOMAIN, config_entry.entry_id)},
        name="HAEO Network",
        manufacturer="HAEO",
        model="entity.device.network",
        sw_version="1.0.0",
    )

    # Register devices for each participant element
    participants = config_entry.data.get("participants", {})
    for element_name, element_config in participants.items():
        element_type = element_config.get("type", "")

        device_registry_client.async_get_or_create(
            config_entry_id=config_entry.entry_id,
            identifiers={(DOMAIN, f"{config_entry.entry_id}_{element_name}")},
            name=element_name,
            manufacturer="HAEO",
            model=f"entity.device.{element_type}",
            via_device=(DOMAIN, config_entry.entry_id),
        )


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up HAEO sensor platform."""
    coordinator: HaeoDataUpdateCoordinator | None = getattr(config_entry, "runtime_data", None)

    # Cannot create any sensors without a coordinator
    if not coordinator:
        _LOGGER.debug("No coordinator available, skipping sensor setup")
        return

    # Register devices with the device registry
    try:
        await async_register_devices(hass, config_entry)
    except Exception as ex:
        _LOGGER.warning("Failed to register devices", exc_info=ex)

    entities = _create_sensors(coordinator, config_entry)

    if entities:
        async_add_entities(entities)


def _create_sensors(
    coordinator: HaeoDataUpdateCoordinator,
    config_entry: ConfigEntry,
) -> list[SensorEntity]:
    """Create all HAEO sensors."""
    entities: list[SensorEntity] = []

    # Add hub-level optimization sensors
    entities.append(HaeoOptimizationCostSensor(coordinator, config_entry))
    entities.append(HaeoOptimizationStatusSensor(coordinator, config_entry))
    entities.append(HaeoOptimizationDurationSensor(coordinator, config_entry))

    # Add element-specific sensors
    participants = config_entry.data.get("participants", {})
    for element_name, element_config in participants.items():
        element_type = element_config.get("type", "")

        # Determine which sensors to create for this element
        sensor_configs = _get_element_sensor_configs(coordinator, element_name, element_type)

        for sensor_config in sensor_configs:
            # Use factory to create the sensor
            sensor = sensor_config["factory"](coordinator, config_entry, element_name, element_type)
            entities.append(sensor)

    return entities


def _get_element_sensor_configs(
    coordinator: HaeoDataUpdateCoordinator,
    element_name: str,
    element_type: str,
) -> list[dict[str, Any]]:
    """Get sensor configurations for an element based on its type.

    Each element type defines which sensors it should create.
    """
    sensor_configs: list[dict[str, Any]] = []

    # Check if we have optimization data for this element
    optimization_result = coordinator.optimization_result
    if optimization_result and "solution" in optimization_result:
        solution = optimization_result["solution"]
        has_power_data = f"{element_name}_{ATTR_POWER}" in solution
        has_energy_data = f"{element_name}_{ATTR_ENERGY}" in solution
    else:
        # Assume we'll have data when optimization runs
        has_power_data = True
        has_energy_data = True

    # Define sensors based on element type
    if element_type in ["photovoltaics", "solar"]:
        # Photovoltaics/Solar: optimized power output + available power forecast
        if has_power_data:
            sensor_configs.append(
                {
                    "factory": lambda coord, entry, name, etype: HaeoPowerSensor(
                        coord, entry, name, etype, data_source=DataSource.OPTIMIZED, translation_key=SENSOR_TYPE_POWER
                    )
                }
            )
        # Available power shows the forecast/capacity
        sensor_configs.append(
            {
                "factory": lambda coord, entry, name, etype: HaeoPowerSensor(
                    coord,
                    entry,
                    name,
                    etype,
                    data_source=DataSource.FORECAST,
                    translation_key="available_power",
                    name_suffix="Available Power",
                )
            }
        )

    elif element_type == "battery":
        # Battery: power, energy, and SOC
        if has_power_data:
            sensor_configs.append(
                {
                    "factory": lambda coord, entry, name, etype: HaeoPowerSensor(
                        coord, entry, name, etype, data_source=DataSource.OPTIMIZED, translation_key=SENSOR_TYPE_POWER
                    )
                }
            )
        if has_energy_data:
            sensor_configs.append(
                {
                    "factory": lambda coord, entry, name, etype: HaeoEnergySensor(
                        coord, entry, name, etype, translation_key=SENSOR_TYPE_ENERGY
                    )
                }
            )
            sensor_configs.append(
                {
                    "factory": lambda coord, entry, name, etype: HaeoSOCSensor(
                        coord, entry, name, etype, translation_key=SENSOR_TYPE_SOC
                    )
                }
            )

    elif element_type == "grid":
        # Grid: bidirectional power (import/export)
        if has_power_data:
            sensor_configs.append(
                {
                    "factory": lambda coord, entry, name, etype: HaeoPowerSensor(
                        coord, entry, name, etype, data_source=DataSource.OPTIMIZED, translation_key=SENSOR_TYPE_POWER
                    )
                }
            )

    elif element_type in ["load", "constant_load", "forecast_load"]:
        # Loads: power consumption only
        if has_power_data:
            sensor_configs.append(
                {
                    "factory": lambda coord, entry, name, etype: HaeoPowerSensor(
                        coord, entry, name, etype, data_source=DataSource.OPTIMIZED, translation_key=SENSOR_TYPE_POWER
                    )
                }
            )

    # Fallback for any other element type
    elif has_power_data:
        sensor_configs.append(
            {
                "factory": lambda coord, entry, name, etype: HaeoPowerSensor(
                    coord, entry, name, etype, data_source=DataSource.OPTIMIZED, translation_key=SENSOR_TYPE_POWER
                )
            }
        )

    return sensor_configs
