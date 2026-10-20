"""EV element adapter for model layer integration."""

from collections.abc import Mapping
from dataclasses import replace
from typing import Final, Literal, NamedTuple

import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.core.adapters.output_utils import connection_power, expect_output_data
from custom_components.haeo.core.const import ConnectivityLevel
from custom_components.haeo.core.model import ModelElementConfig, ModelOutputName, ModelOutputValue
from custom_components.haeo.core.model import battery as model_battery
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.model.elements import (
    MODEL_ELEMENT_TYPE_BATTERY,
    MODEL_ELEMENT_TYPE_CONNECTION,
    MODEL_ELEMENT_TYPE_DEFERRABLE_LOAD,
)
from custom_components.haeo.core.model.elements.battery import BatteryElementConfig
from custom_components.haeo.core.model.elements.connection import CONNECTION_SEGMENTS
from custom_components.haeo.core.model.elements.deferrable_load import (
    DEFERRABLE_LOAD_ENERGY_DELIVERED,
    DEFERRABLE_LOAD_ENERGY_SHORTFALL,
)
from custom_components.haeo.core.model.output_data import OutputData
from custom_components.haeo.core.schema import extract_connection_target
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.buffer import CONF_LOADS, CONF_STORAGE, BufferRole
from custom_components.haeo.core.schema.elements.ev import (
    CONF_AWAY,
    CONF_CAPACITY,
    CONF_CHARGE_LIMIT_COST,
    CONF_CONNECTED,
    CONF_CURRENT_SOC,
    CONF_ENERGY_PER_DISTANCE,
    CONF_MAX_CHARGE_RATE,
    CONF_MAX_DISCHARGE_RATE,
    CONF_MIN_CHARGE_PERCENTAGE,
    CONF_ODOMETER,
    CONF_PUBLIC_CHARGING_PRICE,
    CONF_TRIP_DUE,
    CONF_TRIP_OPENED,
    CONF_TRIP_START,
    ELEMENT_TYPE,
    SECTION_ADVANCED,
    SECTION_CHARGING,
    SECTION_PUBLIC_CHARGING,
    SECTION_TRIP,
    SECTION_VEHICLE,
    EvConfigData,
    TripData,
)
from custom_components.haeo.core.schema.sections import (
    CONF_CONNECTION,
    CONF_EFFICIENCY_SOURCE_TARGET,
    CONF_EFFICIENCY_TARGET_SOURCE,
    SECTION_EFFICIENCY,
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

# Price ($/kWh) of planning more trip energy than a trip needs. A trip's
# energy is not the plan's to choose, so the plan never drives further than
# the trip, even when energy is paid to be used; finite so the optimization
# stays feasible.
TRIP_OVERAGE_PRICE: Final = 10.0

# EV-specific output names for translation/sensor mapping
type EvOutputName = Literal[
    "ev_power_charge",
    "ev_power_discharge",
    "ev_power_active",
    "ev_state_of_charge",
    "ev_energy_stored",
    "ev_trip_energy_delivered",
    "ev_trip_energy_shortfall",
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
        EV_TRIP_ENERGY_SHORTFALL := "ev_trip_energy_shortfall",
        EV_POWER_MAX_CHARGE_PRICE := "ev_power_max_charge_price",
        EV_POWER_MAX_DISCHARGE_PRICE := "ev_power_max_discharge_price",
    )
)

type EvDeviceName = Literal[ElementType.EV]

EV_DEVICE_NAMES: Final[frozenset[EvDeviceName]] = frozenset(
    (EV_DEVICE_EV := ElementType.EV,),
)


class _TripWindows(NamedTuple):
    """Trip windows as deferrable load parameters, in energy.

    Attributes:
        in_window: 1.0 for each period inside a trip (n entries).
        window_start: 1.0 at boundaries where a trip starts (n+1 entries).
        opened: The energy of the trips starting at each boundary (n+1 entries).
        due: The energy of the trips ending at each boundary (n+1 entries).

    """

    in_window: NDArray[np.float64]
    window_start: NDArray[np.float64]
    opened: NDArray[np.float64]
    due: NDArray[np.float64]


class EvAdapter:
    """Adapter for EV elements."""

    element_type: str = ELEMENT_TYPE
    advanced: bool = False
    connectivity: ConnectivityLevel = ConnectivityLevel.NEVER
    can_source: bool = True
    can_sink: bool = True
    buffer_roles: frozenset[BufferRole] = frozenset({CONF_STORAGE, CONF_LOADS})

    def model_elements(self, config: EvConfigData) -> list[ModelElementConfig]:
        """Create model elements for EV configuration.

        Creates 5 model elements:
        1. {name} - Battery (EV battery)
        2. {name}:charge - Connection (network → EV, home charging)
        3. {name}:discharge - Connection (EV → network, V2G)
        4. {name}:trip - Deferrable load (trip energy requirement)
        5. {name}:trip_connection - Connection (EV → trip load, away only)

        Trip windows come from the trip calendar: while away the home
        connections are masked off and each trip's energy (distance times
        consumption) is due into the trip load by that trip's end. The
        requirement is not hard: any shortfall is priced at the public
        charging price, which models topping up publicly during the trip and
        keeps the optimization feasible when home charging cannot cover the
        trip in time.

        The plugged-in sensor pins the current interval, and the odometer's
        distance since the open trip began tells how far the trip has gone:

        - Plugged in without having driven, the car has not left yet. It is
          home for the current interval and the trip happens in the rest of
          its window.
        - Plugged in after driving, the car is back. That trip is over, and
          the car is home until the trip's scheduled end.
        - Unplugged, the car is on the trip, and the energy for the distance
          driven counts toward it, up to the trip's own energy: driving
          further completes the trip. Unplugging again after coming back
          resumes the trip, as the distance counts from the trip's start.
        """
        name = config["name"]
        vehicle = config[SECTION_VEHICLE]
        charging = config[SECTION_CHARGING]
        efficiency = config[SECTION_EFFICIENCY]
        target_name = extract_connection_target(config[CONF_CONNECTION])

        capacity = vehicle[CONF_CAPACITY]
        # current_soc is already a 0-1 ratio (the loader converts percent
        # fields); clamp so a glitched sensor cannot make the model infeasible
        initial_charge = min(max(vehicle[CONF_CURRENT_SOC], 0.0), 1.0) * float(capacity[0])
        energy_per_distance = float(vehicle[CONF_ENERGY_PER_DISTANCE])

        # EV pack, held above its min charge like a battery: falling below
        # it is allowed, so a car that comes home under it stays feasible, but
        # costs the limit cost per hour, so a trip never plans to.
        pack: BatteryElementConfig = {
            "element_type": MODEL_ELEMENT_TYPE_BATTERY,
            "name": name,
            "capacity": capacity,
            "initial_charge": initial_charge,
            "salvage_value": 0.0,
            "charge_limit_cost": config[SECTION_ADVANCED][CONF_CHARGE_LIMIT_COST],
        }
        if (min_ratio := vehicle.get(CONF_MIN_CHARGE_PERCENTAGE)) is not None:
            pack["min_charge"] = min_ratio * capacity

        trip = config.get(SECTION_TRIP, {})
        plugged_in = bool(charging[CONF_CONNECTED][0] >= _CONNECTED_THRESHOLD)
        driven_energy = trip.get(CONF_ODOMETER, 0.0) * energy_per_distance
        n_periods = len(charging[CONF_CONNECTED])

        windows = _trip_windows(trip, energy_per_distance, n_periods)
        if plugged_in and driven_energy > 0.0:
            windows = _drop_open_trip(windows)
        home = 1.0 - windows.in_window
        home[0] = 1.0 if plugged_in else 0.0

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
                    "power_limit": {
                        "segment_type": "power_limit",
                        "max_power": charging[CONF_MAX_CHARGE_RATE] * home,
                    },
                    "efficiency": {
                        "segment_type": "efficiency",
                        "efficiency": efficiency.get(CONF_EFFICIENCY_TARGET_SOURCE),
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
                        "max_power": charging.get(CONF_MAX_DISCHARGE_RATE, 0.0) * home,
                    },
                },
            },
            # 4. Trip requirement as a deferrable load, a shortfall priced at
            # the public charging price and planned overage priced so high it
            # never happens.
            {
                "element_type": MODEL_ELEMENT_TYPE_DEFERRABLE_LOAD,
                "name": f"{name}:trip",
                "is_source": False,
                "is_sink": True,
                "in_window": windows.in_window,
                "window_start": windows.window_start,
                "opened": windows.opened,
                "due": windows.due,
                "initial_energy": 0.0 if plugged_in else min(driven_energy, float(windows.opened[0])),
                "deficit_price": _public_price(config, n_periods),
                "overage_price": np.full(n_periods + 1, TRIP_OVERAGE_PRICE),
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
                        "max_power": (1.0 - home) * _UNLIMITED_POWER,
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
        **_kwargs: object,
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

        # State of charge as a 0-1 ratio (display scales percent outputs).
        # Capacity and stored energy are both boundary aligned, so each
        # boundary divides by its own capacity; a zero capacity reads as 0.
        capacity = np.asarray(config[SECTION_VEHICLE][CONF_CAPACITY], dtype=np.float64)
        stored = np.asarray(energy_stored.values, dtype=np.float64)
        soc_values = np.divide(stored, capacity, out=np.zeros_like(stored), where=capacity > 0)

        ev_outputs[EV_STATE_OF_CHARGE] = OutputData(
            type=OutputType.STATE_OF_CHARGE,
            unit="%",
            values=tuple(soc_values.tolist()),
            direction=None,
        )

        # Trip energy delivered in the current trip and the shortfall each
        # trip is expected to cover with public charging.
        trip_energy = expect_output_data(trip_outputs[DEFERRABLE_LOAD_ENERGY_DELIVERED])
        ev_outputs[EV_TRIP_ENERGY_DELIVERED] = replace(trip_energy, type=OutputType.ENERGY)
        trip_shortfall = expect_output_data(trip_outputs[DEFERRABLE_LOAD_ENERGY_SHORTFALL])
        ev_outputs[EV_TRIP_ENERGY_SHORTFALL] = replace(trip_shortfall, type=OutputType.ENERGY)

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


def _public_price(config: EvConfigData, n_periods: int) -> NDArray[np.float64]:
    """Return the public charging price at each boundary, the high default when none is configured."""
    price = config.get(SECTION_PUBLIC_CHARGING, {}).get(CONF_PUBLIC_CHARGING_PRICE, DEFAULT_PUBLIC_CHARGING_PRICE)
    return np.broadcast_to(np.asarray(price, dtype=np.float64), n_periods + 1).copy()


def _trip_windows(trip: TripData, energy_per_distance: float, n_periods: int) -> _TripWindows:
    """Return the trip windows the trip calendar feeds, in energy; without a trip calendar there are none."""
    away = trip.get(CONF_AWAY)
    trip_start = trip.get(CONF_TRIP_START)
    opened = trip.get(CONF_TRIP_OPENED)
    due = trip.get(CONF_TRIP_DUE)
    if away is None or trip_start is None or opened is None or due is None:
        return _TripWindows(
            in_window=np.zeros(n_periods),
            window_start=np.zeros(n_periods + 1),
            opened=np.zeros(n_periods + 1),
            due=np.zeros(n_periods + 1),
        )
    return _TripWindows(
        in_window=away.copy(),
        window_start=trip_start,
        opened=opened * energy_per_distance,
        due=due * energy_per_distance,
    )


def _drop_open_trip(windows: _TripWindows) -> _TripWindows:
    """Remove the trip open at the horizon start, which the car already came back from.

    The trip runs until its window ends or the next one starts; its events
    neither open nor fall due within it.
    """
    n_periods = len(windows.in_window)
    if windows.in_window[0] <= 0.0:
        return windows
    end = next(
        (t for t in range(1, n_periods) if windows.in_window[t] <= 0.0 or windows.window_start[t] > 0.0),
        n_periods,
    )
    in_window = windows.in_window.copy()
    in_window[:end] = 0.0
    opened = windows.opened.copy()
    opened[:end] = 0.0
    due = windows.due.copy()
    due[1 : end + 1] = 0.0
    return _TripWindows(in_window=in_window, window_start=windows.window_start, opened=opened, due=due)
