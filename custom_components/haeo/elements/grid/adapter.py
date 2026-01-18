"""Grid element adapter for model layer integration."""

from collections.abc import Mapping, Sequence
from dataclasses import replace
from typing import Any, Final, Literal

from homeassistant.components.number import NumberDeviceClass, NumberEntityDescription
from homeassistant.const import UnitOfPower
from homeassistant.core import HomeAssistant
import numpy as np

from custom_components.haeo.const import ConnectivityLevel
from custom_components.haeo.data.loader import TimeSeriesLoader
from custom_components.haeo.elements.input_fields import InputFieldDefaults, InputFieldInfo
from custom_components.haeo.model import ModelElementConfig, ModelOutputName
from custom_components.haeo.model.const import OutputType
from custom_components.haeo.model.elements import (
    ConnectionElementConfig,
    MODEL_ELEMENT_TYPE_CONNECTION,
    MODEL_ELEMENT_TYPE_NODE,
    NodeElementConfig,
)
from custom_components.haeo.model.elements.power_connection import (
    CONNECTION_POWER_SOURCE_TARGET,
    CONNECTION_POWER_TARGET_SOURCE,
    CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET,
    CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE,
)
from custom_components.haeo.model.output_data import OutputData

from .schema import (
    CONF_CONNECTION,
    CONF_EXPORT_LIMIT,
    CONF_EXPORT_PRICE,
    CONF_IMPORT_LIMIT,
    CONF_IMPORT_PRICE,
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

    def inputs(self, config: Any) -> dict[str, InputFieldInfo[Any]]:
        """Return input field definitions for grid elements."""
        _ = config
        return {
            CONF_IMPORT_PRICE: InputFieldInfo(
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
            CONF_EXPORT_PRICE: InputFieldInfo(
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
            CONF_IMPORT_LIMIT: InputFieldInfo(
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
                defaults=InputFieldDefaults(mode="value", value=100.0),
            ),
            CONF_EXPORT_LIMIT: InputFieldInfo(
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
                defaults=InputFieldDefaults(mode="value", value=100.0),
            ),
        }

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
            "import_price": np.asarray(loaded_values["import_price"], dtype=float),
            "export_price": np.asarray(loaded_values["export_price"], dtype=float),
        }

        # Optional limit fields - only include if present
        if "import_limit" in loaded_values:
            data["import_limit"] = np.asarray(loaded_values["import_limit"], dtype=float)

        if "export_limit" in loaded_values:
            data["export_limit"] = np.asarray(loaded_values["export_limit"], dtype=float)

        return data

    def model_elements(self, config: GridConfigData) -> list[ModelElementConfig]:
        """Create model elements for Grid configuration."""
        node_config: NodeElementConfig = {
            "element_type": MODEL_ELEMENT_TYPE_NODE,
            "name": config["name"],
            "is_source": True,
            "is_sink": True,
        }
        connection_config: ConnectionElementConfig = {
            "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
            "name": f"{config['name']}:connection",
            "source": config["name"],
            "target": config["connection"],
            "max_power_source_target": config.get("import_limit"),  # source_target is grid to system (IMPORT)
            "max_power_target_source": config.get("export_limit"),  # target_source is system to grid (EXPORT)
            "price_source_target": config["import_price"],
            "price_target_source": -config["export_price"],  # Negate because exporting earns money
        }
        return [node_config, connection_config]

    def outputs(
        self,
        name: str,
        model_outputs: Mapping[str, Mapping[ModelOutputName, OutputData]],
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

        # Output the shadow prices if they exist
        if CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE in connection:
            grid_outputs[GRID_POWER_MAX_EXPORT_PRICE] = connection[CONNECTION_SHADOW_POWER_MAX_TARGET_SOURCE]
        if CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET in connection:
            grid_outputs[GRID_POWER_MAX_IMPORT_PRICE] = connection[CONNECTION_SHADOW_POWER_MAX_SOURCE_TARGET]

        return {GRID_DEVICE_GRID: grid_outputs}


adapter = GridAdapter()
