"""Load element adapter for model layer integration."""

from collections.abc import Mapping, Sequence
from dataclasses import replace
from typing import Any, Final, Literal

from homeassistant.core import HomeAssistant
import numpy as np

from custom_components.haeo.const import ConnectivityLevel
from custom_components.haeo.data.loader import TimeSeriesLoader
from custom_components.haeo.model import ModelElementConfig, ModelOutputName, ModelOutputValue
from custom_components.haeo.model.const import OutputType
from custom_components.haeo.model.elements import MODEL_ELEMENT_TYPE_CONNECTION, MODEL_ELEMENT_TYPE_NODE, SegmentSpec
from custom_components.haeo.model.elements.connection import CONNECTION_POWER_TARGET_SOURCE, CONNECTION_SEGMENTS
from custom_components.haeo.model.elements.segments import POWER_LIMIT_TARGET_SOURCE, PowerLimitSegmentSpec
from custom_components.haeo.model.output_data import OutputData

from .flow import LoadSubentryFlowHandler
from .schema import CONF_CONNECTION, CONF_FORECAST, ELEMENT_TYPE, LoadConfigData, LoadConfigSchema

# Load output names
type LoadOutputName = Literal[
    "load_power",
    "load_forecast_limit_price",
]

LOAD_OUTPUT_NAMES: Final[frozenset[LoadOutputName]] = frozenset(
    (
        LOAD_POWER := "load_power",
        # Shadow price
        LOAD_FORECAST_LIMIT_PRICE := "load_forecast_limit_price",
    )
)

type LoadDeviceName = Literal["load"]

LOAD_DEVICE_NAMES: Final[frozenset[LoadDeviceName]] = frozenset(
    (LOAD_DEVICE_LOAD := "load",),
)


class LoadAdapter:
    """Adapter for Load elements."""

    element_type: str = ELEMENT_TYPE
    flow_class: type = LoadSubentryFlowHandler
    advanced: bool = False
    connectivity: ConnectivityLevel = ConnectivityLevel.ADVANCED

    def available(self, config: LoadConfigSchema, *, hass: HomeAssistant, **_kwargs: Any) -> bool:
        """Check if load configuration can be loaded."""
        ts_loader = TimeSeriesLoader()
        return ts_loader.available(hass=hass, value=config[CONF_FORECAST])

    def build_config_data(
        self,
        loaded_values: Mapping[str, Any],
        config: LoadConfigSchema,
    ) -> LoadConfigData:
        """Build ConfigData from pre-loaded values.

        This is the single source of truth for ConfigData construction.
        Both load() and the coordinator use this method.

        Args:
            loaded_values: Dict of field names to loaded values (from input entities or TimeSeriesLoader)
            config: Original ConfigSchema for non-input fields (element_type, name, connection)

        Returns:
            LoadConfigData with all fields populated

        """
        return {
            "element_type": config["element_type"],
            "name": config["name"],
            "connection": config[CONF_CONNECTION],
            "forecast": list(loaded_values[CONF_FORECAST]),
        }

    async def load(
        self,
        config: LoadConfigSchema,
        *,
        hass: HomeAssistant,
        forecast_times: Sequence[float],
    ) -> LoadConfigData:
        """Load load configuration values from sensors.

        Uses TimeSeriesLoader to load values, then delegates to build_config_data().
        """
        ts_loader = TimeSeriesLoader()
        loaded_values: dict[str, list[float]] = {}

        loaded_values[CONF_FORECAST] = await ts_loader.load_intervals(
            hass=hass, value=config[CONF_FORECAST], forecast_times=forecast_times
        )

        return self.build_config_data(loaded_values, config)

    def model_elements(self, config: LoadConfigData) -> list[ModelElementConfig]:
        """Create model elements for Load configuration."""
        n_periods = len(config["forecast"])
        power_limit: PowerLimitSegmentSpec = {
            "segment_type": "power_limit",
            "max_power_source_target": np.zeros(n_periods),
            "max_power_target_source": np.array(config["forecast"]),
            "fixed": True,
        }
        segments: dict[str, SegmentSpec] = {"power_limit": power_limit}

        return [
            # Create Node for the load (sink only - consumes power)
            {"element_type": MODEL_ELEMENT_TYPE_NODE, "name": config["name"], "is_source": False, "is_sink": True},
            # Create Connection from node to load (power flows TO the load)
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": f"{config['name']}:connection",
                "source": config["name"],
                "target": config["connection"],
                "segments": segments,
            },
        ]

    def outputs(
        self,
        name: str,
        model_outputs: Mapping[str, Mapping[ModelOutputName, ModelOutputValue]],
        **_kwargs: Any,
    ) -> Mapping[LoadDeviceName, Mapping[LoadOutputName, OutputData]]:
        """Map model outputs to load-specific output names."""
        connection = model_outputs[f"{name}:connection"]

        power_target_source = connection[CONNECTION_POWER_TARGET_SOURCE]
        if not isinstance(power_target_source, OutputData):
            msg = f"Expected OutputData for {name!r} {CONNECTION_POWER_TARGET_SOURCE}"
            raise TypeError(msg)
        load_outputs: dict[LoadOutputName, OutputData] = {
            LOAD_POWER: replace(power_target_source, type=OutputType.POWER),
        }

        # Shadow price from power_limit segment (if present)
        segments_output = connection.get(CONNECTION_SEGMENTS)
        if isinstance(segments_output, Mapping):
            power_limit_outputs = segments_output.get("power_limit")
            if isinstance(power_limit_outputs, Mapping):
                shadow = power_limit_outputs.get(POWER_LIMIT_TARGET_SOURCE)
                if isinstance(shadow, OutputData):
                    load_outputs[LOAD_FORECAST_LIMIT_PRICE] = shadow

        return {LOAD_DEVICE_LOAD: load_outputs}


adapter = LoadAdapter()
