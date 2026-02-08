"""Grid element adapter for model layer integration."""

from collections.abc import Mapping
from dataclasses import replace
from typing import Any, Final, Literal

from homeassistant.components.number import NumberDeviceClass, NumberEntityDescription
from homeassistant.const import UnitOfEnergy, UnitOfPower, UnitOfTime
import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.const import ConnectivityLevel
from custom_components.haeo.elements.input_fields import InputFieldDefaults, InputFieldInfo
from custom_components.haeo.elements.output_utils import expect_output_data
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
from custom_components.haeo.model.util import broadcast_to_sequence
from custom_components.haeo.schema import extract_connection_target
from custom_components.haeo.sections import (
    CONF_CONNECTION,
    CONF_DEMAND_BLOCK_MINUTES,
    CONF_DEMAND_CURRENT_ENERGY_SOURCE_TARGET,
    CONF_DEMAND_PEAK_COST_SOURCE_TARGET,
    CONF_DEMAND_PRICE_SOURCE_TARGET,
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_MAX_POWER_TARGET_SOURCE,
    CONF_PRICE_SOURCE_TARGET,
    CONF_PRICE_TARGET_SOURCE,
    SECTION_COMMON,
    SECTION_DEMAND_PRICING,
    SECTION_POWER_LIMITS,
    SECTION_PRICING,
)

from .schema import ELEMENT_TYPE, GridConfigData

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

    def inputs(self, config: Any) -> dict[str, dict[str, InputFieldInfo[Any]]]:
        """Return input field definitions for grid elements."""
        _ = config
        return {
            SECTION_PRICING: {
                CONF_PRICE_SOURCE_TARGET: InputFieldInfo(
                    field_name=CONF_PRICE_SOURCE_TARGET,
                    entity_description=NumberEntityDescription(
                        key=CONF_PRICE_SOURCE_TARGET,
                        translation_key=f"{ELEMENT_TYPE}_{CONF_PRICE_SOURCE_TARGET}",
                        native_min_value=-1.0,
                        native_max_value=10.0,
                        native_step=0.001,
                    ),
                    output_type=OutputType.PRICE,
                    time_series=True,
                    direction="-",  # Import = consuming from grid = cost
                ),
                CONF_PRICE_TARGET_SOURCE: InputFieldInfo(
                    field_name=CONF_PRICE_TARGET_SOURCE,
                    entity_description=NumberEntityDescription(
                        key=CONF_PRICE_TARGET_SOURCE,
                        translation_key=f"{ELEMENT_TYPE}_{CONF_PRICE_TARGET_SOURCE}",
                        native_min_value=-1.0,
                        native_max_value=10.0,
                        native_step=0.001,
                    ),
                    output_type=OutputType.PRICE,
                    time_series=True,
                    direction="+",  # Export = producing to grid = revenue
                ),
            },
            SECTION_DEMAND_PRICING: {
                CONF_DEMAND_PRICE_SOURCE_TARGET: InputFieldInfo(
                    field_name=CONF_DEMAND_PRICE_SOURCE_TARGET,
                    entity_description=NumberEntityDescription(
                        key=CONF_DEMAND_PRICE_SOURCE_TARGET,
                        translation_key=f"{ELEMENT_TYPE}_{CONF_DEMAND_PRICE_SOURCE_TARGET}",
                        native_unit_of_measurement="$/kW",
                        native_min_value=0.0,
                        native_max_value=100.0,
                        native_step=0.01,
                    ),
                    output_type=OutputType.COST,
                    time_series=True,
                    direction="-",
                ),
                CONF_DEMAND_CURRENT_ENERGY_SOURCE_TARGET: InputFieldInfo(
                    field_name=CONF_DEMAND_CURRENT_ENERGY_SOURCE_TARGET,
                    entity_description=NumberEntityDescription(
                        key=CONF_DEMAND_CURRENT_ENERGY_SOURCE_TARGET,
                        translation_key=f"{ELEMENT_TYPE}_{CONF_DEMAND_CURRENT_ENERGY_SOURCE_TARGET}",
                        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
                        device_class=NumberDeviceClass.ENERGY,
                        native_min_value=0.0,
                        native_max_value=1_000_000.0,
                        native_step=0.01,
                    ),
                    output_type=OutputType.ENERGY,
                    time_series=False,
                    direction="-",
                ),
                CONF_DEMAND_PEAK_COST_SOURCE_TARGET: InputFieldInfo(
                    field_name=CONF_DEMAND_PEAK_COST_SOURCE_TARGET,
                    entity_description=NumberEntityDescription(
                        key=CONF_DEMAND_PEAK_COST_SOURCE_TARGET,
                        translation_key=f"{ELEMENT_TYPE}_{CONF_DEMAND_PEAK_COST_SOURCE_TARGET}",
                        native_unit_of_measurement="$",
                        native_min_value=0.0,
                        native_max_value=1_000_000.0,
                        native_step=0.01,
                    ),
                    output_type=OutputType.COST,
                    time_series=False,
                    direction="-",
                ),
                CONF_DEMAND_BLOCK_MINUTES: InputFieldInfo(
                    field_name=CONF_DEMAND_BLOCK_MINUTES,
                    entity_description=NumberEntityDescription(
                        key=CONF_DEMAND_BLOCK_MINUTES,
                        translation_key=f"{ELEMENT_TYPE}_{CONF_DEMAND_BLOCK_MINUTES}",
                        native_unit_of_measurement=UnitOfTime.MINUTES,
                        native_min_value=1.0,
                        native_max_value=1440.0,
                        native_step=1.0,
                    ),
                    output_type=OutputType.DURATION,
                    time_series=False,
                ),
            },
            SECTION_POWER_LIMITS: {
                CONF_MAX_POWER_SOURCE_TARGET: InputFieldInfo(
                    field_name=CONF_MAX_POWER_SOURCE_TARGET,
                    entity_description=NumberEntityDescription(
                        key=CONF_MAX_POWER_SOURCE_TARGET,
                        translation_key=f"{ELEMENT_TYPE}_{CONF_MAX_POWER_SOURCE_TARGET}",
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
                CONF_MAX_POWER_TARGET_SOURCE: InputFieldInfo(
                    field_name=CONF_MAX_POWER_TARGET_SOURCE,
                    entity_description=NumberEntityDescription(
                        key=CONF_MAX_POWER_TARGET_SOURCE,
                        translation_key=f"{ELEMENT_TYPE}_{CONF_MAX_POWER_TARGET_SOURCE}",
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
            },
        }

    def model_elements(self, config: GridConfigData) -> list[ModelElementConfig]:
        """Create model elements for Grid configuration."""
        demand_block_minutes = config[SECTION_DEMAND_PRICING].get(CONF_DEMAND_BLOCK_MINUTES)
        demand_block_hours = demand_block_minutes / 60.0 if demand_block_minutes is not None else None
        return [
            # Create Node for the grid (both source and sink - can import and export)
            {
                "element_type": MODEL_ELEMENT_TYPE_NODE,
                "name": config[SECTION_COMMON]["name"],
                "is_source": True,
                "is_sink": True,
            },
            # Create a connection from system node to grid
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": f"{config[SECTION_COMMON]['name']}:connection",
                "source": config[SECTION_COMMON]["name"],
                "target": extract_connection_target(config[SECTION_COMMON][CONF_CONNECTION]),
                "segments": {
                    "power_limit": {
                        "segment_type": "power_limit",
                        "max_power_source_target": config[SECTION_POWER_LIMITS].get(CONF_MAX_POWER_SOURCE_TARGET),
                        "max_power_target_source": config[SECTION_POWER_LIMITS].get(CONF_MAX_POWER_TARGET_SOURCE),
                    },
                    "pricing": {
                        "segment_type": "pricing",
                        "price_source_target": config[SECTION_PRICING][CONF_PRICE_SOURCE_TARGET],
                        "price_target_source": -config[SECTION_PRICING][CONF_PRICE_TARGET_SOURCE],
                    },
                    "demand_pricing": {
                        "segment_type": "demand_pricing",
                        "demand_price_source_target": config[SECTION_DEMAND_PRICING].get(
                            CONF_DEMAND_PRICE_SOURCE_TARGET
                        ),
                        "demand_current_energy_source_target": config[SECTION_DEMAND_PRICING].get(
                            CONF_DEMAND_CURRENT_ENERGY_SOURCE_TARGET
                        ),
                        "demand_peak_cost_source_target": config[SECTION_DEMAND_PRICING].get(
                            CONF_DEMAND_PEAK_COST_SOURCE_TARGET
                        ),
                        "demand_block_hours": demand_block_hours,
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
        periods: NDArray[np.floating[Any]],
        **_kwargs: Any,
    ) -> Mapping[GridDeviceName, Mapping[GridOutputName, OutputData]]:
        """Map model outputs to grid-specific output names."""
        connection = model_outputs[f"{name}:connection"]

        grid_outputs: dict[GridOutputName, OutputData] = {}

        # source_target = grid to system = IMPORT
        # target_source = system to grid = EXPORT
        power_import = expect_output_data(connection[CONNECTION_POWER_SOURCE_TARGET])
        power_export = expect_output_data(connection[CONNECTION_POWER_TARGET_SOURCE])

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
        import_prices = broadcast_to_sequence(config[SECTION_PRICING][CONF_PRICE_SOURCE_TARGET], len(periods))
        export_prices = broadcast_to_sequence(config[SECTION_PRICING][CONF_PRICE_TARGET_SOURCE], len(periods))

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
        if isinstance(segments_output := connection.get(CONNECTION_SEGMENTS), Mapping) and isinstance(
            power_limit_outputs := segments_output.get("power_limit"), Mapping
        ):
            shadow_mappings: tuple[tuple[GridOutputName, str], ...] = (
                (GRID_POWER_MAX_EXPORT_PRICE, POWER_LIMIT_TARGET_SOURCE),
                (GRID_POWER_MAX_IMPORT_PRICE, POWER_LIMIT_SOURCE_TARGET),
            )
            for output_name, shadow_key in shadow_mappings:
                if (shadow := expect_output_data(power_limit_outputs.get(shadow_key))) is not None:
                    grid_outputs[output_name] = shadow

        return {GRID_DEVICE_GRID: grid_outputs}


adapter = GridAdapter()
