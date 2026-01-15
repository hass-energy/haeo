"""Connection element adapter for model layer integration."""

from collections.abc import Mapping, Sequence
from dataclasses import replace
from typing import Any, Final, Literal

from homeassistant.core import HomeAssistant
import numpy as np

from custom_components.haeo.const import ConnectivityLevel
from custom_components.haeo.data.loader import TimeSeriesLoader
from custom_components.haeo.model import ModelElementConfig, ModelOutputName, ModelOutputValue
from custom_components.haeo.model.const import OutputType
from custom_components.haeo.model.elements import MODEL_ELEMENT_TYPE_CONNECTION, SegmentSpec
from custom_components.haeo.model.elements.connection import CONNECTION_OUTPUT_NAMES as MODEL_CONNECTION_OUTPUT_NAMES
from custom_components.haeo.model.elements.connection import (
    CONNECTION_POWER_SOURCE_TARGET,
    CONNECTION_POWER_TARGET_SOURCE,
    CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET,
    CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE,
    CONNECTION_TIME_SLICE,
)
from custom_components.haeo.model.elements.connection import ConnectionOutputName as ModelConnectionOutputName
from custom_components.haeo.model.elements.segments import (
    EfficiencySegmentSpec,
    PowerLimitSegmentSpec,
    PricingSegmentSpec,
)
from custom_components.haeo.model.output_data import OutputData, require_output_data

from .flow import ConnectionSubentryFlowHandler
from .schema import (
    CONF_EFFICIENCY_SOURCE_TARGET,
    CONF_EFFICIENCY_TARGET_SOURCE,
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_MAX_POWER_TARGET_SOURCE,
    CONF_PRICE_SOURCE_TARGET,
    CONF_PRICE_TARGET_SOURCE,
    CONF_SOURCE,
    CONF_TARGET,
    ELEMENT_TYPE,
    ConnectionConfigData,
    ConnectionConfigSchema,
)

# Adapter-synthesized output name (computed from model outputs)
CONNECTION_POWER_ACTIVE: Final = "connection_power_active"

# Connection adapter output names include model outputs + adapter-synthesized outputs
type ConnectionOutputName = (
    ModelConnectionOutputName
    | Literal[
        "connection_power_active",
        "connection_shadow_power_max_source_target",
        "connection_shadow_power_max_target_source",
        "connection_time_slice",
    ]
)

CONNECTION_OUTPUT_NAMES: Final[frozenset[ConnectionOutputName]] = frozenset(
    (
        *MODEL_CONNECTION_OUTPUT_NAMES,
        CONNECTION_POWER_ACTIVE,
        CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET,
        CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE,
        CONNECTION_TIME_SLICE,
    )
)

type ConnectionDeviceName = Literal["connection"]

CONNECTION_DEVICE_NAMES: Final[frozenset[ConnectionDeviceName]] = frozenset(
    (CONNECTION_DEVICE_CONNECTION := "connection",),
)


class ConnectionAdapter:
    """Adapter for Connection elements."""

    element_type: str = ELEMENT_TYPE
    flow_class: type = ConnectionSubentryFlowHandler
    advanced: bool = True
    connectivity: ConnectivityLevel = ConnectivityLevel.NEVER

    def available(self, config: ConnectionConfigSchema, *, hass: HomeAssistant, **_kwargs: Any) -> bool:
        """Check if connection configuration can be loaded."""
        ts_loader = TimeSeriesLoader()

        # Check all optional time series fields if present
        optional_fields = [
            CONF_MAX_POWER_SOURCE_TARGET,
            CONF_MAX_POWER_TARGET_SOURCE,
            CONF_EFFICIENCY_SOURCE_TARGET,
            CONF_EFFICIENCY_TARGET_SOURCE,
            CONF_PRICE_SOURCE_TARGET,
            CONF_PRICE_TARGET_SOURCE,
        ]

        for field in optional_fields:
            if field in config and not ts_loader.available(hass=hass, value=config[field]):
                return False

        return True

    def build_config_data(
        self,
        loaded_values: Mapping[str, Any],
        config: ConnectionConfigSchema,
    ) -> ConnectionConfigData:
        """Build ConfigData from pre-loaded values.

        This is the single source of truth for ConfigData construction.
        Both load() and the coordinator use this method.

        Args:
            loaded_values: Dict of field names to loaded values (from input entities or TimeSeriesLoader)
            config: Original ConfigSchema for non-input fields (element_type, name, source, target)

        Returns:
            ConnectionConfigData with all fields populated

        """
        data: ConnectionConfigData = {
            "element_type": config["element_type"],
            "name": config["name"],
            "source": config[CONF_SOURCE],
            "target": config[CONF_TARGET],
        }

        # Optional time series fields
        if CONF_MAX_POWER_SOURCE_TARGET in loaded_values:
            data["max_power_source_target"] = list(loaded_values[CONF_MAX_POWER_SOURCE_TARGET])
        if CONF_MAX_POWER_TARGET_SOURCE in loaded_values:
            data["max_power_target_source"] = list(loaded_values[CONF_MAX_POWER_TARGET_SOURCE])
        if CONF_EFFICIENCY_SOURCE_TARGET in loaded_values:
            data["efficiency_source_target"] = list(loaded_values[CONF_EFFICIENCY_SOURCE_TARGET])
        if CONF_EFFICIENCY_TARGET_SOURCE in loaded_values:
            data["efficiency_target_source"] = list(loaded_values[CONF_EFFICIENCY_TARGET_SOURCE])
        if CONF_PRICE_SOURCE_TARGET in loaded_values:
            data["price_source_target"] = list(loaded_values[CONF_PRICE_SOURCE_TARGET])
        if CONF_PRICE_TARGET_SOURCE in loaded_values:
            data["price_target_source"] = list(loaded_values[CONF_PRICE_TARGET_SOURCE])

        return data

    async def load(
        self,
        config: ConnectionConfigSchema,
        *,
        hass: HomeAssistant,
        forecast_times: Sequence[float],
    ) -> ConnectionConfigData:
        """Load connection configuration values from sensors.

        Uses TimeSeriesLoader to load values, then delegates to build_config_data().
        """
        ts_loader = TimeSeriesLoader()
        loaded_values: dict[str, list[float]] = {}

        # Load optional time series fields
        if CONF_MAX_POWER_SOURCE_TARGET in config:
            loaded_values[CONF_MAX_POWER_SOURCE_TARGET] = await ts_loader.load_intervals(
                hass=hass, value=config[CONF_MAX_POWER_SOURCE_TARGET], forecast_times=forecast_times
            )
        if CONF_MAX_POWER_TARGET_SOURCE in config:
            loaded_values[CONF_MAX_POWER_TARGET_SOURCE] = await ts_loader.load_intervals(
                hass=hass, value=config[CONF_MAX_POWER_TARGET_SOURCE], forecast_times=forecast_times
            )
        if CONF_EFFICIENCY_SOURCE_TARGET in config:
            loaded_values[CONF_EFFICIENCY_SOURCE_TARGET] = await ts_loader.load_intervals(
                hass=hass, value=config[CONF_EFFICIENCY_SOURCE_TARGET], forecast_times=forecast_times
            )
        if CONF_EFFICIENCY_TARGET_SOURCE in config:
            loaded_values[CONF_EFFICIENCY_TARGET_SOURCE] = await ts_loader.load_intervals(
                hass=hass, value=config[CONF_EFFICIENCY_TARGET_SOURCE], forecast_times=forecast_times
            )
        if CONF_PRICE_SOURCE_TARGET in config:
            loaded_values[CONF_PRICE_SOURCE_TARGET] = await ts_loader.load_intervals(
                hass=hass, value=config[CONF_PRICE_SOURCE_TARGET], forecast_times=forecast_times
            )
        if CONF_PRICE_TARGET_SOURCE in config:
            loaded_values[CONF_PRICE_TARGET_SOURCE] = await ts_loader.load_intervals(
                hass=hass, value=config[CONF_PRICE_TARGET_SOURCE], forecast_times=forecast_times
            )

        return self.build_config_data(loaded_values, config)

    def model_elements(self, config: ConnectionConfigData) -> list[ModelElementConfig]:
        """Return model element parameters for Connection configuration.

        Builds the segments list for the Connection model element based on
        which optional configuration fields are present.
        """
        segments: list[SegmentSpec] = []

        # Add efficiency segment if efficiency values are provided
        # Note: Segment uses efficiency_source_target/efficiency_target_source, values are fractions (0-1)
        efficiency_source_target = config.get("efficiency_source_target")
        efficiency_target_source = config.get("efficiency_target_source")
        if efficiency_source_target is not None or efficiency_target_source is not None:
            # Efficiency values from config are percentages, convert to fractions
            efficiency_spec: EfficiencySegmentSpec = {"segment_type": "efficiency"}
            if efficiency_source_target is not None:
                efficiency_spec["efficiency_source_target"] = np.array(efficiency_source_target) / 100.0
            if efficiency_target_source is not None:
                efficiency_spec["efficiency_target_source"] = np.array(efficiency_target_source) / 100.0
            segments.append(efficiency_spec)

        # Add power limit segment if power limits are provided
        max_power_source_target = config.get("max_power_source_target")
        max_power_target_source = config.get("max_power_target_source")
        if max_power_source_target is not None or max_power_target_source is not None:
            power_limit_spec: PowerLimitSegmentSpec = {"segment_type": "power_limit"}
            if max_power_source_target is not None:
                power_limit_spec["max_power_source_target"] = np.array(max_power_source_target)
            if max_power_target_source is not None:
                power_limit_spec["max_power_target_source"] = np.array(max_power_target_source)
            segments.append(power_limit_spec)

        # Add pricing segment if prices are provided
        price_source_target = config.get("price_source_target")
        price_target_source = config.get("price_target_source")
        if price_source_target is not None or price_target_source is not None:
            pricing_spec: PricingSegmentSpec = {"segment_type": "pricing"}
            if price_source_target is not None:
                pricing_spec["price_source_target"] = np.array(price_source_target)
            if price_target_source is not None:
                pricing_spec["price_target_source"] = np.array(price_target_source)
            segments.append(pricing_spec)

        element_data: ModelElementConfig = {
            "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
            "name": config["name"],
            "source": config["source"],
            "target": config["target"],
        }
        if segments:
            element_data["segments"] = segments

        return [element_data]

    def outputs(
        self,
        name: str,
        model_outputs: Mapping[str, Mapping[ModelOutputName, ModelOutputValue]],
        **_kwargs: Any,
    ) -> Mapping[ConnectionDeviceName, Mapping[ConnectionOutputName, OutputData]]:
        """Map model outputs to connection-specific output names."""
        connection = model_outputs[name]
        power_source_target = require_output_data(connection[CONNECTION_POWER_SOURCE_TARGET])
        power_target_source = require_output_data(connection[CONNECTION_POWER_TARGET_SOURCE])

        connection_outputs: dict[ConnectionOutputName, OutputData] = {
            CONNECTION_POWER_SOURCE_TARGET: power_source_target,
            CONNECTION_POWER_TARGET_SOURCE: power_target_source,
        }

        # Active connection power (source_target - target_source)
        connection_outputs[CONNECTION_POWER_ACTIVE] = replace(
            power_source_target,
            values=[
                st - ts
                for st, ts in zip(
                    power_source_target.values,
                    power_target_source.values,
                    strict=True,
                )
            ],
            direction=None,
            type=OutputType.POWER_FLOW,
        )

        # Include legacy shadow prices if present
        if CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET in connection:
            connection_outputs[CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET] = require_output_data(
                connection[CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET]
            )
        if CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE in connection:
            connection_outputs[CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE] = require_output_data(
                connection[CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE]
            )
        if CONNECTION_TIME_SLICE in connection:
            connection_outputs[CONNECTION_TIME_SLICE] = require_output_data(connection[CONNECTION_TIME_SLICE])

        # Note: Segment shadow prices are exposed under the model's `segments` output
        # map. Specific adapters (grid, solar, etc.) map these to their own outputs.

        return {CONNECTION_DEVICE_CONNECTION: connection_outputs}


adapter = ConnectionAdapter()
