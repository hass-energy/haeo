"""Sensor platform for Home Assistant Energy Optimization integration."""

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from custom_components.haeo.const import ATTR_ENERGY, ATTR_POWER, DOMAIN
from custom_components.haeo.coordinator import HaeoDataUpdateCoordinator
from custom_components.haeo.elements import get_model_description, is_element_config_schema
from custom_components.haeo.sensors.energy import SENSOR_TYPE_ENERGY, HaeoEnergySensor
from custom_components.haeo.sensors.optimization import (
    SENSOR_TYPE_OPTIMIZATION_COST,
    SENSOR_TYPE_OPTIMIZATION_DURATION,
    SENSOR_TYPE_OPTIMIZATION_STATUS,
    HaeoOptimizationCostSensor,
    HaeoOptimizationDurationSensor,
    HaeoOptimizationStatusSensor,
)
from custom_components.haeo.sensors.power import SENSOR_TYPE_AVAILABLE_POWER, SENSOR_TYPE_POWER, HaeoPowerSensor
from custom_components.haeo.sensors.soc import SENSOR_TYPE_SOC, HaeoSOCSensor
from custom_components.haeo.sensors.types import DataSource

_LOGGER = logging.getLogger(__name__)

SENSOR_TYPES: tuple[str, ...] = (
    SENSOR_TYPE_OPTIMIZATION_COST,
    SENSOR_TYPE_OPTIMIZATION_STATUS,
    SENSOR_TYPE_OPTIMIZATION_DURATION,
    SENSOR_TYPE_POWER,
    SENSOR_TYPE_ENERGY,
    SENSOR_TYPE_SOC,
)


async def async_register_devices(hass: HomeAssistant, config_entry: ConfigEntry) -> dict[str, str]:
    """Register devices for validated subentries and return their IDs."""

    device_registry_client = device_registry.async_get(hass)
    device_ids: dict[str, str] = {}

    for subentry in config_entry.subentries.values():
        if subentry.subentry_type == "network" and not is_element_config_schema(subentry.data):
            model_description = subentry.subentry_type
        elif is_element_config_schema(subentry.data):
            model_description = get_model_description(subentry.data)
        else:
            _LOGGER.warning(
                "Skipping device registration for subentry %s with invalid configuration",
                subentry.subentry_id,
            )
            continue

        device_ids[subentry.title] = device_registry_client.async_get_or_create(
            config_entry_id=config_entry.entry_id,
            config_subentry_id=subentry.subentry_id,
            identifiers={(DOMAIN, f"{config_entry.entry_id}_{subentry.title}")},
            name=subentry.title,
            manufacturer="HAEO",
            model=model_description,
        ).id

    return device_ids


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up HAEO sensor platform."""

    coordinator: HaeoDataUpdateCoordinator | None = getattr(config_entry, "runtime_data", None)
    if coordinator is None:
        _LOGGER.debug("No coordinator available, skipping sensor setup")
        return

    device_ids = await async_register_devices(hass, config_entry)

    entities: list[SensorEntity] = []

    for subentry in config_entry.subentries.values():
        entities.extend(
            [
                c["factory"](
                    coordinator, subentry, subentry.title, subentry.subentry_type, device_ids.get(subentry.title)
                )
                for c in _get_element_sensor_configs(coordinator, subentry.title, subentry.subentry_type)
            ]
        )

    if entities:
        async_add_entities(entities)


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
    if element_type == "network":
        # Network element gets the optimization sensors
        sensor_configs.append(
            {"factory": lambda coord, entry, _name, _etype, dev_id: HaeoOptimizationCostSensor(coord, entry, dev_id)}
        )
        sensor_configs.append(
            {"factory": lambda coord, entry, _name, _etype, dev_id: HaeoOptimizationStatusSensor(coord, entry, dev_id)}
        )
        sensor_configs.append(
            {
                "factory": lambda coord, entry, _name, _etype, dev_id: HaeoOptimizationDurationSensor(
                    coord, entry, dev_id
                )
            }
        )
        return sensor_configs

    if element_type in ["photovoltaics", "solar"]:
        # Photovoltaics/Solar: optimized power output + available power forecast
        if has_power_data:
            sensor_configs.append(
                {
                    "factory": lambda coord, entry, name, etype, dev_id: HaeoPowerSensor(
                        coord,
                        entry,
                        name,
                        etype,
                        dev_id,
                        data_source=DataSource.OPTIMIZED,
                        translation_key=SENSOR_TYPE_POWER,
                    )
                }
            )
        # Available power shows the forecast/capacity
        sensor_configs.append(
            {
                "factory": lambda coord, entry, name, etype, dev_id: HaeoPowerSensor(
                    coord,
                    entry,
                    name,
                    etype,
                    dev_id,
                    data_source=DataSource.FORECAST,
                    translation_key=SENSOR_TYPE_AVAILABLE_POWER,
                    name_suffix="Available Power",
                )
            }
        )

    elif element_type == "battery":
        # Battery: power, energy, and SOC
        if has_power_data:
            sensor_configs.append(
                {
                    "factory": lambda coord, entry, name, etype, dev_id: HaeoPowerSensor(
                        coord,
                        entry,
                        name,
                        etype,
                        dev_id,
                        data_source=DataSource.OPTIMIZED,
                        translation_key=SENSOR_TYPE_POWER,
                    )
                }
            )
        if has_energy_data:
            sensor_configs.append(
                {
                    "factory": lambda coord, entry, name, etype, dev_id: HaeoEnergySensor(
                        coord, entry, name, etype, dev_id, translation_key=SENSOR_TYPE_ENERGY
                    )
                }
            )
            sensor_configs.append(
                {
                    "factory": lambda coord, entry, name, etype, dev_id: HaeoSOCSensor(
                        coord, entry, name, etype, dev_id, translation_key=SENSOR_TYPE_SOC
                    )
                }
            )

    elif element_type == "grid":
        # Grid: bidirectional power (import/export)
        if has_power_data:
            sensor_configs.append(
                {
                    "factory": lambda coord, entry, name, etype, dev_id: HaeoPowerSensor(
                        coord,
                        entry,
                        name,
                        etype,
                        dev_id,
                        data_source=DataSource.OPTIMIZED,
                        translation_key=SENSOR_TYPE_POWER,
                    )
                }
            )

    elif element_type in ["load", "constant_load", "forecast_load"]:
        # Loads: power consumption only
        if has_power_data:
            sensor_configs.append(
                {
                    "factory": lambda coord, entry, name, etype, dev_id: HaeoPowerSensor(
                        coord,
                        entry,
                        name,
                        etype,
                        dev_id,
                        data_source=DataSource.OPTIMIZED,
                        translation_key=SENSOR_TYPE_POWER,
                    )
                }
            )

    # Fallback for any other element type
    elif has_power_data:
        sensor_configs.append(
            {
                "factory": lambda coord, entry, name, etype, dev_id: HaeoPowerSensor(
                    coord,
                    entry,
                    name,
                    etype,
                    dev_id,
                    data_source=DataSource.OPTIMIZED,
                    translation_key=SENSOR_TYPE_POWER,
                )
            }
        )

    return sensor_configs
