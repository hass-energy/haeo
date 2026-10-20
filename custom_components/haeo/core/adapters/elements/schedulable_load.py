"""Schedulable load element adapter for model layer integration."""

from collections.abc import Mapping
from dataclasses import replace
from typing import Final, Literal

import numpy as np
from numpy.typing import NDArray

from custom_components.haeo.core.adapters.output_utils import connection_power, expect_output_data
from custom_components.haeo.core.const import ConnectivityLevel
from custom_components.haeo.core.model import ModelElementConfig, ModelOutputName, ModelOutputValue
from custom_components.haeo.core.model.const import OutputType
from custom_components.haeo.core.model.elements import (
    MODEL_ELEMENT_TYPE_CONNECTION,
    MODEL_ELEMENT_TYPE_SCHEDULABLE_LOAD,
    SchedulableLoadElementConfig,
)
from custom_components.haeo.core.model.elements.schedulable_load import (
    SCHEDULABLE_LOAD_ENERGY_MISSED,
    SCHEDULABLE_LOAD_START,
)
from custom_components.haeo.core.model.output_data import OutputData
from custom_components.haeo.core.schema import extract_connection_target
from custom_components.haeo.core.schema.elements import ElementType
from custom_components.haeo.core.schema.elements.buffer import CONF_LOADS, BufferRole
from custom_components.haeo.core.schema.elements.schedulable_load import (
    CONF_DEFICIT_PRICE,
    CONF_DURATION,
    CONF_ENERGY_METER,
    CONF_IN_WINDOW,
    CONF_INTEGER_MODE,
    CONF_POWER,
    CONF_RUNNING,
    CONF_WINDOW_START,
    DEFAULT_INTEGER_MODE,
    ELEMENT_TYPE,
    SECTION_ADVANCED,
    SECTION_PRICING,
    SECTION_PROFILE,
    SECTION_SCHEDULE,
    SchedulableLoadConfigData,
)
from custom_components.haeo.core.schema.sections import CONF_CONNECTION

# Readings at or above this count as running, matching availability inputs.
_RUNNING_THRESHOLD: Final = 0.5

# Fraction of a run's energy an idle load must have used since the open
# window began for that window's run to count as done. Standby use stays far
# below it, and a run that stopped partway through counts once mostly done.
_DONE_FRACTION: Final = 0.5

# Schedulable-load-specific output names for translation/sensor mapping
type SchedulableLoadElementOutputName = Literal[
    "schedulable_load_power",
    "schedulable_load_start",
    "schedulable_load_energy_missed",
]

SCHEDULABLE_LOAD_ELEMENT_OUTPUT_NAMES: Final[frozenset[SchedulableLoadElementOutputName]] = frozenset(
    (
        SCHEDULABLE_POWER := "schedulable_load_power",
        SCHEDULABLE_START := "schedulable_load_start",
        SCHEDULABLE_ENERGY_MISSED := "schedulable_load_energy_missed",
    )
)

type SchedulableLoadDeviceName = Literal[ElementType.SCHEDULABLE_LOAD]

SCHEDULABLE_LOAD_DEVICE_NAMES: Final[frozenset[SchedulableLoadDeviceName]] = frozenset(
    (SCHEDULABLE_LOAD_DEVICE := ElementType.SCHEDULABLE_LOAD,),
)


class SchedulableLoadAdapter:
    """Adapter for schedulable load elements."""

    element_type: str = ELEMENT_TYPE
    advanced: bool = False
    connectivity: ConnectivityLevel = ConnectivityLevel.NEVER
    can_source: bool = False
    can_sink: bool = True
    buffer_roles: frozenset[BufferRole] = frozenset({CONF_LOADS})

    def model_elements(self, config: SchedulableLoadConfigData) -> list[ModelElementConfig]:
        """Create model elements for schedulable load configuration.

        Creates 2 model elements:
        1. {name} - Schedulable load (one run of the profile per calendar window)
        2. {name}:connection - Connection (network → load)

        Calendar events define the windows each run must fit inside, and
        overlapping events merge into one window. The profile is a single
        step at the configured power for the configured duration.

        The running sensor and energy meter tie the plan to what the load is
        doing. The meter's rise since the open window began is how far through
        the profile the load is. A load running now finishes the rest of its
        run from the horizon start, and the open window takes no further run.
        Without a meter, a running load is taken to have just started. An idle
        load whose meter rose by at least half a run's energy since the open
        window began has done that window's run.
        """
        name = config["name"]
        schedule = config[SECTION_SCHEDULE]
        profile = config[SECTION_PROFILE]
        pricing = config[SECTION_PRICING]
        advanced = config.get(SECTION_ADVANCED, {})

        in_window = schedule[CONF_IN_WINDOW]
        profile_power = np.array([float(profile[CONF_POWER])])
        profile_duration = np.array([float(profile[CONF_DURATION])])
        used = schedule.get(CONF_ENERGY_METER, 0.0)
        running = float(schedule.get(CONF_RUNNING, 0.0)) >= _RUNNING_THRESHOLD
        run_energy = float(np.sum(profile_power * profile_duration))

        load: SchedulableLoadElementConfig = {
            "element_type": MODEL_ELEMENT_TYPE_SCHEDULABLE_LOAD,
            "name": name,
            "profile_power": profile_power,
            "profile_duration": profile_duration,
            "in_window": in_window,
            "window_start": schedule[CONF_WINDOW_START],
            "deficit_price": pricing[CONF_DEFICIT_PRICE],
            "elapsed": _profile_time(profile_power, profile_duration, used) if running else None,
            "window_started": bool(in_window[0] > 0.0 and (running or used >= _DONE_FRACTION * run_energy > 0.0)),
            "integer_mode": advanced.get(CONF_INTEGER_MODE, DEFAULT_INTEGER_MODE),
            "is_source": False,
            "is_sink": True,
        }

        return [
            load,
            {
                "element_type": MODEL_ELEMENT_TYPE_CONNECTION,
                "name": f"{name}:connection",
                "source": extract_connection_target(config[CONF_CONNECTION]),
                "target": name,
                "segments": {},
            },
        ]

    def outputs(
        self,
        name: str,
        model_outputs: Mapping[str, Mapping[ModelOutputName, ModelOutputValue]],
        *,
        config: SchedulableLoadConfigData,  # noqa: ARG002 (protocol signature)
        **_kwargs: object,
    ) -> Mapping[SchedulableLoadDeviceName, Mapping[SchedulableLoadElementOutputName, OutputData]]:
        """Map model outputs to schedulable-load-specific output names."""
        load_outputs = model_outputs[name]
        connection = model_outputs.get(f"{name}:connection")

        start = expect_output_data(load_outputs[SCHEDULABLE_LOAD_START])
        missed = expect_output_data(load_outputs[SCHEDULABLE_LOAD_ENERGY_MISSED])
        period_count = len(start.values) - 1

        power = replace(connection_power(connection, period_count), type=OutputType.POWER, direction="-")

        return {
            SCHEDULABLE_LOAD_DEVICE: {
                SCHEDULABLE_POWER: power,
                SCHEDULABLE_START: start,
                SCHEDULABLE_ENERGY_MISSED: missed,
            }
        }


adapter = SchedulableLoadAdapter()


def _profile_time(profile_power: NDArray[np.float64], profile_duration: NDArray[np.float64], energy: float) -> float:
    """Return how long, in hours, the profile runs to use *energy*."""
    cumulative_time = np.concatenate(([0.0], np.cumsum(profile_duration)))
    cumulative_energy = np.concatenate(([0.0], np.cumsum(profile_power * profile_duration)))
    return float(np.interp(energy, cumulative_energy, cumulative_time))
