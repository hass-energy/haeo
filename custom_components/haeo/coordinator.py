"""Data update coordinator for the Home Assistant Energy Optimization integration."""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
import time
from typing import Any, get_type_hints

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.debounce import Debouncer
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util
from homeassistant.util import slugify

from . import data as data_module
from .const import (
    CONF_DEBOUNCE_SECONDS,
    CONF_HORIZON_HOURS,
    CONF_PERIOD_MINUTES,
    CONF_UPDATE_INTERVAL_MINUTES,
    DEFAULT_DEBOUNCE_SECONDS,
    DEFAULT_UPDATE_INTERVAL_MINUTES,
    DOMAIN,
    OPTIMIZATION_STATUS_FAILED,
    OPTIMIZATION_STATUS_PENDING,
    OPTIMIZATION_STATUS_SUCCESS,
)
from .elements import ELEMENT_TYPES, ElementConfigSchema, collect_element_subentries
from .model import (
    OUTPUT_NAME_OPTIMIZATION_COST,
    OUTPUT_NAME_OPTIMIZATION_DURATION,
    OUTPUT_NAME_OPTIMIZATION_STATUS,
    OUTPUT_TYPE_COST,
    OUTPUT_TYPE_DURATION,
    OUTPUT_TYPE_ENERGY,
    OUTPUT_TYPE_POWER,
    OUTPUT_TYPE_PRICE,
    OUTPUT_TYPE_SHADOW_PRICE,
    OUTPUT_TYPE_SOC,
    OUTPUT_TYPE_STATUS,
    Network,
    OutputData,
    OutputName,
    OutputType,
)
from .repairs import dismiss_optimization_failure_issue
from .schema import get_field_meta

_LOGGER = logging.getLogger(__name__)


def _collect_entity_ids(value: Any) -> set[str]:
    """Recursively collect entity IDs from nested configuration values."""

    if isinstance(value, str):
        return {value}

    if isinstance(value, Mapping):
        mapping_ids: set[str] = set()
        for nested in value.values():
            mapping_ids.update(_collect_entity_ids(nested))
        return mapping_ids

    if isinstance(value, Sequence):
        sequence_ids: set[str] = set()
        for nested in value:
            sequence_ids.update(_collect_entity_ids(nested))
        return sequence_ids

    return set()


def _extract_entity_ids_from_config(config: ElementConfigSchema) -> set[str]:
    """Extract entity IDs from a configuration using schema loaders."""
    entity_ids: set[str] = set()

    element_type = config["element_type"]
    data_config_class = ELEMENT_TYPES[element_type].data
    hints = get_type_hints(data_config_class, include_extras=True)

    for field_name in hints:
        # Skip metadata fields
        if field_name in ("element_type", "name"):
            continue

        field_value = config.get(field_name)
        if field_value is None:
            continue

        field_meta = get_field_meta(field_name, data_config_class)
        if field_meta is None:
            continue

        # Check if this is a constant field (not a sensor)
        if field_meta.field_type == "constant":
            continue

        try:
            entity_ids.update(_collect_entity_ids(field_value))
        except TypeError:
            continue

    return entity_ids


@dataclass(frozen=True, slots=True)
class CoordinatorOutput:
    """Processed output ready for Home Assistant entities."""

    type: OutputType
    unit: str | None
    state: StateType | None
    forecast: dict[datetime, Any] | None
    entity_category: EntityCategory | None = None
    device_class: SensorDeviceClass | None = None
    state_class: SensorStateClass | None = None
    options: tuple[str, ...] | None = None


DEVICE_CLASS_MAP: dict[OutputType, SensorDeviceClass] = {
    OUTPUT_TYPE_POWER: SensorDeviceClass.POWER,
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
    output_name: OutputName,
    output_data: OutputData,
    *,
    forecast_times: tuple[int, ...] | None,
) -> CoordinatorOutput:
    """Convert model output values into coordinator state and forecast."""

    values = tuple(output_data.values)
    state: Any | None = values[0] if values else None
    forecast: dict[datetime, Any] | None = None
    aligned_times: tuple[int, ...] | None = None

    if forecast_times and len(values) > 1:
        if len(values) == len(forecast_times):
            aligned_times = forecast_times
        elif len(values) == len(forecast_times) - 1:
            aligned_times = forecast_times[1:]

    if aligned_times:
        try:
            # Convert timestamps to localized datetime objects using HA's configured timezone
            local_tz = dt_util.get_default_time_zone()
            forecast = {
                datetime.fromtimestamp(timestamp, tz=local_tz): value
                for timestamp, value in zip(aligned_times, values, strict=True)
            }
        except ValueError:
            forecast = None

    return CoordinatorOutput(
        type=output_data.type,
        unit=output_data.unit,
        state=state,
        forecast=forecast,
        entity_category=(EntityCategory.DIAGNOSTIC if output_name == OUTPUT_NAME_OPTIMIZATION_DURATION else None),
        device_class=DEVICE_CLASS_MAP.get(output_data.type),
        state_class=STATE_CLASS_MAP.get(output_data.type),
        options=(STATUS_OPTIONS if output_data.type == OUTPUT_TYPE_STATUS else None),
    )


type CoordinatorData = dict[str, dict[OutputName, CoordinatorOutput]]


class HaeoDataUpdateCoordinator(DataUpdateCoordinator[CoordinatorData]):
    """Data update coordinator for HAEO integration."""

    # Refine config entry type to not be optional
    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the coordinator."""

        # Runtime attributes exposed to other integration modules
        self.network: Network | None = None

        self._participant_configs: dict[str, ElementConfigSchema] = {
            slugify(participant.name): participant.config for participant in collect_element_subentries(config_entry)
        }

        self._state_change_unsub: Callable[[], None] | None = None

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

        # Extract entity IDs from all participant configurations
        all_entity_ids: set[str] = set()
        for config in self._participant_configs.values():
            all_entity_ids.update(_extract_entity_ids_from_config(config))

        # Set up state change listeners for all entity IDs in configuration
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

    @staticmethod
    def _generate_forecast_timestamps(*, period_seconds: int, n_periods: int) -> tuple[int, ...]:
        """Return rounded forecast timestamps for the optimization horizon."""

        epoch_seconds = dt_util.utcnow().timestamp()
        rounded_epoch = int(epoch_seconds // period_seconds * period_seconds)
        origin_time = dt_util.utc_from_timestamp(rounded_epoch)

        return tuple(
            int((origin_time + timedelta(seconds=period_seconds * index)).timestamp()) for index in range(n_periods)
        )

    async def _async_update_data(self) -> CoordinatorData:
        """Update data from Home Assistant entities and run optimization."""
        start_time = time.time()

        # Convert the time parameters from seconds and hours to seconds and a number of periods
        period_seconds = self.config_entry.data[CONF_PERIOD_MINUTES] * 60  # Convert minutes to seconds
        horizon_seconds = self.config_entry.data[CONF_HORIZON_HOURS] * 3600  # Convert hours to seconds
        n_periods = horizon_seconds // period_seconds
        forecast_timestamps = self._generate_forecast_timestamps(
            period_seconds=period_seconds,
            n_periods=n_periods,
        )

        # Try to load the data into a network object
        network = await data_module.load_network(
            self.hass,
            self.config_entry,
            period_seconds=period_seconds,
            n_periods=n_periods,
            participants=self._participant_configs,
            forecast_times=forecast_timestamps,
        )

        # Perform the optimization
        cost = await self.hass.async_add_executor_job(network.optimize)

        end_time = time.time()
        optimization_duration = end_time - start_time

        _LOGGER.debug("Optimization completed successfully with cost: %s", cost)
        dismiss_optimization_failure_issue(self.hass, self.config_entry.entry_id)

        # Persist runtime state for diagnostics and system health
        self.network = network

        network_output_data: dict[OutputName, OutputData] = {
            OUTPUT_NAME_OPTIMIZATION_COST: OutputData(OUTPUT_TYPE_COST, unit=self.hass.config.currency, values=(cost,)),
            OUTPUT_NAME_OPTIMIZATION_STATUS: OutputData(
                OUTPUT_TYPE_STATUS, unit=None, values=(OPTIMIZATION_STATUS_SUCCESS,)
            ),
            OUTPUT_NAME_OPTIMIZATION_DURATION: OutputData(
                OUTPUT_TYPE_DURATION, unit=UnitOfTime.SECONDS, values=(optimization_duration,)
            ),
        }

        # Return network outputs first, then element outputs
        result: CoordinatorData = {
            # We use the name of the hub config entry as the network element name
            slugify(self.config_entry.title): {
                name: _build_coordinator_output(name, output, forecast_times=None)
                for name, output in network_output_data.items()
            }
        }

        # Add element outputs from each network element keyed by element name
        for element_name, element in network.elements.items():
            element_outputs = element.get_outputs()
            if not element_outputs:
                continue

            processed_outputs: dict[OutputName, CoordinatorOutput] = {
                output_name: _build_coordinator_output(
                    output_name,
                    output_data,
                    forecast_times=forecast_timestamps,
                )
                for output_name, output_data in element_outputs.items()
            }

            if processed_outputs:
                result[slugify(element_name)] = processed_outputs

        return result
