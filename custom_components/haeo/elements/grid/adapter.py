"""Grid element adapter for model layer integration."""

from collections.abc import Mapping
from dataclasses import replace
from typing import Any, Final, Literal

from homeassistant.components.number import NumberDeviceClass, NumberEntityDescription
from homeassistant.const import UnitOfPower
from homeassistant.core import HomeAssistant

from custom_components.haeo.const import ConnectivityLevel
from custom_components.haeo.data.loader import TimeSeriesLoader
from custom_components.haeo.elements.input_fields import InputFieldInfo
from custom_components.haeo.model import ModelOutputName
from custom_components.haeo.model.const import OutputType
from custom_components.haeo.model.elements.power_connection import (
    CONNECTION_COST_SOURCE_TARGET,
    CONNECTION_COST_TARGET_SOURCE,
    CONNECTION_POWER_SOURCE_TARGET,
    CONNECTION_POWER_TARGET_SOURCE,
    CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET,
    CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE,
)
from custom_components.haeo.model.output_data import OutputData

from .flow import GridSubentryFlowHandler
from .schema import (
    CONF_EXPORT_LIMIT,
    CONF_EXPORT_PRICE,
    CONF_IMPORT_LIMIT,
    CONF_IMPORT_PRICE,
    DEFAULT_EXPORT_LIMIT,
    DEFAULT_IMPORT_LIMIT,
    ELEMENT_TYPE,
    GridConfigData,
    GridConfigSchema,
)

# Grid-specific output names for translation/sensor mapping
type GridOutputName = Literal[
    "grid_power_import",
    "grid_power_export",
    "grid_power_active",
    "grid_cost_import",
    "grid_cost_export",
    "grid_cost_net",
    "grid_power_max_import_price",
    "grid_power_max_export_price",
]

GRID_OUTPUT_NAMES: Final[frozenset[GridOutputName]] = frozenset(
    (
        GRID_POWER_IMPORT := "grid_power_import",
        GRID_POWER_EXPORT := "grid_power_export",
        GRID_POWER_ACTIVE := "grid_power_active",
        # Cost outputs
        GRID_COST_IMPORT := "grid_cost_import",
        GRID_COST_EXPORT := "grid_cost_export",
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

        # Helper to check entity list availability
        def entities_available(value: list[str] | float | None) -> bool:
            if not isinstance(value, list) or not value:
                return True  # Constants and missing values are always available
            return ts_loader.available(hass=hass, value=value)

        return entities_available(config.get("import_price")) and entities_available(config.get("export_price"))

    def inputs(
        self,
        config: GridConfigSchema,  # noqa: ARG002
    ) -> tuple[InputFieldInfo[NumberEntityDescription], ...]:
        """Return input field definitions for creating grid input entities.

        Grid has fixed device structure - all inputs belong to the main grid device.
        """
        return (
            InputFieldInfo(
                field_name=CONF_IMPORT_PRICE,
                entity_description=NumberEntityDescription(
                    key=CONF_IMPORT_PRICE,
                    translation_key=f"{ELEMENT_TYPE}_{CONF_IMPORT_PRICE}",
                    native_min_value=-1.0,
                    native_max_value=10.0,
                    native_step=0.001,
                ),
                output_type=OutputType.PRICE,
                time_series=True,
                direction="-",  # Import = consuming from grid = cost
            ),
            InputFieldInfo(
                field_name=CONF_EXPORT_PRICE,
                entity_description=NumberEntityDescription(
                    key=CONF_EXPORT_PRICE,
                    translation_key=f"{ELEMENT_TYPE}_{CONF_EXPORT_PRICE}",
                    native_min_value=-1.0,
                    native_max_value=10.0,
                    native_step=0.001,
                ),
                output_type=OutputType.PRICE,
                time_series=True,
                direction="+",  # Export = producing to grid = revenue
            ),
            InputFieldInfo(
                field_name=CONF_IMPORT_LIMIT,
                entity_description=NumberEntityDescription(
                    key=CONF_IMPORT_LIMIT,
                    translation_key=f"{ELEMENT_TYPE}_{CONF_IMPORT_LIMIT}",
                    native_unit_of_measurement=UnitOfPower.KILO_WATT,
                    device_class=NumberDeviceClass.POWER,
                    native_min_value=0.0,
                    native_max_value=1000.0,
                    native_step=0.1,
                ),
                output_type=OutputType.POWER_LIMIT,
                time_series=True,
                direction="+",
                default=DEFAULT_IMPORT_LIMIT,
            ),
            InputFieldInfo(
                field_name=CONF_EXPORT_LIMIT,
                entity_description=NumberEntityDescription(
                    key=CONF_EXPORT_LIMIT,
                    translation_key=f"{ELEMENT_TYPE}_{CONF_EXPORT_LIMIT}",
                    native_unit_of_measurement=UnitOfPower.KILO_WATT,
                    device_class=NumberDeviceClass.POWER,
                    native_min_value=0.0,
                    native_max_value=1000.0,
                    native_step=0.1,
                ),
                output_type=OutputType.POWER_LIMIT,
                time_series=True,
                direction="-",
                default=DEFAULT_EXPORT_LIMIT,
            ),
        )

    def model_elements(self, config: GridConfigData) -> list[dict[str, Any]]:
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
        grid_outputs[GRID_POWER_EXPORT] = replace(connection[CONNECTION_POWER_TARGET_SOURCE], type=OutputType.POWER)
        grid_outputs[GRID_POWER_IMPORT] = replace(connection[CONNECTION_POWER_SOURCE_TARGET], type=OutputType.POWER)

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
            type=OutputType.POWER,
        )

        # Cost outputs: only include if the connection has pricing configured
        # Import cost: positive value = money spent
        import_cost_data: OutputData | None = None
        export_cost_data: OutputData | None = None

        if CONNECTION_COST_SOURCE_TARGET in connection:
            import_cost_data = connection[CONNECTION_COST_SOURCE_TARGET]
            grid_outputs[GRID_COST_IMPORT] = replace(import_cost_data, direction="-")

        # Export cost: negative value = money earned (revenue)
        # The price_target_source is already negated in create_model_elements, so cost is negative
        if CONNECTION_COST_TARGET_SOURCE in connection:
            export_cost_data = connection[CONNECTION_COST_TARGET_SOURCE]
            grid_outputs[GRID_COST_EXPORT] = replace(export_cost_data, direction="+")

        # Net cost = import cost + export cost (where export cost is negative = revenue)
        # Only output if at least one cost exists
        if import_cost_data is not None and export_cost_data is not None:
            net_cost_values = tuple(
                i + e for i, e in zip(import_cost_data.values, export_cost_data.values, strict=True)
            )
            grid_outputs[GRID_COST_NET] = OutputData(
                type=OutputType.COST, unit="$", values=net_cost_values, direction=None
            )
        elif import_cost_data is not None:
            grid_outputs[GRID_COST_NET] = replace(import_cost_data, direction=None)
        elif export_cost_data is not None:
            grid_outputs[GRID_COST_NET] = replace(export_cost_data, direction=None)

        # Output the given inputs if they exist
        if CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE in connection:
            grid_outputs[GRID_POWER_MAX_EXPORT_PRICE] = connection[CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE]
        if CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET in connection:
            grid_outputs[GRID_POWER_MAX_IMPORT_PRICE] = connection[CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET]

        return {GRID_DEVICE_GRID: grid_outputs}


adapter = GridAdapter()
