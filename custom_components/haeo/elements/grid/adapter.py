"""Grid element adapter for model layer integration."""

from collections.abc import Mapping, Sequence
from dataclasses import replace
from typing import Any, Final, Literal

from homeassistant.core import HomeAssistant

from custom_components.haeo.const import ConnectivityLevel
from custom_components.haeo.data.loader import ConstantLoader, TimeSeriesLoader
from custom_components.haeo.model import ModelOutputName
from custom_components.haeo.model.const import OUTPUT_TYPE_POWER
from custom_components.haeo.model.output_data import OutputData
from custom_components.haeo.model.power_connection import (
    CONNECTION_POWER_SOURCE_TARGET,
    CONNECTION_POWER_TARGET_SOURCE,
    CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET,
    CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE,
)

from .flow import GridSubentryFlowHandler
from .schema import (
    CONF_CONNECTION,
    DEFAULT_EXPORT_PRICE,
    DEFAULT_IMPORT_PRICE,
    ELEMENT_TYPE,
    GridConfigData,
    GridConfigSchema,
)

# Grid-specific output names for translation/sensor mapping
type GridOutputName = Literal[
    "grid_power_import",
    "grid_power_export",
    "grid_power_active",
    "grid_power_max_import_price",
    "grid_power_max_export_price",
]

GRID_OUTPUT_NAMES: Final[frozenset[GridOutputName]] = frozenset(
    (
        GRID_POWER_IMPORT := "grid_power_import",
        GRID_POWER_EXPORT := "grid_power_export",
        GRID_POWER_ACTIVE := "grid_power_active",
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

        # Empty price lists are valid - uses default prices from schema
        import_available = not config["import_price"] or ts_loader.available(hass=hass, value=config["import_price"])
        export_available = not config["export_price"] or ts_loader.available(hass=hass, value=config["export_price"])
        return import_available and export_available

    async def load(
        self,
        config: GridConfigSchema,
        *,
        hass: HomeAssistant,
        forecast_times: Sequence[float],
    ) -> GridConfigData:
        """Load grid configuration values from sensors."""
        ts_loader = TimeSeriesLoader()
        const_loader = ConstantLoader[float](float)

        # Use default prices from schema when no sensors are configured
        if not config["import_price"]:
            import_price = [DEFAULT_IMPORT_PRICE for _ in forecast_times]
        else:
            import_price = await ts_loader.load(
                hass=hass,
                value=config["import_price"],
                forecast_times=forecast_times,
            )

        if not config["export_price"]:
            export_price = [DEFAULT_EXPORT_PRICE for _ in forecast_times]
        else:
            export_price = await ts_loader.load(
                hass=hass,
                value=config["export_price"],
                forecast_times=forecast_times,
            )

        data: GridConfigData = {
            "element_type": config["element_type"],
            "name": config["name"],
            "connection": config[CONF_CONNECTION],
            "import_price": import_price,
            "export_price": export_price,
        }

        # Load optional fields
        if "import_limit" in config:
            data["import_limit"] = await const_loader.load(value=config["import_limit"])
        if "export_limit" in config:
            data["export_limit"] = await const_loader.load(value=config["export_limit"])

        return data

    def create_model_elements(self, config: GridConfigData) -> list[dict[str, Any]]:
        """Create model elements for Grid configuration."""
        return [
            # Create Node for the grid (both source and sink - can import and export)
            {"element_type": "node", "name": config["name"], "is_source": True, "is_sink": True},
            # Create a connection from system node to grid
            {
                "element_type": "connection",
                "name": f"{config['name']}:connection",
                "source": config["name"],
                "target": config["connection"],
                "max_power_source_target": config.get("import_limit"),  # source_target is grid to system (IMPORT)
                "max_power_target_source": config.get("export_limit"),  # target_source is system to grid (EXPORT)
                "price_source_target": config["import_price"],
                "price_target_source": [-p for p in config["export_price"]],  # Negate because exporting earns money
            },
        ]

    def outputs(
        self,
        name: str,
        model_outputs: Mapping[str, Mapping[ModelOutputName, OutputData]],
        _config: GridConfigData,
    ) -> Mapping[GridDeviceName, Mapping[GridOutputName, OutputData]]:
        """Map model outputs to grid-specific output names."""
        connection = model_outputs[f"{name}:connection"]

        grid_outputs: dict[GridOutputName, OutputData] = {}

        # source_target = grid to system = IMPORT
        # target_source = system to grid = EXPORT
        grid_outputs[GRID_POWER_EXPORT] = replace(connection[CONNECTION_POWER_TARGET_SOURCE], type=OUTPUT_TYPE_POWER)
        grid_outputs[GRID_POWER_IMPORT] = replace(connection[CONNECTION_POWER_SOURCE_TARGET], type=OUTPUT_TYPE_POWER)

        # Active grid power (export - import)
        grid_outputs[GRID_POWER_ACTIVE] = replace(
            connection[CONNECTION_POWER_TARGET_SOURCE],
            values=[
                i - e
                for i, e in zip(
                    connection[CONNECTION_POWER_SOURCE_TARGET].values,
                    connection[CONNECTION_POWER_TARGET_SOURCE].values,
                    strict=True,
                )
            ],
            direction=None,
            type=OUTPUT_TYPE_POWER,
        )

        # Output the given inputs if they exist
        if CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE in connection:
            grid_outputs[GRID_POWER_MAX_EXPORT_PRICE] = connection[CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE]
        if CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET in connection:
            grid_outputs[GRID_POWER_MAX_IMPORT_PRICE] = connection[CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET]

        return {GRID_DEVICE_GRID: grid_outputs}


adapter = GridAdapter()
