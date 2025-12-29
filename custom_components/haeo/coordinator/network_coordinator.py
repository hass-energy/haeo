"""Data update coordinator for the Home Assistant Energy Optimizer integration."""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
import time
from typing import Any, Literal, TypedDict

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.debounce import Debouncer
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.translation import async_get_translations
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from custom_components.haeo import data as data_module
from custom_components.haeo.const import (
    CONF_DEBOUNCE_SECONDS,
    CONF_UPDATE_INTERVAL_MINUTES,
    DEFAULT_DEBOUNCE_SECONDS,
    DEFAULT_UPDATE_INTERVAL_MINUTES,
    DOMAIN,
    ELEMENT_TYPE_NETWORK,
    OPTIMIZATION_STATUS_FAILED,
    OPTIMIZATION_STATUS_PENDING,
    OPTIMIZATION_STATUS_SUCCESS,
    OUTPUT_NAME_OPTIMIZATION_COST,
    OUTPUT_NAME_OPTIMIZATION_DURATION,
    OUTPUT_NAME_OPTIMIZATION_STATUS,
    NetworkOutputName,
)
from custom_components.haeo.elements import (
    ELEMENT_TYPES,
    ElementConfigSchema,
    ElementDeviceName,
    ElementOutputName,
    collect_element_subentries,
)
from custom_components.haeo.model import (
    OUTPUT_TYPE_COST,
    OUTPUT_TYPE_DURATION,
    OUTPUT_TYPE_ENERGY,
    OUTPUT_TYPE_POWER,
    OUTPUT_TYPE_POWER_FLOW,
    OUTPUT_TYPE_POWER_LIMIT,
    OUTPUT_TYPE_PRICE,
    OUTPUT_TYPE_SHADOW_PRICE,
    OUTPUT_TYPE_SOC,
    OUTPUT_TYPE_STATUS,
    ModelOutputName,
    Network,
    OutputData,
    OutputType,
)
from custom_components.haeo.repairs import dismiss_optimization_failure_issue
from custom_components.haeo.util.forecast_times import generate_forecast_timestamps, tiers_to_periods_seconds

_LOGGER = logging.getLogger(__name__)


def collect_entity_ids(value: Any) -> set[str]:
    """Recursively collect entity IDs from nested configuration values.

    Entity IDs are identified by containing a '.' (e.g., 'sensor.temperature').
    Plain strings without dots (like element names 'AC Bus') are not entity IDs.
    """
    if isinstance(value, str):
        # Entity IDs contain a domain separator (e.g., sensor.temperature)
        # Element names don't have dots (e.g., "AC Bus", "network")
        return {value} if "." in value else set()

    if isinstance(value, Mapping):
        mapping_ids: set[str] = set()
        for nested in value.values():
            mapping_ids.update(collect_entity_ids(nested))
        return mapping_ids

    if isinstance(value, Sequence) and not isinstance(value, str):
        sequence_ids: set[str] = set()
        for nested in value:
            sequence_ids.update(collect_entity_ids(nested))
        return sequence_ids

    return set()


def extract_entity_ids_from_config(config: ElementConfigSchema) -> set[str]:
    """Extract entity IDs from a configuration.

    Collects entity IDs from list[str] fields in the config, which represent
    sensor entity ID lists in the new explicit schema format.
    """
    entity_ids: set[str] = set()

    for field_name, field_value in config.items():
        # Skip metadata fields and None values
        if field_name in ("element_type", "name") or field_value is None:
            continue

        try:
            entity_ids.update(collect_entity_ids(field_value))
        except TypeError:
            continue

    return entity_ids


class ForecastPoint(TypedDict):
    """Single point in a forecast time series.

    Attributes:
        time: Timestamp as datetime object (timezone-aware)
        value: Forecast value (numeric or other types depending on output type)

    """

    time: datetime
    value: Any


@dataclass(frozen=True, slots=True)
class CoordinatorOutput:
    """Processed output ready for Home Assistant entities."""

    type: OutputType
    unit: str | None
    state: StateType | None
    forecast: list[ForecastPoint] | None
    direction: Literal["+", "-"] | None = None
    entity_category: EntityCategory | None = None
    device_class: SensorDeviceClass | None = None
    state_class: SensorStateClass | None = None
    options: tuple[str, ...] | None = None
    advanced: bool = False


DEVICE_CLASS_MAP: dict[OutputType, SensorDeviceClass] = {
    OUTPUT_TYPE_POWER: SensorDeviceClass.POWER,
    OUTPUT_TYPE_POWER_FLOW: SensorDeviceClass.POWER,
    OUTPUT_TYPE_POWER_LIMIT: SensorDeviceClass.POWER,
    OUTPUT_TYPE_ENERGY: SensorDeviceClass.ENERGY,
    OUTPUT_TYPE_SOC: SensorDeviceClass.BATTERY,
    OUTPUT_TYPE_COST: SensorDeviceClass.MONETARY,
    OUTPUT_TYPE_PRICE: SensorDeviceClass.MONETARY,
    OUTPUT_TYPE_SHADOW_PRICE: SensorDeviceClass.MONETARY,
    OUTPUT_TYPE_DURATION: SensorDeviceClass.DURATION,
    OUTPUT_TYPE_STATUS: SensorDeviceClass.ENUM,
}

STATE_CLASS_MAP: dict[OutputType, SensorStateClass | None] = {
    OUTPUT_TYPE_POWER: SensorStateClass.MEASUREMENT,
    OUTPUT_TYPE_POWER_FLOW: SensorStateClass.MEASUREMENT,
    OUTPUT_TYPE_POWER_LIMIT: SensorStateClass.MEASUREMENT,
    OUTPUT_TYPE_SOC: SensorStateClass.MEASUREMENT,
    OUTPUT_TYPE_DURATION: SensorStateClass.MEASUREMENT,
}

STATUS_OPTIONS: tuple[str, ...] = tuple(
    sorted(  # Keep a stable order for enum options in Home Assistant UI
        {
            OPTIMIZATION_STATUS_FAILED,
            OPTIMIZATION_STATUS_PENDING,
            OPTIMIZATION_STATUS_SUCCESS,
        }
    )
)


def _build_coordinator_output(
    output_name: ElementOutputName,
    output_data: OutputData,
    *,
    forecast_times: tuple[float, ...] | None,
) -> CoordinatorOutput:
    """Convert model output values into coordinator state and forecast.

    This function handles the "fence post problem" where different output types require
    different numbers of timestamps:

    - **Interval values** (power, prices): Average values over time periods.
      These have n_periods values, each representing the average from the start
      of that period to its end. Use the first n_periods timestamps (fence posts).

    - **Boundary values** (energy, SOC): Instantaneous state at specific points in time.
      These have n_periods+1 values (one more than intervals) representing the state
      at each fence post. Use all n_periods+1 timestamps.

    The forecast_times tuple contains n_periods+1 timestamps (all fence posts).
    Each output type zips its values with however many timestamps it needs.

    Example with 3 periods of 300 seconds starting at t=0:
      - forecast_times: [0, 300, 600, 900] (n_periods+1 = 4 fence posts)
      - Interval values (n=3): zip with [0, 300, 600]
      - Boundary values (n=4): zip with [0, 300, 600, 900]
    """

    values = tuple(output_data.values)
    state: Any | None = values[0] if values else None
    forecast: list[ForecastPoint] | None = None

    if forecast_times and len(values) > 1:
        try:
            # Convert timestamps to localized datetime objects using HA's configured timezone
            local_tz = dt_util.get_default_time_zone()
            # Zip values with available timestamps - interval values use n_periods timestamps,
            # boundary values use all n_periods+1 timestamps (strict=False handles both)
            forecast = [
                ForecastPoint(time=datetime.fromtimestamp(timestamp, tz=local_tz), value=value)
                for timestamp, value in zip(forecast_times, values, strict=False)
            ]
        except ValueError:
            forecast = None

    return CoordinatorOutput(
        type=output_data.type,
        unit=output_data.unit,
        state=state,
        forecast=forecast,
        direction=output_data.direction,
        entity_category=(EntityCategory.DIAGNOSTIC if output_name == OUTPUT_NAME_OPTIMIZATION_DURATION else None),
        device_class=DEVICE_CLASS_MAP.get(output_data.type),
        state_class=STATE_CLASS_MAP.get(output_data.type),
        options=(STATUS_OPTIONS if output_data.type == OUTPUT_TYPE_STATUS else None),
        advanced=output_data.advanced,
    )


type SubentryDevices = dict[ElementDeviceName, dict[ElementOutputName | NetworkOutputName, CoordinatorOutput]]
type CoordinatorData = dict[str, SubentryDevices]


class HaeoDataUpdateCoordinator(DataUpdateCoordinator[CoordinatorData]):
    """Data update coordinator for HAEO integration."""

    # Refine config entry type to not be optional
    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the coordinator.

        Args:
            hass: Home Assistant instance
            config_entry: The hub config entry

        """
        # Runtime attributes exposed to other integration modules
        self.network: Network | None = None

        # Build participant configs and track subentry IDs
        self._participant_configs: dict[str, ElementConfigSchema] = {}
        self._participant_subentry_ids: dict[str, str] = {}  # element_name -> subentry_id

        for participant in collect_element_subentries(config_entry):
            self._participant_configs[participant.name] = participant.config
            self._participant_subentry_ids[participant.name] = participant.subentry.subentry_id

        debounce_seconds = float(config_entry.data.get(CONF_DEBOUNCE_SECONDS, DEFAULT_DEBOUNCE_SECONDS))
        update_interval_minutes = config_entry.data.get(CONF_UPDATE_INTERVAL_MINUTES, DEFAULT_UPDATE_INTERVAL_MINUTES)

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{config_entry.entry_id}",
            update_interval=timedelta(minutes=update_interval_minutes),
            config_entry=config_entry,
            request_refresh_debouncer=Debouncer(hass, _LOGGER, cooldown=debounce_seconds, immediate=True),
            always_update=False,
        )

        # Set up state tracking for all source entities
        self._state_change_unsub: Callable[[], None] | None = None
        all_entity_ids: set[str] = set()
        for config in self._participant_configs.values():
            all_entity_ids.update(extract_entity_ids_from_config(config))

        if all_entity_ids:
            self._state_change_unsub = async_track_state_change_event(
                self.hass,
                list(all_entity_ids),
                self._state_change_handler,
            )

    async def _state_change_handler(self, _event: Any) -> None:
        """Handle state change events for monitored entities."""
        await self.async_request_refresh()

    def cleanup(self) -> None:
        """Clean up coordinator resources when unloading."""

        if self._state_change_unsub is not None:
            self._state_change_unsub()
            self._state_change_unsub = None

    async def _async_update_data(self) -> CoordinatorData:
        """Update data from Home Assistant entities and run optimization."""
        start_time = time.time()

        # Convert tier configuration to list of period durations in seconds
        periods_seconds = tiers_to_periods_seconds(self.config_entry.data)
        forecast_timestamps = generate_forecast_timestamps(periods_seconds)

        # Check sensor availability before loading
        missing_sensors: list[str] = []
        for name, element_config in self._participant_configs.items():
            if not data_module.config_available(
                element_config,
                hass=self.hass,
                forecast_times=list(forecast_timestamps),
            ):
                missing_sensors.append(name)

        if missing_sensors:
            raise UpdateFailed(
                translation_key="missing_sensors",
                translation_placeholders={"unavailable_sensors": ", ".join(missing_sensors)},
            )

        # Load element configurations from source sensors
        loaded_configs = await data_module.load_element_configs(
            self.hass,
            self._participant_configs,
            forecast_timestamps,
        )

        # Build network with loaded configurations
        network = await data_module.load_network(
            self.config_entry,
            periods_seconds=periods_seconds,
            participants=loaded_configs,
        )

        # Perform the optimization
        cost = await self.hass.async_add_executor_job(network.optimize)

        end_time = time.time()
        optimization_duration = end_time - start_time

        _LOGGER.debug("Optimization completed successfully with cost: %s", cost)
        dismiss_optimization_failure_issue(self.hass, self.config_entry.entry_id)

        # Persist runtime state for diagnostics and system health
        self.network = network

        network_output_data: dict[NetworkOutputName, OutputData] = {
            OUTPUT_NAME_OPTIMIZATION_COST: OutputData(OUTPUT_TYPE_COST, unit=self.hass.config.currency, values=(cost,)),
            OUTPUT_NAME_OPTIMIZATION_STATUS: OutputData(
                OUTPUT_TYPE_STATUS, unit=None, values=(OPTIMIZATION_STATUS_SUCCESS,)
            ),
            OUTPUT_NAME_OPTIMIZATION_DURATION: OutputData(
                OUTPUT_TYPE_DURATION, unit=UnitOfTime.SECONDS, values=(optimization_duration,)
            ),
        }

        # Load the network subentry name from translations
        translations = await async_get_translations(
            self.hass, self.hass.config.language, "common", integrations=[DOMAIN]
        )
        network_subentry_name = translations[f"component.{DOMAIN}.common.network_subentry_name"]

        result: CoordinatorData = {
            # HAEO outputs use network subentry name as key, network element type as device
            network_subentry_name: {
                ELEMENT_TYPE_NETWORK: {
                    name: _build_coordinator_output(name, output, forecast_times=None)
                    for name, output in network_output_data.items()
                }
            }
        }

        # Build nested outputs structure from all network model elements
        model_outputs: dict[str, Mapping[ModelOutputName, OutputData]] = {
            element_name: element.outputs() for element_name, element in network.elements.items()
        }

        # Process each config element using its outputs function to transform model outputs into device outputs
        for element_name, element_config in self._participant_configs.items():
            element_type = element_config["element_type"]
            outputs_fn = ELEMENT_TYPES[element_type].outputs

            # outputs function returns {device_name: {output_name: OutputData}}
            # May return multiple devices per config element (e.g., battery regions)
            try:
                adapter_outputs: Mapping[ElementDeviceName, Mapping[Any, OutputData]] = outputs_fn(
                    element_name, model_outputs, loaded_configs[element_name]
                )
            except KeyError:
                _LOGGER.exception(
                    "Failed to get outputs for config element %r (type=%r): missing model element. "
                    "Available model elements: %s",
                    element_name,
                    element_type,
                    list(model_outputs.keys()),
                )
                raise

            # Process each device's outputs, grouping under the subentry (element_name)
            subentry_devices: SubentryDevices = {}
            for device_name, device_outputs in adapter_outputs.items():
                processed_outputs: dict[ElementOutputName, CoordinatorOutput] = {
                    output_name: _build_coordinator_output(
                        output_name,
                        output_data,
                        forecast_times=forecast_timestamps,
                    )
                    for output_name, output_data in device_outputs.items()
                }

                if processed_outputs:
                    subentry_devices[device_name] = processed_outputs

            if subentry_devices:
                result[element_name] = subentry_devices

        return result
