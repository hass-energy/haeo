"""Grid element adapter for model layer integration."""

from collections.abc import Mapping, Sequence
from dataclasses import replace
from typing import Any, Final, Literal

from homeassistant.core import HomeAssistant
import numpy as np

from custom_components.haeo.const import ConnectivityLevel
from custom_components.haeo.data.loader import TimeSeriesLoader
from custom_components.haeo.model import ModelElementConfig, ModelOutputName, ModelOutputValue
from custom_components.haeo.model.const import OutputType
from custom_components.haeo.model.elements import MODEL_ELEMENT_TYPE_CONNECTION, MODEL_ELEMENT_TYPE_NODE
from custom_components.haeo.model.elements.connection import (
    CONNECTION_POWER_SOURCE_TARGET,
    CONNECTION_POWER_TARGET_SOURCE,
    CONNECTION_SEGMENTS,
)
from custom_components.haeo.model.elements.segments import POWER_LIMIT_SOURCE_TARGET, POWER_LIMIT_TARGET_SOURCE
from custom_components.haeo.model.output_data import OutputData

from .flow import GridSubentryFlowHandler
from .schema import CONF_CONNECTION, ELEMENT_TYPE, GridConfigData, GridConfigSchema

# Grid-specific output names for translation/sensor mapping
type GridOutputName = Literal[
    "grid_power_import",
    "grid_power_export",
    "grid_power_active",
    "grid_cost_import",
    "grid_revenue_export",
    "grid_cost_net",
    "grid_power_max_import_price",
    "grid_power_max_export_price",
]

GRID_OUTPUT_NAMES: Final[frozenset[GridOutputName]] = frozenset(
    (
        GRID_POWER_IMPORT := "grid_power_import",
        GRID_POWER_EXPORT := "grid_power_export",
        GRID_POWER_ACTIVE := "grid_power_active",
        # Cost/revenue outputs
        GRID_COST_IMPORT := "grid_cost_import",
        GRID_REVENUE_EXPORT := "grid_revenue_export",
        GRID_COST_NET := "grid_cost_net",
        # Shadow prices
        GRID_POWER_MAX_IMPORT_PRICE := "grid_power_max_import_price",
        GRID_POWER_MAX_EXPORT_PRICE := "grid_power_max_export_price",
    )
)

type GridDeviceName = Literal["grid"]

GRID_DEVICE_NAMES: Final[frozenset[GridDeviceName]] = frozenset(
    (GRID_DEVICE_GRID := "grid",),
)


class GridAdapter:
    """Adapter for Grid elements."""

    element_type: str = ELEMENT_TYPE
    flow_class: type = GridSubentryFlowHandler
    advanced: bool = False
    connectivity: ConnectivityLevel = ConnectivityLevel.ADVANCED

    def available(self, config: GridConfigSchema, *, hass: HomeAssistant, **_kwargs: Any) -> bool:
        """Check if grid configuration can be loaded."""
        ts_loader = TimeSeriesLoader()

        # Helper to check entity availability
        def entities_available(value: list[str] | str | float | None) -> bool:
            if value is None or isinstance(value, float | int):
                return True  # Constants and missing values are always available
            if isinstance(value, str):
                return ts_loader.available(hass=hass, value=[value])
            # At this point value is a list of strings
            return ts_loader.available(hass=hass, value=value) if value else True

        return entities_available(config.get("import_price")) and entities_available(config.get("export_price"))

    def build_config_data(
        self,
        loaded_values: Mapping[str, Any],
        config: GridConfigSchema,
    ) -> GridConfigData:
        """Build ConfigData from pre-loaded values.

        This is the single source of truth for ConfigData construction.
        Both load() and the coordinator use this method.

        Args:
            loaded_values: Dict of field names to loaded values (from input entities or TimeSeriesLoader)
            config: Original ConfigSchema for non-input fields (element_type, name, connection)

        Returns:
            GridConfigData with all fields populated and defaults applied

        """
        # Build data with required fields (prices must be present in loaded_values)
        data: GridConfigData = {
            "element_type": config["element_type"],
            "name": config["name"],
            "connection": config[CONF_CONNECTION],
            "import_price": list(loaded_values["import_price"]),
            "export_price": list(loaded_values["export_price"]),
        }

        # Optional limit fields - only include if present
        if "import_limit" in loaded_values:
            data["import_limit"] = list(loaded_values["import_limit"])

        if "export_limit" in loaded_values:
            data["export_limit"] = list(loaded_values["export_limit"])

        return data

    async def load(
        self,
        config: GridConfigSchema,
        *,
        hass: HomeAssistant,
        forecast_times: Sequence[float],
    ) -> GridConfigData:
        """Load grid configuration values from sensors.

        Uses TimeSeriesLoader to load values, then delegates to build_config_data().
        """
        ts_loader = TimeSeriesLoader()
        n_periods = max(0, len(forecast_times) - 1)
        loaded_values: dict[str, list[float]] = {}

        # Load import_price: entity ID, entity list, or constant (required field)
        import_value = config["import_price"]
        if isinstance(import_value, list):
            loaded_values["import_price"] = await ts_loader.load_intervals(
                hass=hass, value=import_value, forecast_times=forecast_times
            )
        elif isinstance(import_value, str):
            loaded_values["import_price"] = await ts_loader.load_intervals(
                hass=hass, value=[import_value], forecast_times=forecast_times
            )
        else:
            loaded_values["import_price"] = [float(import_value)] * n_periods

        # Load export_price: entity ID, entity list, or constant (required field)
        export_value = config["export_price"]
        if isinstance(export_value, list):
            loaded_values["export_price"] = await ts_loader.load_intervals(
                hass=hass, value=export_value, forecast_times=forecast_times
            )
        elif isinstance(export_value, str):
            loaded_values["export_price"] = await ts_loader.load_intervals(
                hass=hass, value=[export_value], forecast_times=forecast_times
            )
        else:
            loaded_values["export_price"] = [float(export_value)] * n_periods

        # Load optional limit fields
        import_limit = config.get("import_limit")
        if import_limit is not None:
            if isinstance(import_limit, list) and import_limit:
                loaded_values["import_limit"] = await ts_loader.load_intervals(
                    hass=hass, value=import_limit, forecast_times=forecast_times
                )
            elif isinstance(import_limit, str):
                loaded_values["import_limit"] = await ts_loader.load_intervals(
                    hass=hass, value=[import_limit], forecast_times=forecast_times
                )
            else:
                loaded_values["import_limit"] = [float(import_limit)] * n_periods

        export_limit = config.get("export_limit")
        if export_limit is not None:
            if isinstance(export_limit, list) and export_limit:
                loaded_values["export_limit"] = await ts_loader.load_intervals(
                    hass=hass, value=export_limit, forecast_times=forecast_times
                )
            elif isinstance(export_limit, str):
                loaded_values["export_limit"] = await ts_loader.load_intervals(
                    hass=hass, value=[export_limit], forecast_times=forecast_times
                )
            else:
                loaded_values["export_limit"] = [float(export_limit)] * n_periods

        return self.build_config_data(loaded_values, config)

    def model_elements(self, config: GridConfigData) -> list[ModelElementConfig]:
        """Create model elements for Grid configuration."""
        import_limit = config.get("import_limit")
        export_limit = config.get("export_limit")
        return [
            # Create Node for the grid (both source and sink - can import and export)
            {
                "element_type": MODEL_ELEMENT_TYPE_NODE,
                "name": config["name"],
                "is_source": True,
                "is_sink": True,
            },
            # Create a connection from system node to grid
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": f"{config['name']}:connection",
                "source": config["name"],
                "target": config["connection"],
                "segments": {
                    "power_limit": {
                        "segment_type": "power_limit",
                        "max_power_source_target": np.array(import_limit) if import_limit is not None else None,
                        "max_power_target_source": np.array(export_limit) if export_limit is not None else None,
                    },
                    "pricing": {
                        "segment_type": "pricing",
                        "price_source_target": np.array(config["import_price"]),
                        "price_target_source": np.array([-p for p in config["export_price"]]),
                    },
                },
            },
        ]

    def outputs(
        self,
        name: str,
        model_outputs: Mapping[str, Mapping[ModelOutputName, ModelOutputValue]],
        *,
        config: GridConfigData,
        periods: Sequence[float],
        **_kwargs: Any,
    ) -> Mapping[GridDeviceName, Mapping[GridOutputName, OutputData]]:
        """Map model outputs to grid-specific output names."""
        connection = model_outputs[f"{name}:connection"]

        grid_outputs: dict[GridOutputName, OutputData] = {}

        # source_target = grid to system = IMPORT
        # target_source = system to grid = EXPORT
        power_import = connection[CONNECTION_POWER_SOURCE_TARGET]
        power_export = connection[CONNECTION_POWER_TARGET_SOURCE]
        if not isinstance(power_import, OutputData):
            msg = f"Expected OutputData for {name!r} {CONNECTION_POWER_SOURCE_TARGET}"
            raise TypeError(msg)
        if not isinstance(power_export, OutputData):
            msg = f"Expected OutputData for {name!r} {CONNECTION_POWER_TARGET_SOURCE}"
            raise TypeError(msg)

        grid_outputs[GRID_POWER_EXPORT] = replace(power_export, type=OutputType.POWER)
        grid_outputs[GRID_POWER_IMPORT] = replace(power_import, type=OutputType.POWER)

        # Active grid power (export - import)
        grid_outputs[GRID_POWER_ACTIVE] = replace(
            power_export,
            values=[i - e for i, e in zip(power_import.values, power_export.values, strict=True)],
            direction=None,
            type=OutputType.POWER,
        )

        # Calculate cost outputs in adapter layer: cost = power * price * period
        # This is a derived calculation, not from model layer outputs
        import_prices = config["import_price"]
        export_prices = config["export_price"]

        # Import cost: positive = money spent (power from grid * price * period)
        import_cost_values = tuple(
            power * price * period
            for power, price, period in zip(power_import.values, import_prices, periods, strict=True)
        )
        import_cumsum = tuple(np.cumsum(import_cost_values))
        grid_outputs[GRID_COST_IMPORT] = OutputData(
            type=OutputType.COST, unit="$", values=import_cumsum, direction="-", state_last=True
        )

        # Export revenue: positive = money earned (power to grid * price * period)
        export_revenue_values = tuple(
            power * price * period
            for power, price, period in zip(power_export.values, export_prices, periods, strict=True)
        )
        export_cumsum = tuple(np.cumsum(export_revenue_values))
        grid_outputs[GRID_REVENUE_EXPORT] = OutputData(
            type=OutputType.COST, unit="$", values=export_cumsum, direction="+", state_last=True
        )

        # Net cost = import cost - export revenue (positive = net spending, negative = net earning)
        net_cost_values = tuple(ic - er for ic, er in zip(import_cost_values, export_revenue_values, strict=True))
        net_cumsum = tuple(np.cumsum(net_cost_values))
        grid_outputs[GRID_COST_NET] = OutputData(
            type=OutputType.COST, unit="$", values=net_cumsum, direction=None, state_last=True
        )

        # Output the shadow prices from power_limit segment
        segments_output = connection.get(CONNECTION_SEGMENTS)
        if isinstance(segments_output, Mapping):
            power_limit_outputs = segments_output.get("power_limit")
            if isinstance(power_limit_outputs, Mapping):
                export_shadow = power_limit_outputs.get(POWER_LIMIT_TARGET_SOURCE)
                if isinstance(export_shadow, OutputData):
                    grid_outputs[GRID_POWER_MAX_EXPORT_PRICE] = export_shadow
                import_shadow = power_limit_outputs.get(POWER_LIMIT_SOURCE_TARGET)
                if isinstance(import_shadow, OutputData):
                    grid_outputs[GRID_POWER_MAX_IMPORT_PRICE] = import_shadow

        return {GRID_DEVICE_GRID: grid_outputs}


adapter = GridAdapter()
