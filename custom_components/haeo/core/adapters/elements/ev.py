"""EV element adapter for model layer integration."""

from collections.abc import Mapping
from dataclasses import dataclass, replace
from typing import Any, Final, Literal

import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.core.adapters.output_utils import connection_power, expect_output_data
from custom_components.haeo.core.const import ConnectivityLevel
from custom_components.haeo.core.data.loader.calendar_resolver import CalendarBoundaryData
from custom_components.haeo.core.model import ModelElementConfig, ModelOutputName, ModelOutputValue
from custom_components.haeo.core.model import battery as model_battery
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.model.elements import (
    MODEL_ELEMENT_TYPE_BATTERY,
    MODEL_ELEMENT_TYPE_CONNECTION,
    MODEL_ELEMENT_TYPE_DEFERRABLE_LOAD,
)
from custom_components.haeo.core.model.elements.battery import BATTERY_RESERVE_SHORTFALL, BatteryElementConfig
from custom_components.haeo.core.model.elements.connection import CONNECTION_SEGMENTS
from custom_components.haeo.core.model.elements.deferrable_load import (
    DEFERRABLE_LOAD_ENERGY_ABSORBED,
    DEFERRABLE_LOAD_ENERGY_DEFICIT,
)
from custom_components.haeo.core.model.output_data import OutputData
from custom_components.haeo.core.schema import extract_connection_target
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.ev import (
    CONF_CAPACITY,
    CONF_CONNECTED,
    CONF_CURRENT_SOC,
    CONF_ENERGY_PER_DISTANCE,
    CONF_MAX_CHARGE_RATE,
    CONF_MAX_DISCHARGE_RATE,
    CONF_ODOMETER,
    CONF_ODOMETER_AT_DISCONNECT,
    CONF_PUBLIC_CHARGING_PRICE,
    CONF_RESERVE_PRICE,
    CONF_RESERVE_SOC,
    CONF_TRIP_CALENDAR,
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

# Effectively unlimited power (kW) for trip/public flows that are only
# gated by the away mask, not by a physical charger.
_UNLIMITED_POWER: Final = 1.0e6

# Threshold above which a connected flag counts as plugged in.
_CONNECTED_THRESHOLD: Final = 0.5

# Default public charging price ($/kWh) when none is configured. High enough
# that home charging always wins when physically possible, but finite so the
# trip energy requirement can never make the optimization infeasible.
DEFAULT_PUBLIC_CHARGING_PRICE: Final = 10.0

# EV-specific output names for translation/sensor mapping
type EvOutputName = Literal[
    "ev_power_charge",
    "ev_power_discharge",
    "ev_power_active",
    "ev_state_of_charge",
    "ev_energy_stored",
    "ev_trip_energy_delivered",
    "ev_trip_energy_deficit",
    "ev_reserve_shortfall",
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
        EV_TRIP_ENERGY_DELIVERED := "ev_trip_energy_delivered",
        EV_TRIP_ENERGY_DEFICIT := "ev_trip_energy_deficit",
        EV_RESERVE_SHORTFALL := "ev_reserve_shortfall",
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
    can_source: bool = True
    can_sink: bool = True

    def model_elements(self, config: EvConfigData) -> list[ModelElementConfig]:
        """Create model elements for EV configuration.

        Creates 5 model elements:
        1. {name} - Battery (EV battery)
        2. {name}:charge - Connection (network → EV, home charging)
        3. {name}:discharge - Connection (EV → network, V2G)
        4. {name}:trip - Deferrable load (trip energy requirement)
        5. {name}:trip_connection - Connection (EV → trip load, away only)

        Trip windows come from the trip calendar: while away the home
        connections are masked off and trip energy (distance times consumption)
        is due into the trip load by each trip's end. The requirement is not
        hard — any shortfall is priced at the public charging price, which
        models topping up publicly during the trip and keeps the optimization
        feasible when home charging cannot cover the trip in time.
        """
        name = config["name"]
        vehicle = config[SECTION_VEHICLE]
        charging = config[SECTION_CHARGING]
        power_limits = config[SECTION_POWER_LIMITS]
        efficiency = config[SECTION_EFFICIENCY]
        target_name = extract_connection_target(config[CONF_CONNECTION])

        capacity = vehicle[CONF_CAPACITY]
        capacity_first = float(capacity[0])
        # current_soc is already a 0-1 ratio (the loader converts percent
        # fields); clamp so a glitched sensor cannot make the model infeasible
        initial_charge = min(max(vehicle[CONF_CURRENT_SOC], 0.0), 1.0) * capacity_first
        energy_per_distance = float(vehicle[CONF_ENERGY_PER_DISTANCE])

        max_charge = charging[CONF_MAX_CHARGE_RATE]
        max_discharge = charging.get(CONF_MAX_DISCHARGE_RATE, 0.0)

        trip = config.get(SECTION_TRIP, {})
        calendar = trip.get(CONF_TRIP_CALENDAR)
        connected_live = trip.get(CONF_CONNECTED)

        # Trip energy requirements from the calendar (distances in km):
        # capacity opens at each trip's start, the requirement is due by its
        # end. Cumulative sums let multiple trips share the one sink.
        trip_capacity: NDArray[np.float64] | float = 0.0
        trip_required: NDArray[np.float64] | float = 0.0
        if calendar is not None:
            trip_capacity = np.cumsum(calendar["value_edge_start"]) * energy_per_distance
            trip_required = np.cumsum(calendar["value_edge_end"]) * energy_per_distance

        connected_flag = _combine_connected(calendar, connected_live)
        away_flag = _invert_flag(connected_flag)

        trip_initial = _trip_progress_energy(trip, calendar, energy_per_distance, connected_flag)

        # Home charging limits zeroed while away via connected_flag
        home_max_charge = _apply_connected_mask(max_charge, connected_flag)
        home_max_discharge = _apply_connected_mask(max_discharge, connected_flag)

        # EV pack battery, with reserve demand pricing at trip window ends
        pack: BatteryElementConfig = {
            "element_type": MODEL_ELEMENT_TYPE_BATTERY,
            "name": name,
            "capacity": capacity,
            "initial_charge": initial_charge,
            "salvage_value": 0.0,
        }
        reserve = _reserve_config(config, calendar)
        if reserve is not None:
            pack["reserve_level"] = reserve.level
            pack["reserve_mask"] = reserve.mask
            pack["reserve_price"] = reserve.price

        return [
            # 1. EV Battery
            pack,
            # 2. Home charging: network → EV
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": f"{name}:charge",
                "source": target_name,
                "target": name,
                "segments": {
                    "efficiency": {
                        "segment_type": "efficiency",
                        "efficiency": efficiency.get(CONF_EFFICIENCY_TARGET_SOURCE),
                    },
                    "power_limit": {
                        "segment_type": "power_limit",
                        "max_power": _combine_limits(
                            home_max_charge,
                            power_limits.get(CONF_MAX_POWER_TARGET_SOURCE),
                        ),
                    },
                },
            },
            # 3. V2G discharge: EV → network
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": f"{name}:discharge",
                "source": name,
                "target": target_name,
                "segments": {
                    "efficiency": {
                        "segment_type": "efficiency",
                        "efficiency": efficiency.get(CONF_EFFICIENCY_SOURCE_TARGET),
                    },
                    "power_limit": {
                        "segment_type": "power_limit",
                        "max_power": _combine_limits(
                            home_max_discharge,
                            power_limits.get(CONF_MAX_POWER_SOURCE_TARGET),
                        ),
                    },
                },
            },
            # 4. Trip requirement as a deferrable load: capacity opens at
            # each trip's start, the requirement is due by its end, and any
            # locked-in shortfall is priced at the public charging price —
            # the energy that would have to be bought publicly mid-trip.
            {
                "element_type": MODEL_ELEMENT_TYPE_DEFERRABLE_LOAD,
                "name": f"{name}:trip",
                "capacity": trip_capacity,
                "required": trip_required,
                "initial_energy": trip_initial,
                "deficit_price": _to_boundaries(_public_price(config), len(capacity)),
            },
            # 5. Trip connection: EV → trip load. Driving power is not
            # limited by the charger, only by being away.
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": f"{name}:trip_connection",
                "source": name,
                "target": f"{name}:trip",
                "segments": {
                    "power_limit": {
                        "segment_type": "power_limit",
                        "max_power": _mask_or_zero(away_flag, _UNLIMITED_POWER),
                    },
                },
            },
        ]

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
        trip_outputs = model_outputs[f"{name}:trip"]
        charge_conn = model_outputs.get(f"{name}:charge")
        discharge_conn = model_outputs.get(f"{name}:discharge")

        energy_stored = expect_output_data(battery_outputs[model_battery.BATTERY_ENERGY_STORED])
        period_count = len(expect_output_data(battery_outputs[model_battery.BATTERY_POWER_CHARGE]).values)

        power_charge = replace(connection_power(charge_conn, period_count), type=OutputType.POWER, direction="-")
        power_discharge = replace(connection_power(discharge_conn, period_count), type=OutputType.POWER, direction="+")

        ev_outputs: dict[EvOutputName, OutputData] = {
            EV_POWER_CHARGE: power_charge,
            EV_POWER_DISCHARGE: power_discharge,
            EV_ENERGY_STORED: energy_stored,
        }

        # Active power (discharge - charge)
        ev_outputs[EV_POWER_ACTIVE] = replace(
            power_discharge,
            values=[d - c for d, c in zip(power_discharge.values, power_charge.values, strict=True)],
            direction=None,
            type=OutputType.POWER,
        )

        # State of charge as a 0-1 ratio (display scales percent outputs)
        vehicle = config[SECTION_VEHICLE]
        capacity_first = float(vehicle[CONF_CAPACITY][0])
        if capacity_first > 0:
            soc_values = [float(e) / capacity_first for e in energy_stored.values]
        else:
            soc_values = [0.0] * len(energy_stored.values)

        ev_outputs[EV_STATE_OF_CHARGE] = OutputData(
            type=OutputType.STATE_OF_CHARGE,
            unit="%",
            values=tuple(soc_values),
            direction=None,
        )

        # Trip energy delivered so far and the locked-in shortfall the
        # optimizer expects to cover with public charging.
        trip_energy = expect_output_data(trip_outputs[DEFERRABLE_LOAD_ENERGY_ABSORBED])
        ev_outputs[EV_TRIP_ENERGY_DELIVERED] = replace(trip_energy, type=OutputType.ENERGY)
        trip_deficit = expect_output_data(trip_outputs[DEFERRABLE_LOAD_ENERGY_DEFICIT])
        ev_outputs[EV_TRIP_ENERGY_DEFICIT] = replace(trip_deficit, type=OutputType.ENERGY)

        # Reserve shortfall, only when a reserve is configured
        if config.get(SECTION_TRIP, {}).get(CONF_RESERVE_SOC) is not None:
            reserve = expect_output_data(battery_outputs[BATTERY_RESERVE_SHORTFALL])
            ev_outputs[EV_RESERVE_SHORTFALL] = replace(reserve, type=OutputType.ENERGY)

        # Shadow prices for the home charge/discharge power limits
        shadow_mappings: tuple[tuple[EvOutputName, Mapping[ModelOutputName, ModelOutputValue] | None], ...] = (
            (EV_POWER_MAX_CHARGE_PRICE, charge_conn),
            (EV_POWER_MAX_DISCHARGE_PRICE, discharge_conn),
        )
        for output_name, conn in shadow_mappings:
            if (
                conn is not None
                and isinstance(segments_output := conn.get(CONNECTION_SEGMENTS), Mapping)
                and isinstance(power_limit_outputs := segments_output.get("power_limit"), Mapping)
                and (shadow := expect_output_data(power_limit_outputs.get("power_limit"))) is not None
            ):
                ev_outputs[output_name] = shadow

        return {EV_DEVICE_EV: ev_outputs}


adapter = EvAdapter()


def _public_price(config: EvConfigData) -> NDArray[np.floating[Any]] | float:
    """Return the configured public charging price or the high default."""
    public_charging = config.get(SECTION_PUBLIC_CHARGING, {})
    price = public_charging.get(CONF_PUBLIC_CHARGING_PRICE)
    if price is None:
        return DEFAULT_PUBLIC_CHARGING_PRICE
    return _non_negative(price)


def _non_negative(price: NDArray[np.floating[Any]] | float) -> NDArray[np.floating[Any]] | float:
    """Clamp a penalty price at zero.

    A negative price on a trip deficit or reserve shortfall would pay the
    optimizer to miss the trip, and an entity can report one even though
    the form cannot.
    """
    if isinstance(price, np.ndarray):
        return np.maximum(price, 0.0)
    return max(float(price), 0.0)


def _combine_connected(
    calendar: CalendarBoundaryData | None,
    connected_live: NDArray[np.floating[Any]] | float | None,
) -> NDArray[np.floating[Any]] | float | None:
    """Combine calendar presence and the live connected sensor.

    The calendar is authoritative for the future (away during trip windows);
    the live sensor pins the present interval. Without a calendar the live
    sensor value applies across the whole horizon. Returns per-interval
    values, a scalar, or None when neither source is configured.
    """
    if calendar is None:
        return connected_live

    # presence marks periods overlapping a trip window; drop the trailing
    # boundary entry to get the n per-interval mask.
    connected = 1.0 - np.asarray(calendar["presence"][:-1], dtype=np.float64)

    if connected_live is not None:
        live_now = float(np.atleast_1d(connected_live)[0])
        connected = connected.copy()
        connected[0] = live_now

    return connected


def _trip_progress_energy(
    trip: Mapping[str, Any],
    calendar: CalendarBoundaryData | None,
    energy_per_distance: float,
    connected_flag: NDArray[np.floating[Any]] | float | None,
) -> float:
    """Energy already consumed on the open trip, from odometer readings.

    Only applies while the EV is away during a trip window that overlaps the
    current interval: the distance driven since disconnect counts toward that
    trip's requirement so the optimizer does not charge again for distance
    already covered. The credit is capped at the open trip's distance, so
    driving further than planned — or driving outside any trip window — never
    counts toward trips that have not started yet.
    """
    if calendar is None or connected_flag is None:
        return 0.0
    if float(np.atleast_1d(connected_flag)[0]) >= _CONNECTED_THRESHOLD:
        return 0.0

    odometer = trip.get(CONF_ODOMETER)
    odometer_at_disconnect = trip.get(CONF_ODOMETER_AT_DISCONNECT)
    if odometer is None or odometer_at_disconnect is None:
        return 0.0

    open_trip_distance = float(calendar["value_span"][0])
    driven = max(0.0, float(odometer) - float(odometer_at_disconnect))
    return min(driven, open_trip_distance) * energy_per_distance


@dataclass(frozen=True)
class _ReserveConfig:
    """Battery reserve parameters derived from the trip configuration."""

    level: NDArray[np.float64]
    mask: NDArray[np.float64]
    price: NDArray[np.floating[Any]] | float


def _reserve_config(
    config: EvConfigData,
    calendar: CalendarBoundaryData | None,
) -> _ReserveConfig | None:
    """Battery reserve parameters from the trip reserve configuration.

    The reserve is checked at each trip window's end — because the pack can
    only drain while away, the level at a window's end is the lowest level
    hit during that window, so one priced check per window prices the
    window minimum (demand-level pricing). The price defaults to the public
    charging price: the cost of restoring the buffer away from home.
    """
    trip = config.get(SECTION_TRIP, {})
    reserve_soc = trip.get(CONF_RESERVE_SOC)
    if reserve_soc is None or calendar is None:
        return None

    capacity = config[SECTION_VEHICLE][CONF_CAPACITY]
    reserve_ratio = min(max(float(reserve_soc), 0.0), 1.0)
    reserve_price = trip.get(CONF_RESERVE_PRICE)
    reserve_price = _public_price(config) if reserve_price is None else _non_negative(reserve_price)

    return _ReserveConfig(
        level=reserve_ratio * np.asarray(capacity, dtype=np.float64),
        mask=(np.asarray(calendar["value_edge_end"], dtype=np.float64) > 0).astype(np.float64),
        price=_to_boundaries(reserve_price, len(capacity)),
    )


def _to_boundaries(
    value: NDArray[np.floating[Any]] | float,
    n_boundaries: int,
) -> NDArray[np.floating[Any]] | float:
    """Extend an interval-shaped series to boundary length by repeating the end."""
    if not isinstance(value, np.ndarray):
        return value
    if len(value) == n_boundaries - 1:
        return np.append(value, value[-1])
    return value


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


def _mask_or_zero(
    flag: NDArray[np.floating[Any]] | float | None,
    magnitude: float,
) -> NDArray[np.floating[Any]] | float:
    """Scale a binary mask to a power limit; no mask means no flow."""
    if flag is None:
        return 0.0
    return flag * magnitude


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
