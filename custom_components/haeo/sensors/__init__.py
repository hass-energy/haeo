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
    CONF_ELEMENT_TYPE,
    CONF_PARTICIPANTS,
    DOMAIN,
    SENSOR_TYPE_ENERGY,
    SENSOR_TYPE_POWER,
    SENSOR_TYPE_SOC,
)
from custom_components.haeo.coordinator import HaeoDataUpdateCoordinator
from custom_components.haeo.schema import load
from custom_components.haeo.sensors.energy import HaeoEnergySensor
from custom_components.haeo.sensors.optimization import (
    HaeoOptimizationCostSensor,
    HaeoOptimizationDurationSensor,
    HaeoOptimizationStatusSensor,
)
from custom_components.haeo.sensors.power import HaeoPowerSensor
from custom_components.haeo.sensors.soc import HaeoSOCSensor
from custom_components.haeo.sensors.types import DataSource
from custom_components.haeo.types import ElementConfigData, get_model_description

_LOGGER = logging.getLogger(__name__)


async def _get_model_description(element_config: dict[str, Any], hass: HomeAssistant) -> str:
    """Get model description string from element configuration.

    Args:
        element_config: Schema mode element configuration
        hass: Home Assistant instance for loading data

    Returns:
        Formatted model description string

    """
    element_type = str(element_config.get(CONF_ELEMENT_TYPE, ""))

    # Load element config into Data mode
    loaded_config: ElementConfigData
    try:
        loaded_config = await load(
            element_config,  # type: ignore[arg-type]
            hass=hass,
            forecast_times=[],
        )
    except Exception:
        # Fallback to generic title-cased element type
        return element_type.replace("_", " ").title()

    # Call type-specific model_description function via dispatch
    try:
        return get_model_description(loaded_config)
    except ValueError:
        # Fallback for unknown element types
        return element_type.replace("_", " ").title()


async def async_register_devices(
    hass: HomeAssistant, config_entry: ConfigEntry, coordinator: HaeoDataUpdateCoordinator
) -> dict[str, str]:
    """Register devices with proper subentry associations BEFORE entities are created.

    Returns a mapping of element_name -> device_id for linking entities to devices.
    """
    device_registry_client = device_registry.async_get(hass)
    device_ids: dict[str, str] = {}

    # Register each subentry's device with explicit subentry association
    for subentry in config_entry.subentries.values():
        element_name = subentry.data.get("name_value")
        if not element_name:
            _LOGGER.warning("Subentry %s has no name_value, skipping device registration", subentry.subentry_id)
            continue

        element_type = subentry.subentry_type

        # Build device name and model description
        if element_type == "network":
            device_name = element_name
            model_string = "Energy Optimization Network"
        else:
            device_name = element_name
            # Get element config from coordinator for detailed model description
            participants = coordinator.config.get(CONF_PARTICIPANTS, {})
            element_config = participants.get(element_name, {})
            if element_config:
                model_string = await _get_model_description(element_config, hass)
            else:
                # Fallback if not in coordinator config
                model_string = element_type.replace("_", " ").title()

        # Create device with subentry association from the start
        device = device_registry_client.async_get_or_create(
            config_entry_id=config_entry.entry_id,
            config_subentry_id=subentry.subentry_id,
            identifiers={(DOMAIN, f"{config_entry.entry_id}_{element_name}")},
            name=device_name,
            manufacturer="HAEO",
            model=model_string,
            translation_key=element_type,
        )

        # Store device ID for entity creation
        device_ids[element_name] = device.id

    return device_ids


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

    # FIRST: Register devices with subentry associations and get device IDs
    device_ids = await async_register_devices(hass, config_entry, coordinator)

    # SECOND: Create sensors with explicit device_id links
    entities = _create_sensors(coordinator, config_entry, device_ids)

    if entities:
        async_add_entities(entities)


def _create_sensors(
    coordinator: HaeoDataUpdateCoordinator,
    config_entry: ConfigEntry,
    device_ids: dict[str, str],
) -> list[SensorEntity]:
    """Create all HAEO sensors with explicit device ID links."""
    entities: list[SensorEntity] = []

    # Build mapping of participant names to subentries from hub's subentries
    participant_subentries: dict[str, Any] = {}
    network_subentry = None
    for subentry in config_entry.subentries.values():
        name = subentry.data.get("name_value")
        if name:
            participant_subentries[name] = subentry
            # Track network subentry separately for optimization sensors
            if subentry.subentry_type == "network":
                network_subentry = subentry

    # Create network-level optimization sensors if network subentry exists
    if network_subentry:
        network_name = network_subentry.data.get("name_value", "Network")
        network_device_id = device_ids.get(network_name)
        if network_device_id:
            # Create the three optimization sensors
            sensor_configs = _get_element_sensor_configs(coordinator, network_name, "network")
            for sensor_config in sensor_configs:
                sensor = sensor_config["factory"](
                    coordinator, network_subentry, network_name, "network", network_device_id
                )
                entities.append(sensor)
        else:
            _LOGGER.warning("No device ID found for network element, skipping optimization sensors")

    # Add element-specific sensors for all participants (from coordinator.config)
    # All elements are treated equally - no special cases
    participants = coordinator.config.get(CONF_PARTICIPANTS, {})
    for element_name, element_config in participants.items():
        element_type = element_config.get("type", "")

        # Find the subentry for this participant
        subentry = participant_subentries.get(element_name)
        if not subentry:
            _LOGGER.warning(
                "No subentry found for participant %s, skipping sensor creation",
                element_name,
            )
            continue

        # Get the device ID for this element
        device_id = device_ids.get(element_name)
        if not device_id:
            _LOGGER.warning(
                "No device ID found for element %s, skipping sensor creation",
                element_name,
            )
            continue

        # Determine which sensors to create for this element
        sensor_configs = _get_element_sensor_configs(coordinator, element_name, element_type)

        for sensor_config in sensor_configs:
            # Use factory to create the sensor with device_id for direct linking
            sensor = sensor_config["factory"](coordinator, subentry, element_name, element_type, device_id)
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
