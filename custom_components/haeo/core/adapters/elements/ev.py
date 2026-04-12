"""EV element adapter for model layer integration."""

from collections.abc import Mapping
from dataclasses import replace
from typing import Any, Final, Literal

import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.core.adapters.output_utils import expect_output_data
from custom_components.haeo.core.const import ConnectivityLevel
from custom_components.haeo.core.model import ModelElementConfig, ModelOutputName, ModelOutputValue
from custom_components.haeo.core.model import battery as model_battery
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.model.elements import (
    MODEL_ELEMENT_TYPE_BATTERY,
    MODEL_ELEMENT_TYPE_CONNECTION,
    MODEL_ELEMENT_TYPE_NODE,
)
from custom_components.haeo.core.model.elements.connection import CONNECTION_POWER_SOURCE_TARGET, CONNECTION_SEGMENTS
from custom_components.haeo.core.model.elements.segments import POWER_LIMIT_SOURCE_TARGET, POWER_LIMIT_TARGET_SOURCE
from custom_components.haeo.core.model.output_data import OutputData
from custom_components.haeo.core.schema import extract_connection_target
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.ev import (
    CONF_CAPACITY,
    CONF_CONNECTED,
    CONF_CURRENT_SOC,
    CONF_MAX_CHARGE_RATE,
    CONF_MAX_DISCHARGE_RATE,
    CONF_PUBLIC_CHARGING_PRICE,
    ELEMENT_TYPE,
    SECTION_CHARGING,
    SECTION_PUBLIC_CHARGING,
    SECTION_TRIP,
    SECTION_VEHICLE,
    EvConfigData,
)
from custom_components.haeo.core.schema.sections import (
    CONF_CONNECTION,
    CONF_EFFICIENCY_SOURCE_TARGET,
    CONF_EFFICIENCY_TARGET_SOURCE,
    CONF_MAX_POWER_SOURCE_TARGET,
    CONF_MAX_POWER_TARGET_SOURCE,
    SECTION_EFFICIENCY,
    SECTION_POWER_LIMITS,
)

# EV-specific output names for translation/sensor mapping
type EvOutputName = Literal[
    "ev_power_charge",
    "ev_power_discharge",
    "ev_power_active",
    "ev_state_of_charge",
    "ev_energy_stored",
    "ev_power_balance",
    "ev_trip_energy_required",
    "ev_public_charge_power",
    "ev_power_max_charge_price",
    "ev_power_max_discharge_price",
]

EV_OUTPUT_NAMES: Final[frozenset[EvOutputName]] = frozenset(
    (
        EV_POWER_CHARGE := "ev_power_charge",
        EV_POWER_DISCHARGE := "ev_power_discharge",
        EV_POWER_ACTIVE := "ev_power_active",
        EV_STATE_OF_CHARGE := "ev_state_of_charge",
        EV_ENERGY_STORED := "ev_energy_stored",
        EV_POWER_BALANCE := "ev_power_balance",
        EV_TRIP_ENERGY_REQUIRED := "ev_trip_energy_required",
        EV_PUBLIC_CHARGE_POWER := "ev_public_charge_power",
        EV_POWER_MAX_CHARGE_PRICE := "ev_power_max_charge_price",
        EV_POWER_MAX_DISCHARGE_PRICE := "ev_power_max_discharge_price",
    )
)

type EvDeviceName = Literal[ElementType.EV]

EV_DEVICE_NAMES: Final[frozenset[EvDeviceName]] = frozenset(
    (EV_DEVICE_EV := ElementType.EV,),
)


class EvAdapter:
    """Adapter for EV elements."""

    element_type: str = ELEMENT_TYPE
    advanced: bool = False
    connectivity: ConnectivityLevel = ConnectivityLevel.ADVANCED

    def model_elements(self, config: EvConfigData) -> list[ModelElementConfig]:
        """Create model elements for EV configuration.

        Creates 6 model elements:
        1. {name} - Battery (EV battery)
        2. {name}:connection - Connection (home charging: EV ↔ switchboard)
        3. {name}:trip - Battery (trip energy requirement)
        4. {name}:trip_connection - Connection (EV battery ↔ trip battery)
        5. {name}:public_grid - Node (public charging source)
        6. {name}:public_connection - Connection (public grid ↔ trip battery)
        """
        name = config["name"]
        vehicle = config[SECTION_VEHICLE]
        charging = config[SECTION_CHARGING]
        power_limits = config[SECTION_POWER_LIMITS]
        efficiency = config[SECTION_EFFICIENCY]

        capacity = vehicle[CONF_CAPACITY]
        capacity_first = float(capacity[0])
        initial_soc = vehicle[CONF_CURRENT_SOC] / 100.0
        initial_charge = initial_soc * capacity_first

        max_charge = charging[CONF_MAX_CHARGE_RATE]
        max_discharge = charging.get(CONF_MAX_DISCHARGE_RATE, 0.0)

        trip = config.get(SECTION_TRIP, {})
        connected_flag = trip.get(CONF_CONNECTED)
        trip_capacity: NDArray[np.floating[Any]] | None = None

        elements: list[ModelElementConfig] = []

        # 1. EV Battery
        elements.append(
            {
                "element_type": MODEL_ELEMENT_TYPE_BATTERY,
                "name": name,
                "capacity": capacity,
                "initial_charge": initial_charge,
                "salvage_value": 0.0,
            }
        )

        # 2. Home charging connection (EV ↔ switchboard)
        # Power limits zeroed when disconnected via connected_flag
        home_max_charge = _apply_connected_mask(max_charge, connected_flag)
        home_max_discharge = _apply_connected_mask(max_discharge, connected_flag)

        elements.append(
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": f"{name}:connection",
                "source": name,
                "target": extract_connection_target(config[CONF_CONNECTION]),
                "segments": {
                    "efficiency": {
                        "segment_type": "efficiency",
                        "efficiency_source_target": efficiency.get(CONF_EFFICIENCY_SOURCE_TARGET),
                        "efficiency_target_source": efficiency.get(CONF_EFFICIENCY_TARGET_SOURCE),
                    },
                    "power_limit": {
                        "segment_type": "power_limit",
                        "max_power_source_target": _combine_limits(
                            home_max_discharge,
                            power_limits.get(CONF_MAX_POWER_SOURCE_TARGET),
                        ),
                        "max_power_target_source": _combine_limits(
                            home_max_charge,
                            power_limits.get(CONF_MAX_POWER_TARGET_SOURCE),
                        ),
                    },
                },
            }
        )

        # 3. Trip battery (energy requirement for the trip)
        # Capacity and initial charge set per-trip from calendar data
        elements.append(
            {
                "element_type": MODEL_ELEMENT_TYPE_BATTERY,
                "name": f"{name}:trip",
                "capacity": trip_capacity if trip_capacity is not None else np.array([0.0]),
                "initial_charge": 0.0,
                "salvage_value": 0.0,
            }
        )

        # 4. Trip connection (EV battery ↔ trip battery)
        # Active only during trips (inverse of connected_flag)
        disconnected_flag = _invert_flag(connected_flag)
        trip_max_power = _apply_connected_mask(max_discharge, disconnected_flag)

        elements.append(
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": f"{name}:trip_connection",
                "source": name,
                "target": f"{name}:trip",
                "segments": {
                    "power_limit": {
                        "segment_type": "power_limit",
                        "max_power_source_target": trip_max_power,
                        "max_power_target_source": None,
                    },
                },
            }
        )

        # 5. Public charging grid (source-only node)
        elements.append(
            {
                "element_type": MODEL_ELEMENT_TYPE_NODE,
                "name": f"{name}:public_grid",
                "is_source": True,
                "is_sink": False,
            }
        )

        # 6. Public charging connection (public grid ↔ trip battery)
        public_charging = config.get(SECTION_PUBLIC_CHARGING, {})
        public_price = public_charging.get(CONF_PUBLIC_CHARGING_PRICE)
        pub_max_power = _apply_connected_mask(None, disconnected_flag)

        pub_segments: dict[str, Any] = {
            "power_limit": {
                "segment_type": "power_limit",
                "max_power_source_target": pub_max_power,
                "max_power_target_source": None,
            },
        }
        if public_price is not None:
            pub_segments["pricing"] = {
                "segment_type": "pricing",
                "price_source_target": public_price,
                "price_target_source": None,
            }

        elements.append(
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": f"{name}:public_connection",
                "source": f"{name}:public_grid",
                "target": f"{name}:trip",
                "segments": pub_segments,
            }
        )

        return elements

    def outputs(
        self,
        name: str,
        model_outputs: Mapping[str, Mapping[ModelOutputName, ModelOutputValue]],
        *,
        config: EvConfigData,
        **_kwargs: Any,
    ) -> Mapping[EvDeviceName, Mapping[EvOutputName, OutputData]]:
        """Map model outputs to EV-specific output names."""
        battery_outputs = model_outputs[name]
        connection_outputs = model_outputs[f"{name}:connection"]
        trip_outputs = model_outputs[f"{name}:trip"]

        ev_outputs: dict[EvOutputName, OutputData] = {}

        # EV battery outputs
        power_charge = expect_output_data(battery_outputs[model_battery.BATTERY_POWER_CHARGE])
        power_discharge = expect_output_data(battery_outputs[model_battery.BATTERY_POWER_DISCHARGE])
        energy_stored = expect_output_data(battery_outputs[model_battery.BATTERY_ENERGY_STORED])

        ev_outputs[EV_POWER_CHARGE] = power_charge
        ev_outputs[EV_POWER_DISCHARGE] = power_discharge
        ev_outputs[EV_ENERGY_STORED] = energy_stored

        # Active power (discharge - charge)
        ev_outputs[EV_POWER_ACTIVE] = replace(
            power_discharge,
            values=[d - c for d, c in zip(power_discharge.values, power_charge.values, strict=True)],
            direction=None,
            type=OutputType.POWER,
        )

        # State of charge
        vehicle = config[SECTION_VEHICLE]
        capacity = vehicle[CONF_CAPACITY]
        capacity_first = float(capacity[0])
        if capacity_first > 0:
            soc_values = [float(e) / capacity_first * 100.0 for e in energy_stored.values]
        else:
            soc_values = [0.0] * len(energy_stored.values)

        ev_outputs[EV_STATE_OF_CHARGE] = OutputData(
            type=OutputType.STATE_OF_CHARGE,
            unit="%",
            values=tuple(soc_values),
            direction=None,
        )

        # Power balance shadow price
        ev_outputs[EV_POWER_BALANCE] = expect_output_data(battery_outputs[model_battery.BATTERY_POWER_BALANCE])

        # Trip energy required (from trip battery energy stored)
        trip_energy = expect_output_data(trip_outputs[model_battery.BATTERY_ENERGY_STORED])
        ev_outputs[EV_TRIP_ENERGY_REQUIRED] = replace(trip_energy, type=OutputType.ENERGY)

        # Public charging power
        pub_connection = model_outputs.get(f"{name}:public_connection")
        if pub_connection is not None:
            pub_power = expect_output_data(pub_connection.get(CONNECTION_POWER_SOURCE_TARGET))
            if pub_power is not None:
                ev_outputs[EV_PUBLIC_CHARGE_POWER] = replace(pub_power, type=OutputType.POWER)

        # Shadow prices for charging connection power limits
        if isinstance(segments_output := connection_outputs.get(CONNECTION_SEGMENTS), Mapping) and isinstance(
            power_limit_outputs := segments_output.get("power_limit"), Mapping
        ):
            shadow_mappings: tuple[tuple[EvOutputName, str], ...] = (
                (EV_POWER_MAX_DISCHARGE_PRICE, POWER_LIMIT_SOURCE_TARGET),
                (EV_POWER_MAX_CHARGE_PRICE, POWER_LIMIT_TARGET_SOURCE),
            )
            for output_name, shadow_key in shadow_mappings:
                if (shadow := expect_output_data(power_limit_outputs.get(shadow_key))) is not None:
                    ev_outputs[output_name] = shadow

        return {EV_DEVICE_EV: ev_outputs}


adapter = EvAdapter()


def _apply_connected_mask(
    value: NDArray[np.floating[Any]] | float | None,
    connected_flag: NDArray[np.floating[Any]] | float | None,
) -> NDArray[np.floating[Any]] | float | None:
    """Apply connected flag as a mask to a power limit value.

    When connected_flag is 0.0, the result is 0.0 (disabled).
    When connected_flag is 1.0, the result is the original value.
    """
    if connected_flag is None:
        return value
    if value is None:
        return None
    return value * connected_flag


def _invert_flag(
    flag: NDArray[np.floating[Any]] | float | None,
) -> NDArray[np.floating[Any]] | float | None:
    """Invert a binary flag (1.0 → 0.0, 0.0 → 1.0)."""
    if flag is None:
        return None
    return 1.0 - flag


def _combine_limits(
    *limits: NDArray[np.floating[Any]] | float | None,
) -> NDArray[np.floating[Any]] | float | None:
    """Combine multiple power limit values by taking the element-wise minimum.

    None values are ignored. If all values are None, returns None.
    """
    result: NDArray[np.floating[Any]] | float | None = None
    for limit in limits:
        if limit is None:
            continue
        result = limit if result is None else np.minimum(result, limit)
    return result
